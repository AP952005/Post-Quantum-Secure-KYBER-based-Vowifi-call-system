import streamlit as st
import hashlib
import requests
import socket
import os
import time
import threading
from datetime import datetime
from crypto_utils import (
    kyber_generate_keypair, kyber_decapsulate,
    decrypt_audio_chunks, deserialize_chunks, decrypt_and_show_obfuscated,
    decrypt_metadata
)
from server import start_server
from audio_stream import VoiceStream
from call_handler import CallHandler

st.set_page_config(layout="wide")
st.title("🔑 PQC Audio Receiver Panel")

# Key registry server URL (read from environment or use localhost default)
DEFAULT_REGISTRY = "http://localhost:5001"
KEY_REGISTRY_URL = os.getenv('REGISTRY_SERVER', DEFAULT_REGISTRY)

st.sidebar.markdown(f"**Registry Server**: {KEY_REGISTRY_URL}")

# Initialize session state variables
if "receiver_pk" not in st.session_state:
    st.session_state['receiver_pk'] = None
    st.session_state['receiver_sk'] = None
    st.session_state['registered_username'] = None
    st.session_state['registered_address'] = None

# Voice call session state
if "voice_call_active" not in st.session_state:
    st.session_state['voice_call_active'] = False
    st.session_state['voice_stream'] = None
    st.session_state['call_handler'] = None
    st.session_state['caller_info'] = None

def get_local_ip():
    """Get the machine's local IP address on the network."""
    try:
        # Connect to a public DNS server (doesn't actually connect, just gets the IP)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# Get local IP
local_ip = get_local_ip()

# UI Layout
st.markdown("---")
st.subheader("🛡️ 1. Kyber Keypair Setup & Auto-Register")

col1, col2 = st.columns([2, 2])

with col1:
    if st.button("Generate Receiver Kyber Keypair", key="gen_key"):
        pk, sk = kyber_generate_keypair()
        st.session_state['receiver_pk'] = pk
        st.session_state['receiver_sk'] = sk
        st.success("✅ Keypair generated!")

with col2:
    st.write("")
    st.write("")
    st.info(f"📍 Your local IP: **{local_ip}**")

if st.session_state['receiver_pk'] is not None and st.session_state['receiver_sk'] is not None:
    st.markdown("---")
    st.subheader("📝 Register with Key Registry Server")
    
    # Username and port inputs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        username = st.text_input(
            "Choose a username (e.g., alice, bob):",
            placeholder="username",
            key="receiver_username"
        )
    
    with col2:
        listening_port = st.number_input(
            "Listening Port:",
            value=5000,
            min_value=1024,
            max_value=65535,
            step=1,
            key="receiver_port"
        )
    
    with col3:
        st.write("")
        st.write("")
        display_ip = local_ip
        st.text_input("Listening IP (Auto-detected):", value=display_ip, disabled=True)
    
    # Register button
    if st.button("🔗 Register Public Key to Server", key="register_btn"):
        if not username or len(username) < 2:
            st.error("❌ Username must be at least 2 characters")
        else:
            # Try to register with server
            try:
                response = requests.post(
                    f"{KEY_REGISTRY_URL}/register",
                    json={
                        "username": username.strip().lower(),
                        "public_key": st.session_state['receiver_pk'].hex(),
                        "listening_ip": local_ip,
                        "listening_port": int(listening_port)
                    },
                    timeout=5
                )
                
                if response.status_code == 201:
                    result = response.json()
                    st.session_state['registered_username'] = result['username']
                    st.session_state['registered_address'] = result['listening_address']
                    st.success(f"✅ {result['message']}")
                    st.info(f"📅 Registered at: {result['timestamp']}")
                    st.info(f"📢 Tell the sender to use username: **{result['username']}**")
                    st.info(f"📍 You are listening on: **{result['listening_address']}**")
                else:
                    error_data = response.json()
                    st.error(f"❌ Registration failed: {error_data.get('message', 'Unknown error')}")
            
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to Key Registry Server at http://localhost:5001")
                st.info("💡 Make sure the server is running: python key_registry_server.py")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    # Show registration status
    if st.session_state['registered_username']:
        st.markdown("---")
        st.success(f"✅ **Registered as:** '{st.session_state['registered_username']}'")
        st.success(f"✅ **Listening on:** {st.session_state['registered_address']}")
        st.info("👂 Ready to receive audio. Waiting for sender to connect...")

if st.session_state['receiver_pk'] is not None and st.session_state['receiver_sk'] is not None:
    exp2 = st.expander("📡 2. Listen and Receive Data (Wait for Sender)")
    exp3 = st.expander("📦 3. Process Incoming Packets / PQC Decapsulation")
    exp4 = st.expander("� 4. Decrypt Metadata (PQC Protected)")
    exp5 = st.expander("🔐 5. AES-GCM Chunk Decryption")
    exp6 = st.expander("🎭 6. Obfuscated Audio (Identity Hidden)")
    exp7 = st.expander("🔊 7. Final Decrypted Audio (De-obfuscated)")

    if exp2.button("Listen for Incoming Transmission"):
        # Determine listening address
        listen_ip = local_ip  # Use auto-detected IP
        listen_port = 5000   # Default port for audio
        
        exp2.info(f"Listening on {listen_ip}:{listen_port}...")
        data = start_server(host=listen_ip, port=listen_port)
        exp2.success("Data received!")

        payload = deserialize_chunks(data)
        ciphertext = payload['ciphertext']
        encrypted_chunks = payload['encrypted_chunks']
        metadata_nonce = payload.get('metadata_nonce')
        metadata_ciphertext = payload.get('metadata_ciphertext')

        # Processing - PQC Decapsulation
        exp3.code(f"Received Ciphertext hash: {hashlib.sha256(ciphertext).hexdigest()[:20]}...", language="text")
        session_key = kyber_decapsulate(ciphertext, st.session_state['receiver_sk'])
        exp3.code(f"Recovered session key hash: {hashlib.sha256(session_key).hexdigest()[:20]}...", language="text")
        exp3.success("Decapsulated (quantum-safe) session key!")

        # Decrypt Metadata
        if metadata_nonce and metadata_ciphertext:
            exp4.info("🔓 Decrypting audio metadata using PQC session key...")
            try:
                metadata = decrypt_metadata(metadata_nonce, metadata_ciphertext, session_key)
                exp4.write("**Decrypted Metadata:**")
                exp4.json(metadata)
                exp4.success("Metadata decrypted successfully! ✅")
            except Exception as e:
                exp4.error(f"Failed to decrypt metadata: {str(e)}")
                metadata = {}
        else:
            exp4.warning("⚠️ No metadata found in transmission")
            metadata = {}

        # Decryption
        exp5.info(f"Decrypting **{len(encrypted_chunks)}** audio chunks…")
        progress = exp5.progress(0)
        for idx, chunk in enumerate(encrypted_chunks):
            if idx < 16 or idx == len(encrypted_chunks)-1:
                exp5.write(
                    f"Decrypting chunk {idx+1}/{len(encrypted_chunks)}: Nonce: {chunk[0].hex()[:12]}..."
                )
            progress.progress((idx+1)/len(encrypted_chunks))
        exp5.success(f"Decryption complete!")

        # Show obfuscated audio (unrecognizable)
        exp6.warning("⚠️ This is the received audio with obfuscation applied - NOT human or AI understandable")
        obfuscated_path = decrypt_and_show_obfuscated(encrypted_chunks, session_key)
        exp6.audio(obfuscated_path, format="audio/wav")
        exp6.info("Identity is hidden - audio is unrecognizable without the session key")

        # Show final de-obfuscated audio
        exp7.info("De-obfuscating and reconstructing original audio...")
        output_path = decrypt_audio_chunks(encrypted_chunks, session_key)
        exp7.success(f"Decryption complete — audio file reconstructed as {output_path}")
        exp7.audio(output_path, format="audio/wav")
        exp7.success("Decrypted, authenticated, and reconstructed audio! ✅")


# ============================================================
# VOICE CALL SECTION
# ============================================================

if st.session_state['registered_username']:
    st.markdown("---")
    st.subheader("📞 Voice Call Interface")
    
    # Initialize call handler if needed
    if st.session_state['call_handler'] is None:
        st.session_state['call_handler'] = CallHandler(
            st.session_state['registered_username'],
            KEY_REGISTRY_URL
        )
    
    # Display current status
    if not st.session_state['voice_call_active']:
        st.info("👂 Ready to receive voice calls. Listening for incoming calls...")
        
        # Polling for incoming calls
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("**Waiting for incoming calls...**")
        with col2:
            if st.button("🔄 Check for Calls", key="check_calls"):
                try:
                    # Query registry for pending calls to this user
                    response = requests.get(
                        f"{KEY_REGISTRY_URL}/call/pending/{st.session_state['registered_username']}",
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        pending_calls = response.json().get('pending_calls', [])
                        
                        if pending_calls:
                            st.info(f"📞 Found {len(pending_calls)} incoming call(s)!")
                            
                            for call in pending_calls:
                                call_id = call['call_id']
                                caller = call['caller']
                                
                                st.write(f"**Incoming call from: {caller}**")
                                
                                call_col1, call_col2 = st.columns(2)
                                
                                with call_col1:
                                    if st.button(f"✅ Accept", key=f"accept_{call_id}"):
                                        try:
                                            # Get receiver keypair for Kyber encapsulation
                                            if st.session_state['receiver_pk'] is None:
                                                st.session_state['receiver_pk'], st.session_state['receiver_sk'] = kyber_generate_keypair()
                                            
                                            # Accept call at registry
                                            accept_response = requests.post(
                                                f"{KEY_REGISTRY_URL}/call/accept",
                                                json={
                                                    "call_id": call_id,
                                                    "callee_listen_port": 5557
                                                },
                                                timeout=5
                                            )
                                            
                                            if accept_response.status_code == 200:
                                                call_info = accept_response.json()
                                                
                                                # Extract ciphertext and decapsulate to get session key
                                                ciphertext = bytes.fromhex(call_info['session_key_ciphertext'])
                                                session_key = kyber_decapsulate(ciphertext, st.session_state['receiver_sk'])
                                                
                                                # SET STATE FIRST - mark call as active before starting stream
                                                st.session_state['voice_call_active'] = True
                                                st.session_state['caller_info'] = {'caller': caller, 'call_id': call_id}
                                                st.success("✅ Call accepted!")
                                                
                                                # NOW try to start the voice stream
                                                try:
                                                    stream = VoiceStream(
                                                        session_key=session_key,
                                                        peer_ip=call_info['caller_ip'],
                                                        peer_port=call_info['caller_port'],
                                                        listen_port=5557
                                                    )
                                                    
                                                    stream.start_call()
                                                    st.session_state['voice_stream'] = stream
                                                    st.success("✅ Audio stream started!")
                                                except Exception as stream_error:
                                                    st.warning(f"⚠️ Audio stream error: {stream_error}")
                                                    st.info("Call is active but audio may not be working")
                                                    import traceback
                                                    st.error(traceback.format_exc())
                                                
                                                st.rerun()
                                            else:
                                                st.error(f"Failed to accept call: {accept_response.text}")
                                        
                                        except Exception as e:
                                            st.error(f"❌ Error accepting call: {e}")
                                            import traceback
                                            st.error(traceback.format_exc())
                                
                                with call_col2:
                                    if st.button(f"❌ Reject", key=f"reject_{call_id}"):
                                        try:
                                            requests.post(
                                                f"{KEY_REGISTRY_URL}/call/reject",
                                                json={"call_id": call_id},
                                                timeout=5
                                            )
                                            st.info("Call rejected")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error rejecting call: {e}")
                        else:
                            st.info("No incoming calls at this moment")
                
                except Exception as e:
                    st.error(f"Error checking for calls: {e}")
    
    else:
        # Active call view
        st.success(f"🟢 **ACTIVE VOICE CALL** with {st.session_state['caller_info'].get('caller', 'Unknown')}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Frames Sent", st.session_state['voice_stream'].tx_frame_num)
        
        with col2:
            st.metric("Frames Received", st.session_state['voice_stream'].rx_frame_num)
        
        with col3:
            st.metric("Queue Size", len(st.session_state['voice_stream'].audio_queue))
        
        audio_column, button_column = st.columns([2, 1])
        
        with button_column:
            st.write("")
            st.write("")
            if st.button("❌ End Call", key="end_call_btn"):
                try:
                    st.session_state['voice_stream'].end_call()
                    st.session_state['call_handler'].end_call()
                    st.session_state['voice_call_active'] = False
                    st.session_state['voice_stream'] = None
                    st.session_state['caller_info'] = None
                    st.success("✅ Call ended")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error ending call: {e}")
        
        with audio_column:
            st.info("🎤 Speaking... (your microphone is live)")


