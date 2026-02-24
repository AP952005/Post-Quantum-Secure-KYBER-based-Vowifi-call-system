
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.properties import StringProperty, BooleanProperty
import socket
import threading
import requests
import time
import queue
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import crypto_utils

# Use PyAudio if available (Pydroid 3 has it), else dummy for testing UI
try:
    import pyaudio
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

# Audio Constants (Synced with main server)
CHUNK = 1024
FORMAT = 16 # pyaudio.paInt16
CHANNELS = 1
RATE = 16000

class UserManager:
    def __init__(self, registry_url):
        self.registry_url = registry_url.rstrip('/')
        self.username = None
        self.public_key = None
        self.secret_key = None
        self.listening_port = 50005

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except: return "127.0.0.1"

    def register(self, username):
        try:
            self.public_key, self.secret_key = crypto_utils.kyber_generate_keypair()
            payload = {
                "username": username,
                "public_key": self.public_key.hex(),
                "listening_ip": "internal",
                "listening_port": self.listening_port
            }
            resp = requests.post(f"{self.registry_url}/register", json=payload, timeout=5)
            if resp.status_code in [200, 201]:
                self.username = username
                return True, ""
            return False, resp.json().get("message", "Error")
        except Exception as e: return False, str(e)

    def fetch_online_users(self):
        try:
            resp = requests.get(f"{self.registry_url}/list", timeout=2)
            if resp.status_code == 200:
                users = resp.json().get("users", {})
                return [u for u in users.keys() if u != self.username]
        except: pass
        return []

    def initiate_call(self, target):
        try:
            resp = requests.get(f"{self.registry_url}/fetch/{target}")
            if resp.status_code != 200: return False, "User not found", None
            pk = bytes.fromhex(resp.json()['public_key'])
            session_key, ciphertext = crypto_utils.kyber_encapsulate(pk)
            payload = {
                "caller": self.username,
                "callee": target,
                "caller_listen_port": self.listening_port,
                "session_key_ciphertext": ciphertext.hex()
            }
            cresp = requests.post(f"{self.registry_url}/call/initiate", json=payload)
            if cresp.status_code == 200:
                data = cresp.json()
                return True, data['call_id'], (data['callee_ip'], data['callee_port'], session_key)
            return False, "Call Refused", None
        except: return False, "Network Error", None

    def poll_calls(self):
        try:
            resp = requests.get(f"{self.registry_url}/call/pending/{self.username}", timeout=1)
            if resp.status_code == 200: return resp.json().get("pending_calls", [])
        except: pass
        return []

    def check_status(self, call_id):
        try:
            resp = requests.get(f"{self.registry_url}/call/status/{call_id}", timeout=1)
            if resp.status_code == 200: return resp.json().get("status")
        except: pass
        return "unknown"

    def accept_call(self, call_id, cipher_hex):
        try:
            sk = crypto_utils.kyber_decapsulate(bytes.fromhex(cipher_hex), self.secret_key)
            resp = requests.post(f"{self.registry_url}/call/accept", json={"call_id": call_id})
            if resp.status_code == 200:
                d = resp.json()
                return True, (d['caller_ip'], d['caller_port'], sk)
        except: pass
        return False, None

class NetworkHandler:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target = None
        self.session_key = None
        self.crypt = None
        self.counter = 0

    def start(self, callback):
        self.sock.bind(('0.0.0.0', 50005))
        def listen():
            while True:
                try:
                    data, addr = self.sock.recvfrom(4096)
                    if self.session_key:
                        raw = self.decrypt(data)
                        if raw: callback(raw, addr[0])
                except: break
        threading.Thread(target=listen, daemon=True).start()

    def decrypt(self, data):
        try:
            nonce, idx_b, ct = data[:12], data[12:16], data[16:]
            idx = int.from_bytes(idx_b, 'big')
            obf = self.crypt.decrypt(nonce, ct, associated_data=idx_b)
            return crypto_utils.deobfuscate_audio(obf, self.session_key, idx)
        except: return None

    def send(self, audio):
        if not self.target or not self.session_key: return
        try:
            idx = self.counter
            obf = crypto_utils.obfuscate_audio(audio, self.session_key, idx)
            nonce = os.urandom(12)
            idx_b = idx.to_bytes(4, 'big')
            ct = self.crypt.encrypt(nonce, obf, associated_data=idx_b)
            self.sock.sendto(nonce + idx_b + ct, self.target)
            self.counter += 1
        except: pass

class LoginScreen(Screen):
    def connect(self):
        url = self.ids.url.text
        user = self.ids.user.text
        if not url or not user: return
        app = App.get_running_app()
        app.um = UserManager(url)
        success, err = app.um.register(user)
        if success: app.root.current = 'lobby'
        else: self.ids.status.text = f"Failed: {err}"

class LobbyScreen(Screen):
    def on_enter(self):
        self.update_list()
        Clock.schedule_interval(self.update_list, 3)
        Clock.schedule_interval(self.check_calls, 2)

    def update_list(self, *args):
        app = App.get_running_app()
        users = app.um.fetch_online_users()
        self.ids.container.clear_widgets()
        for u in users:
            btn = Button(text=f"📞 {u}", size_hint_y=None, height=150)
            btn.bind(on_press=lambda b, name=u: self.call_user(name))
            self.ids.container.add_widget(btn)

    def check_calls(self, *args):
        app = App.get_running_app()
        if app.state == "idle":
            calls = app.um.poll_calls()
            if calls:
                app.incoming_call = calls[0]
                app.root.current = 'incoming'

    def call_user(self, name):
        app = App.get_running_app()
        app.target_name = name
        app.root.current = 'calling'

class CallingScreen(Screen):
    def on_enter(self):
        self.ids.lbl.text = f"Calling {App.get_running_app().target_name}..."
        threading.Thread(target=self.dial_thread, daemon=True).start()

    def dial_thread(self):
        app = App.get_running_app()
        success, call_id, details = app.um.initiate_call(app.target_name)
        if success:
            for _ in range(20):
                if app.um.check_status(call_id) == 'active':
                    Clock.schedule_once(lambda x: app.start_call(details, app.target_name))
                    return
                time.sleep(1)
        Clock.schedule_once(lambda x: setattr(app.root, 'current', 'lobby'))

class IncomingScreen(Screen):
    def on_enter(self):
        self.ids.lbl.text = f"Incoming from {App.get_running_app().incoming_call['caller']}"
    
    def accept(self):
        app = App.get_running_app()
        call = app.incoming_call
        success, details = app.um.accept_call(call['call_id'], call['session_key_ciphertext'])
        if success: app.start_call(details, call['caller'])

class ActiveScreen(Screen):
    timer = StringProperty("00:00")
    def on_enter(self):
        self.start_at = time.time()
        Clock.schedule_interval(self.tick, 1)
    def tick(self, *args):
        dur = int(time.time() - self.start_at)
        self.timer = f"{dur//60:02d}:{dur%60:02d}"
    def end(self):
        App.get_running_app().stop_call()

class PQCApp(App):
    state = StringProperty("idle")
    def build(self):
        self.um = None
        self.net = NetworkHandler()
        self.audio_q = queue.Queue()
        self.running = True
        
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(LobbyScreen(name='lobby'))
        sm.add_widget(CallingScreen(name='calling'))
        sm.add_widget(IncomingScreen(name='incoming'))
        sm.add_widget(ActiveScreen(name='active'))
        return sm

    def start_call(self, details, name):
        ip, port, key = details
        self.net.target = (ip, int(port))
        self.net.session_key = key
        self.net.crypt = AESGCM(key)
        self.state = "active"
        self.root.current = 'active'
        self.net.start(self.on_data)
        if HAS_AUDIO:
            threading.Thread(target=self.audio_thread, daemon=True).start()

    def on_data(self, raw, addr):
        if self.state == "active": self.audio_q.put(raw)

    def audio_thread(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, output=True, frames_per_buffer=1024)
        def speaker():
            while self.state == "active":
                try: stream.write(self.audio_q.get(timeout=0.1))
                except: pass
        threading.Thread(target=speaker, daemon=True).start()
        while self.state == "active":
            try: self.net.send(stream.read(1024, exception_on_overflow=False))
            except: pass
        stream.stop_stream(); stream.close(); p.terminate()

    def stop_call(self):
        self.state = "idle"
        self.root.current = 'lobby'

# Kivy Layout Language
from kivy.lang import Builder
Builder.load_string('''
<LoginScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 50
        spacing: 20
        Label:
            text: 'PQC SECURE VOICE'
            font_size: 40
            color: 0.1, 0.5, 0.9, 1
        TextInput:
            id: url
            text: 'http://192.168.1.7:5001'
            size_hint_y: None
            height: 120
            multiline: False
        TextInput:
            id: user
            hint_text: 'Username'
            size_hint_y: None
            height: 120
            multiline: False
        Button:
            text: 'LOG IN'
            background_color: 0.1, 0.6, 0.3, 1
            on_press: root.connect()
        Label:
            id: status
            text: ''
            color: 1, 0, 0, 1

<LobbyScreen>:
    BoxLayout:
        orientation: 'vertical'
        Label:
            text: 'ONLINE CONTACTS'
            size_hint_y: None
            height: 100
        ScrollView:
            GridLayout:
                id: container
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: 10
                padding: 10

<CallingScreen>:
    BoxLayout:
        orientation: 'vertical'
        Label:
            id: lbl
            text: 'Calling...'

<IncomingScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 50
        Label:
            id: lbl
            text: 'Incoming Call'
        Button:
            text: 'ACCEPT'
            background_color: 0, 1, 0, 1
            on_press: root.accept()
        Button:
            text: 'DECLINE'
            background_color: 1, 0, 0, 1
            on_press: app.root.current = 'lobby'

<ActiveScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 50
        Label:
            text: 'ACTIVE CALL'
            font_size: 30
        Label:
            text: root.timer
            font_size: 60
        Button:
            text: 'HANG UP'
            background_color: 1, 0, 0, 1
            on_press: root.end()
''')

if __name__ == '__main__':
    PQCApp().run()
