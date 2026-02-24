
import socket
import threading
import pyaudio
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import requests
import json
import time
import queue
import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import crypto_utils
from urllib.parse import urlparse

# Matplotlib for post-call graphs
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Audio Configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Constants
REGISTRY_URL_DEFAULT = "http://127.0.0.1:5001"


def get_local_ip(registry_url=None):
    """Get this machine's LAN IP address, attempting to use registry host to identify interface."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if registry_url:
            host = urlparse(registry_url).hostname
            if host and not host.startswith("127.") and host != "localhost":
                # Connect to registry server's IP to find which local interface we're on
                s.connect((host, 5001))
            else:
                s.connect(("8.8.8.8", 80))
        else:
            s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try: return socket.gethostbyname(socket.gethostname())
        except: return "127.0.0.1"


class UserManager:
    def __init__(self, registry_url):
        self.registry_url = registry_url.rstrip('/')
        self.username = None
        self.public_key = None
        self.secret_key = None
        self.listening_port = None

    def register(self, username, port):
        try:
            self.public_key, self.secret_key = crypto_utils.kyber_generate_keypair()
            pk_hex = self.public_key.hex()

            # Ensure lower-case consistency
            uname = username.strip().lower()

            # Identify our LAN IP relative to the registry server
            my_real_ip = get_local_ip(self.registry_url)
            payload = {
                "username": uname,
                "public_key": pk_hex,
                "listening_ip": my_real_ip,
                "listening_port": port
            }

            resp = requests.post(f"{self.registry_url}/register", json=payload)
            if resp.status_code in [200, 201]:
                self.username = uname
                self.listening_port = port
                return True, resp.json().get("message")
            else:
                return False, resp.json().get("message")
        except Exception as e:
            return False, str(e)

    def initiate_call(self, callee_username):
        try:
            uname = callee_username.strip().lower()
            resp = requests.get(f"{self.registry_url}/fetch/{uname}")
            if resp.status_code != 200:
                return False, f"User {uname} not found", None
            data = resp.json()
            callee_pk = bytes.fromhex(data['public_key'])
            session_key, ciphertext = crypto_utils.kyber_encapsulate(callee_pk)
            payload = {
                "caller": self.username,
                "callee": uname,
                "caller_listen_port": self.listening_port,
                "session_key_ciphertext": ciphertext.hex()
            }
            call_resp = requests.post(f"{self.registry_url}/call/initiate", json=payload)
            if call_resp.status_code != 200:
                return False, call_resp.json().get("message"), None
            call_data = call_resp.json()
            # Return peer_ip, peer_port, session_key
            return True, call_data['call_id'], (call_data.get('callee_ip'), call_data.get('callee_port'), session_key)
        except Exception as e:
            return False, str(e), None

    def accept_call(self, call_id, ciphertext_hex):
        try:
            ciphertext = bytes.fromhex(ciphertext_hex)
            session_key = crypto_utils.kyber_decapsulate(ciphertext, self.secret_key)
            payload = {"call_id": call_id}
            resp = requests.post(f"{self.registry_url}/call/accept", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                # Return peer_ip, peer_port, session_key
                return True, (data.get('caller_ip'), data.get('caller_port'), session_key)
            else:
                return False, None
        except Exception as e:
            print(f"Accept error: {e}")
            return False, None

    def poll_pending_calls(self):
        if not self.username: return []
        try:
            resp = requests.get(f"{self.registry_url}/call/pending/{self.username}", timeout=1)
            if resp.status_code == 200:
                return resp.json().get("pending_calls", [])
        except: pass
        return []

    def check_call_status(self, call_id):
        try:
            resp = requests.get(f"{self.registry_url}/call/status/{call_id}", timeout=1)
            if resp.status_code == 200:
                return resp.json().get("status")
        except: pass
        return "unknown"

    def unregister(self):
        if self.username:
            try: requests.delete(f"{self.registry_url}/unregister/{self.username}")
            except: pass

    def fetch_online_users(self):
        try:
            resp = requests.get(f"{self.registry_url}/list", timeout=1)
            if resp.status_code == 200:
                users = resp.json().get("users", {})
                return [u for u in users.keys() if u != self.username]
        except: pass
        return []


class AudioHandler:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.in_stream = None
        self.out_stream = None
        self.recording = False

    def start_stream(self):
        if self.in_stream: return
        try:
            # Separate input and output streams to prevent local hardware feedback
            self.in_stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                                          input=True, output=False, frames_per_buffer=CHUNK)
            self.out_stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                                          input=False, output=True, frames_per_buffer=CHUNK)
            self.recording = True
        except Exception as e:
            print(f"Audio Error: {e}")
            raise

    def stop_stream(self):
        self.recording = False
        if self.in_stream:
            try:
                self.in_stream.stop_stream()
                self.in_stream.close()
            except: pass
            self.in_stream = None
        if self.out_stream:
            try:
                self.out_stream.stop_stream()
                self.out_stream.close()
            except: pass
            self.out_stream = None

    def record_chunk(self):
        if self.in_stream and self.recording:
            try: return self.in_stream.read(CHUNK, exception_on_overflow=False)
            except: pass
        return None

    def play_chunk(self, data):
        if self.out_stream and self.recording:
            try: self.out_stream.write(data)
            except: pass

    def terminate(self):
        self.stop_stream()
        self.p.terminate()


class NetworkHandler:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', 0))
        self.target_ip = None
        self.target_port = None
        self.running = False
        self.session_key = None
        self.packet_counter_send = 0
        self.crypt = None

        # Metrics
        self.pkts_sent = 0
        self.pkts_recv = 0
        self.pkts_lost = 0
        self.bytes_sent = 0
        self.bytes_recv = 0
        self.obfuscation_enabled = True

        self.latency_ms = 0.0
        self.jitter_ms = 0.0
        self._prev_latency = 0.0

        self.latency_history = []
        self.throughput_history = []
        self._call_start_time = 0
        self._last_throughput_check = 0
        self._last_bytes_sent = 0
        self._last_bytes_recv = 0

    def set_session_key(self, key):
        self.session_key = key
        self.crypt = AESGCM(key)
        self.packet_counter_send = 0
        self.pkts_sent = 0
        self.pkts_recv = 0
        self.pkts_lost = 0
        self.bytes_sent = 0
        self.bytes_recv = 0
        self.latency_ms = 0.0
        self.jitter_ms = 0.0
        self._prev_latency = 0.0
        self.latency_history = []
        self.throughput_history = []
        self._call_start_time = time.time()
        self._last_throughput_check = time.time()
        self._last_bytes_sent = 0
        self._last_bytes_recv = 0

    def start_listening(self, port, on_receive_callback):
        self.running = True
        try:
            self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(('0.0.0.0', int(port)))
        except Exception as e:
            print(f"Error binding to port {port}: {e}")
            raise

        def listen():
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(CHUNK * 4)
                    on_receive_callback(data, addr[0])
                except Exception as e:
                    if self.running: print(f"Error receiving: {e}")

        threading.Thread(target=listen, daemon=True).start()

    def send_data(self, audio_data):
        if self.target_ip and self.target_port and self.session_key:
            try:
                idx = self.packet_counter_send
                # XOR Obfuscation (Identity protection)
                obfuscated = crypto_utils.obfuscate_audio(audio_data, self.session_key, idx)
                nonce = os.urandom(12)
                index_bytes = idx.to_bytes(4, 'big')
                ts = struct.pack('!d', time.time())
                # AES-GCM Encryption (Payload protection)
                ciphertext = self.crypt.encrypt(nonce, ts + obfuscated, associated_data=index_bytes)
                packet = nonce + index_bytes + ciphertext
                self.sock.sendto(packet, (self.target_ip, int(self.target_port)))
                self.packet_counter_send += 1
                self.pkts_sent += 1
                self.bytes_sent += len(packet)
            except: pass

    def process_incoming_packet(self, data):
        if not self.session_key: return None, None
        try:
            if len(data) < 24: return None, None
            nonce, index_bytes, ciphertext = data[:12], data[12:16], data[16:]
            idx = int.from_bytes(index_bytes, 'big')

            # Decrypt
            plaintext = self.crypt.decrypt(nonce, ciphertext, associated_data=index_bytes)
            send_ts = struct.unpack('!d', plaintext[:8])[0]
            obfuscated = plaintext[8:]

            # Latency Metrics
            now = time.time()
            new_latency = (now - send_ts) * 1000
            if new_latency < 0: new_latency = 0
            if new_latency > 5000: new_latency = self.latency_ms
            self.jitter_ms = abs(new_latency - self._prev_latency) * 0.1 + self.jitter_ms * 0.9
            self._prev_latency = self.latency_ms
            self.latency_ms = new_latency * 0.3 + self.latency_ms * 0.7

            self.pkts_recv += 1
            self.bytes_recv += len(data)

            # De-obfuscate
            clear_audio = crypto_utils.deobfuscate_audio(obfuscated, self.session_key, idx)
            return clear_audio, obfuscated
        except:
            self.pkts_lost += 1
            return None, None

    def record_metrics_snapshot(self):
        now = time.time()
        elapsed = now - self._call_start_time
        self.latency_history.append((elapsed, self.latency_ms))
        dt = now - self._last_throughput_check
        if dt > 0:
            tx_rate = (self.bytes_sent - self._last_bytes_sent) / dt / 1024.0
            rx_rate = (self.bytes_recv - self._last_bytes_recv) / dt / 1024.0
            self.throughput_history.append((elapsed, tx_rate, rx_rate))
        self._last_throughput_check = now
        self._last_bytes_sent = self.bytes_sent
        self._last_bytes_recv = self.bytes_recv

    def stop(self):
        self.running = False
        try: self.sock.close()
        except: pass


class VoiceChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PQC Secure Voice Chat")
        self.root.geometry("520x800")
        self.root.configure(bg="#f0f2f5")

        self.style = ttk.Style()
        self.style.configure("Header.TLabel", font=("Arial", 16, "bold"), background="#f0f2f5", foreground="#1a73e8")

        self.audio = AudioHandler()
        self.network = NetworkHandler()
        self.user_manager = None
        self.is_call_active = False
        self.poll_active = False
        self.start_time = 0
        self.peer_username = ""
        self.my_ip = get_local_ip()
        self.peer_ip = ""
        self.audio_queue = queue.Queue()
        self.playback_thread_running = False

        self.setup_login_ui()

    def setup_login_ui(self):
        for widget in self.root.winfo_children(): widget.destroy()
        main_frame = tk.Frame(self.root, bg="#f0f2f5")
        main_frame.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(main_frame, text="PQC SECURE VOICE", style="Header.TLabel").pack(pady=20)
        box = tk.LabelFrame(main_frame, text=" Registry Login ", bg="white", padx=20, pady=20, font=("Arial", 10, "bold"))
        box.pack(padx=20, pady=10, fill="both")
        ttk.Label(box, text="Server URL:", background="white").pack(anchor="w")
        self.registry_var = tk.StringVar(value=REGISTRY_URL_DEFAULT)
        ttk.Entry(box, textvariable=self.registry_var, width=40).pack(pady=5)
        ttk.Label(box, text="Username:", background="white").pack(anchor="w", pady=(10,0))
        self.username_var = tk.StringVar()
        ttk.Entry(box, textvariable=self.username_var, width=40).pack(pady=5)
        ttk.Button(box, text="Connect Online", command=self.do_login).pack(pady=20, fill="x")
        tk.Label(box, text=f"Local IP: {self.my_ip}", bg="white", fg="#1a73e8", font=("Arial", 9, "bold")).pack()

    def do_login(self):
        uname = self.username_var.get().strip()
        reg = self.registry_var.get().strip()
        if not uname: return messagebox.showerror("Error", "Username required")
        if reg and not reg.startswith("http"): reg = f"http://{reg}"
        if ":" not in reg[7:]: reg = f"{reg}:5001"

        # Update my_ip using the registry host
        self.my_ip = get_local_ip(reg)

        self.user_manager = UserManager(reg)
        success, msg = self.user_manager.register(uname, 50005)
        if success:
            try:
                self.network.start_listening(50005, self.on_packet_received)
                self.setup_main_ui()
                self.start_polling()
            except Exception as e:
                messagebox.showerror("Error", f"Binding error: {e}")
        else:
            messagebox.showerror("Failed", msg)

    def setup_main_ui(self):
        for widget in self.root.winfo_children(): widget.destroy()
        top = tk.Frame(self.root, bg="#1a73e8", height=60)
        top.pack(fill="x")
        tk.Label(top, text=f"  {self.user_manager.username}", bg="#1a73e8", fg="white", font=("Arial", 11, "bold")).pack(side="left", padx=10, pady=15)
        tk.Button(top, text="Exit", command=self.logout, bg="#1a73e8", fg="white", bd=0).pack(side="right", padx=15)

        self.container = tk.Frame(self.root, bg="#f0f2f5")
        self.container.pack(fill="both", expand=True, padx=15, pady=10)

        self.idle_frame = tk.Frame(self.container, bg="#f0f2f5")
        self.idle_frame.pack(fill="both", expand=True)
        tk.Label(self.idle_frame, text="Target Username:", bg="#f0f2f5").pack(pady=(20,0))
        self.target_user_var = tk.StringVar()
        tk.Entry(self.idle_frame, textvariable=self.target_user_var, font=("Arial", 14), justify="center").pack(pady=5, fill="x")
        self.call_btn = tk.Button(self.idle_frame, text="START PQC-BASED CALL", command=self.initiate_call, bg="#28a745", fg="white", font=("Arial", 11, "bold"), pady=8)
        self.call_btn.pack(pady=10, fill="x")

        tk.Label(self.idle_frame, text="ONLINE CONTACTS", bg="#f0f2f5", font=("Arial", 9, "bold")).pack(pady=(10,0))
        lf = tk.Frame(self.idle_frame, bg="white", bd=1, relief="solid")
        lf.pack(fill="both", expand=True, pady=5)
        self.users_listbox = tk.Listbox(lf, font=("Arial", 11), bd=0)
        self.users_listbox.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lf, command=self.users_listbox.yview)
        sb.pack(side="right", fill="y")
        self.users_listbox.config(yscrollcommand=sb.set)
        self.users_listbox.bind('<Double-1>', lambda e: self.call_selected_user())

        self.call_active_frame = tk.Frame(self.container, bg="white", highlightbackground="#28a745", highlightthickness=2)
        # Call UI elements (timer, stats, toggle)
        self.peer_name_lbl = tk.Label(self.call_active_frame, text="PEER", bg="white", font=("Arial", 16, "bold"))
        self.peer_name_lbl.pack(pady=10)
        self.timer_lbl = tk.Label(self.call_active_frame, text="00:00", bg="white", font=("Courier", 28), fg="#28a745")
        self.timer_lbl.pack()
        
        dash = tk.LabelFrame(self.call_active_frame, text=" Metrics ", bg="#f8f9fa", font=("Arial", 8, "bold"))
        dash.pack(padx=10, pady=5, fill="x")
        self.kem_lbl = tk.Label(dash, text="KEM: Kyber-512", bg="#f8f9fa", font=("Courier", 8), anchor="w")
        self.kem_lbl.pack(fill="x", padx=5)
        self.tx_lbl = tk.Label(dash, text="TX: 0 pkts", bg="#f8f9fa", font=("Courier", 8), anchor="w")
        self.tx_lbl.pack(fill="x", padx=5)
        self.rx_lbl = tk.Label(dash, text="RX: 0 pkts", bg="#f8f9fa", font=("Courier", 8), anchor="w")
        self.rx_lbl.pack(fill="x", padx=5)
        self.latency_lbl = tk.Label(dash, text="LATENCY: -- ms", bg="#f8f9fa", font=("Courier", 8), anchor="w")
        self.latency_lbl.pack(fill="x", padx=5)
        self.loss_lbl = tk.Label(dash, text="PKT LOSS: 0", bg="#f8f9fa", font=("Courier", 8), anchor="w", fg="#dc3545")
        self.loss_lbl.pack(fill="x", padx=5)

        self.deobf_btn = tk.Button(self.call_active_frame, text="DEOBFUSCATION: ON", command=self.toggle_deobfuscation, bg="#28a745", fg="white", font=("Arial", 9, "bold"))
        self.deobf_btn.pack(pady=10, fill="x", padx=30)
        tk.Button(self.call_active_frame, text="END CALL", command=self.hangup, bg="#dc3545", fg="white", font=("Arial", 12, "bold"), pady=8).pack(pady=10, fill="x", padx=30)

        self.incoming_frame = tk.Frame(self.root, bg="#fff3cd", bd=1, relief="solid")

    def toggle_deobfuscation(self):
        self.network.obfuscation_enabled = not self.network.obfuscation_enabled
        if self.network.obfuscation_enabled: self.deobf_btn.config(text="DEOBFUSCATION: ON", bg="#28a745")
        else: self.deobf_btn.config(text="DEOBFUSCATION: OFF", bg="#dc3545")

    def start_polling(self):
        self.poll_active = True
        self.root.after(2000, self.poll_loop)

    def poll_loop(self):
        if not self.poll_active: return
        if not self.is_call_active:
            calls = self.user_manager.poll_pending_calls()
            if calls: self.show_incoming_call(calls[0])
            users = self.user_manager.fetch_online_users()
            self.users_listbox.delete(0, tk.END)
            for u in users: self.users_listbox.insert(tk.END, f"  {u}")
        self.root.after(2000, self.poll_loop)

    def show_incoming_call(self, call):
        self.incoming_frame.pack(fill="x", side="bottom", padx=10, pady=10)
        for w in self.incoming_frame.winfo_children(): w.destroy()
        tk.Label(self.incoming_frame, text=f"Incoming: {call['caller']}", bg="#fff3cd", font=("Arial", 10, "bold")).pack()
        bf = tk.Frame(self.incoming_frame, bg="#fff3cd")
        bf.pack(pady=5)
        tk.Button(bf, text="ACCEPT", bg="#28a745", fg="white", command=lambda: self.accept_call(call)).pack(side="left", padx=10)
        tk.Button(bf, text="IGNORE", command=lambda: self.incoming_frame.pack_forget()).pack(side="left")

    def initiate_call(self):
        target = self.target_user_var.get().strip()
        if not target: return
        self.call_btn.config(state="disabled", text="DIALING...")
        threading.Thread(target=self._dial_thread, args=(target,), daemon=True).start()

    def _dial_thread(self, target):
        success, cid, details = self.user_manager.initiate_call(target)
        if success:
            self.peer_username = target
            self.peer_ip = details[0]
            self._wait_for_answer(cid, *details)
        else:
            self.root.after(0, self.reset_ui)

    def _wait_for_answer(self, cid, ip, port, key):
        for _ in range(30):
            if self.user_manager.check_call_status(cid) == 'active':
                self.root.after(0, lambda: self.start_session(ip, port, key, cid, self.peer_username))
                return
            time.sleep(1)
        self.root.after(0, self.reset_ui)

    def accept_call(self, call):
        self.incoming_frame.pack_forget()
        self.peer_username = call['caller']
        success, details = self.user_manager.accept_call(call['call_id'], call['session_key_ciphertext'])
        if success:
            self.peer_ip = details[0]
            self.start_session(details[0], details[1], details[2], call['call_id'], self.peer_username)

    def start_session(self, ip, port, key, cid, peer):
        self.is_call_active = True
        self.network.target_ip, self.network.target_port = ip, port
        self.network.set_session_key(key)
        self.audio.start_stream()
        self.start_time = time.time()

        self.idle_frame.pack_forget()
        self.call_active_frame.pack(fill="both", expand=True, pady=10)
        self.peer_name_lbl.config(text=peer.upper())
        self.update_timer()

        self.playback_thread_running = True
        while not self.audio_queue.empty(): self.audio_queue.get_nowait()
        threading.Thread(target=self.playback_loop, daemon=True).start()
        threading.Thread(target=self.send_loop, daemon=True).start()

    def update_timer(self):
        if not self.is_call_active: return
        elapsed = int(time.time() - self.start_time)
        self.timer_lbl.config(text=f"{elapsed//60:02d}:{elapsed%60:02d}")
        self.network.record_metrics_snapshot()
        self.tx_lbl.config(text=f"TX: {self.network.pkts_sent} pkts")
        self.rx_lbl.config(text=f"RX: {self.network.pkts_recv} pkts")
        self.latency_lbl.config(text=f"LATENCY: {self.network.latency_ms:.1f} ms")
        self.loss_lbl.config(text=f"PKT LOSS: {self.network.pkts_lost}")
        self.root.after(1000, self.update_timer)

    def playback_loop(self):
        while self.playback_thread_running:
            try: self.audio.play_chunk(self.audio_queue.get(timeout=0.1))
            except: pass

    def send_loop(self):
        while self.is_call_active:
            d = self.audio.record_chunk()
            if d: self.network.send_data(d)

    def on_packet_received(self, data, sender_ip):
        # Strict Echo/Security Filter
        if sender_ip == self.my_ip or sender_ip == "127.0.0.1": return
        if not self.is_call_active or sender_ip != self.peer_ip: return

        clear, obf = self.network.process_incoming_packet(data)
        if clear:
            aud = clear if self.network.obfuscation_enabled else obf
            if self.audio_queue.qsize() > 5: self.audio_queue.get_nowait()
            self.audio_queue.put(aud)

    def hangup(self):
        params = (self.peer_username, time.time()-self.start_time, list(self.network.latency_history), list(self.network.throughput_history), self.network.pkts_sent, self.network.pkts_recv, self.network.pkts_lost, self.network.bytes_sent, self.network.bytes_recv)
        self.is_call_active = False
        self.playback_thread_running = False
        self.audio.stop_stream()
        self.reset_ui()
        self.root.after(300, lambda: self.show_post_call_graph(*params))

    def show_post_call_graph(self, peer, dur, lath, tph, ps, pr, pl, bs, br):
        win = tk.Toplevel(self.root)
        win.title("Call Stats")
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(2, 1, 1)
        if lath: ax.plot([x[0] for x in lath], [x[1] for x in lath], color='blue')
        ax.set_title("Latency (ms)")
        ax2 = fig.add_subplot(2, 1, 2)
        ax2.bar(['Sent', 'Recv', 'Lost'], [ps, pr, pl], color=['blue', 'green', 'red'])
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack()

    def reset_ui(self):
        self.is_call_active = False
        self.call_active_frame.pack_forget()
        self.idle_frame.pack(fill="both", expand=True)
        self.call_btn.config(state="normal", text="START PQC-BASED CALL")

    def logout(self):
        self.is_call_active = self.poll_active = self.playback_thread_running = False
        if self.user_manager: self.user_manager.unregister()
        self.network.stop()
        self.audio.terminate()
        self.setup_login_ui()

    def on_close(self):
        self.logout()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceChatApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
