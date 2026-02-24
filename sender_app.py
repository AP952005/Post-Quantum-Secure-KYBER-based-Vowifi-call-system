import streamlit as st
import hashlib
import requests
import os
import time
from crypto_utils import (
    kyber_encapsulate, encrypt_audio_chunks, serialize_chunks, 
    save_obfuscated_audio, encrypt_metadata, extract_metadata_from_chunks,
    kyber_generate_keypair
)
from server import send_to_server
from audio_stream import VoiceStream
from call_handler import CallHandler

st.set_page_config(layout="wide")
st.title("🔐 PQC Audio Sender Panel")

# Key registry server URL (read from environment or use localhost default)
DEFAULT_REGISTRY = "http://localhost:5001"
KEY_REGISTRY_URL = os.getenv('REGISTRY_SERVER', DEFAULT_REGISTRY)

st.sidebar.markdown(f"**Registry Server**: {KEY_REGISTRY_URL}")

# Initialize session state variables
if "fetched_receiver_pk" not in st.session_state:
    st.session_state['fetched_receiver_pk'] = None
if "fetched_receiver_username" not in st.session_state:
    st.session_state['fetched_receiver_username'] = None
if "fetched_receiver_ip" not in st.session_state:
    st.session_state['fetched_receiver_ip'] = None
if "fetched_receiver_port" not in st.session_state:
    st.session_state['fetched_receiver_port'] = None
if "encrypted_chunks" not in st.session_state:
    st.session_state['encrypted_chunks'] = None
if "obfuscated_chunks" not in st.session_state:
    st.session_state['obfuscated_chunks'] = None
if "session_key" not in st.session_state:
    st.session_state['session_key'] = None
if "kyber_ciphertext" not in st.session_state:
    st.session_state['kyber_ciphertext'] = None
if "metadata_nonce" not in st.session_state:
    st.session_state['metadata_nonce'] = None
if "metadata_ciphertext" not in st.session_state:
    st.session_state['metadata_ciphertext'] = None

# Voice call session state
if "voice_call_active" not in st.session_state:
    st.session_state['voice_call_active'] = False
    st.session_state['voice_stream'] = None
    st.session_state['call_handler'] = None
    st.session_state['call_id'] = None
    st.session_state['sender_pk'] = None
    st.session_state['sender_sk'] = None
    st.session_state['call_waiting'] = False

# ==============================================================
# VOICE CALL FOCUS - HIDE FILE TRANSFER FOR NOW
# ==============================================================

st.info("📞 **VOICE CALL MODE** - File transfer available in expander below")

# ============================================================
# VOICE CALL SECTION - PRIMARY FOCUS
# ============================================================

st.markdown("---")
st.subheader("📞 Voice Call Discovery")

receiver_username = st.text_input(
    "Enter receiver's username (registered in receiver panel):",
    placeholder="e.g., alice",
    key="receiver_username_input"
)

if receiver_username:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🔍 Fetch Public Key & Address from Registry", key="fetch_key_btn"):
            try:
                response = requests.get(
                    f"{KEY_REGISTRY_URL}/fetch/{receiver_username.strip().lower()}",
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.session_state['fetched_receiver_pk'] = result['public_key']
                    st.session_state['fetched_receiver_username'] = result['username']
                    st.session_state['fetched_receiver_ip'] = result['listening_ip']
                    st.session_state['fetched_receiver_port'] = result['listening_port']
                    st.success(f"✅ Found '{result['username']}'!")
                    st.info(f"📍 Listening at: **{result['listening_address']}**")
                    st.info(f"📅 Registered at: {result['registered_at']}")
                    st.info(f"✅ Ready to send audio")
                else:
                    error_data = response.json()
                    st.error(f"❌ Fetch failed: {error_data.get('message', 'Unknown error')}")
            
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to Key Registry Server at http://localhost:5001")
                st.info("💡 Make sure the server is running: python key_registry_server.py")
                st.info("💡 And receiver has registered their public key")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    with col2:
        # Show list of available users
        if st.button("👥 See Available Users", key="list_users_btn"):
            try:
                response = requests.get(f"{KEY_REGISTRY_URL}/list", timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    st.info(f"**{result['total_users']} user(s) registered:**")
                    for user in result['users']:
                        st.write(f"  • {user['username']} @ {user['listening_address']}")
            except Exception as e:
                st.error(f"Error fetching user list: {str(e)}")
    
    # Show fetched status
    if st.session_state['fetched_receiver_pk']:
        st.success(f"✅ **Ready to call {st.session_state['fetched_receiver_username']}**")

# ============================================================
# OPTIONAL FILE TRANSFER SECTION
# ============================================================
st.markdown("---")
with st.expander("📁 File Transfer (Optional - Audio File Mode)", expanded=False):
    st.info("📤 Upload a WAV file to send via secure encrypted audio stream")
    audio_file = st.file_uploader("Upload a WAV file", type="wav", key="audio_upload_file")
    
    if audio_file and st.session_state['fetched_receiver_pk']:
        receiver_pk = bytes.fromhex(st.session_state['fetched_receiver_pk'])
        
        # Only run encryption once (store in session state)
        if st.session_state['encrypted_chunks'] is None:
            # 1. PQC Encapsulate and Key establishment
            with st.expander("🛡️ 1. Kyber Key Encapsulation (Quantum-Safe Key Exchange)", expanded=True):
                st.write("Using Kyber KEM to generate a secure session key.")
                session_key, ciphertext = kyber_encapsulate(receiver_pk)
                st.session_state['session_key'] = session_key
                st.session_state['kyber_ciphertext'] = ciphertext
                st.code(f"Ciphertext hash: {hashlib.sha256(ciphertext).hexdigest()[:20]}...",
                        language="text")
                st.code(f"Session key hash: {hashlib.sha256(session_key).hexdigest()[:20]}...",
                        language="text")
                st.success("Session key (AES) established via Kyber512! ✅")
            
            # 2. Chunking
            with st.expander("🔊 2. Audio File Chunking"):
                st.info("Splitting uploaded WAV file into fixed-length chunks…")
                encrypted_chunks, obfuscated_chunks = encrypt_audio_chunks(audio_file, session_key)
                st.session_state['encrypted_chunks'] = encrypted_chunks
                st.session_state['obfuscated_chunks'] = obfuscated_chunks
                st.write(f"Audio split into **{len(encrypted_chunks)}** chunks.")
                st.write("First 5 chunks info (bytes each):")
                for idx, chunk in enumerate(encrypted_chunks[:5]):
                    st.write(
                        f"Chunk {idx+1}: {len(chunk[1])} bytes, Nonce: {chunk[0].hex()[:12]}..."
                    )
                st.success("Chunking complete.")

            # 3. AES-GCM Encryption Progress / Log
            with st.expander("🔒 3. AES-GCM Encryption / Packing Progress"):
                st.info("All chunks are encrypted using AES-GCM (authenticated encryption).")
                progress = st.progress(0)
                for idx, chunk in enumerate(encrypted_chunks):
                    if idx < 16 or idx == len(encrypted_chunks)-1:
                        st.write(f"Encrypted chunk {idx+1}/{len(encrypted_chunks)}: {len(chunk[1])} bytes")
                    progress.progress((idx+1)/len(encrypted_chunks))
                st.success("All audio chunks are encrypted and ready for transmission.")

            # 4. Show Obfuscated Audio (Preview of what's being sent)
            with st.expander("🎭 4. Obfuscated Audio Preview (Identity Hidden)"):
                st.info("This is what will be sent - audio identity is obfuscated and unrecognizable")
                obfuscated_audio_path = save_obfuscated_audio(obfuscated_chunks)
                st.audio(obfuscated_audio_path, format="audio/wav")
                st.warning("⚠️ This obfuscated audio will be encrypted before transmission")

            # 5. Metadata Encryption
            with st.expander("🔐 5. Metadata Encryption (PQC Protected)"):
                st.info("Encrypting audio metadata using PQC-derived key...")
                metadata = extract_metadata_from_chunks(encrypted_chunks)
                st.write("**Metadata to be encrypted:**")
                st.json(metadata)
                metadata_nonce, metadata_ciphertext = encrypt_metadata(metadata, session_key)
                st.session_state['metadata_nonce'] = metadata_nonce
                st.session_state['metadata_ciphertext'] = metadata_ciphertext
                st.code(f"Metadata Nonce: {metadata_nonce.hex()[:24]}...", language="text")
                st.code(f"Encrypted Metadata hash: {hashlib.sha256(metadata_ciphertext).hexdigest()[:20]}...", language="text")
                st.success("Metadata encrypted with PQC session key! ✅")
        
        else:
            # Data already encrypted, show summary
            st.info("✅ **Audio already encrypted and ready for transmission**")
            with st.expander("📋 Encryption Summary", expanded=False):
                st.success(f"✓ Kyber encapsulation complete")
                st.success(f"✓ {len(st.session_state['encrypted_chunks'])} audio chunks encrypted")
                st.success(f"✓ Metadata encrypted")
                st.write("Click 'Start Transmission' to send to receiver")

        # 6. Transmission Step/Packet Log
        with st.expander("📨 6. Transmitting All Chunks to Receiver"):
            if st.button("Start Transmission", key="transmit_btn"):
                payload = {
                    'ciphertext': st.session_state['kyber_ciphertext'],
                    'encrypted_chunks': st.session_state['encrypted_chunks'],
                    'metadata_nonce': st.session_state['metadata_nonce'],
                    'metadata_ciphertext': st.session_state['metadata_ciphertext']
                }
                data = serialize_chunks(payload)
                
                # Use auto-fetched IP:port
                server_ip = st.session_state['fetched_receiver_ip']
                server_port = st.session_state['fetched_receiver_port']
                
                st.info(f"📍 Sending to {server_ip}:{server_port}...")
                st.info("Sending data to receiver (this may take a few seconds)...")
                try:
                    send_to_server(data, host=server_ip, port=int(server_port))
                    st.success(f"✅ Transmission complete! **Sent {len(st.session_state['encrypted_chunks'])} chunks + encrypted metadata.**")
                    st.success(f"📍 Sent to: {server_ip}:{server_port}")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Transmission failed: {str(e)}")
                    st.info(f"💡 Make sure receiver is listening on {server_ip}:{server_port}")
    
    elif audio_file and not st.session_state['fetched_receiver_pk']:
        st.warning("⚠️ Please fetch the receiver's public key first (use the 'Fetch Public Key from Registry' button above)")
    else:
        st.info("👆 Upload an audio file and fetch receiver's public key to begin")

# ============================================================
# VOICE CALL SECTION
# ============================================================

if st.session_state['fetched_receiver_username']:
    st.markdown("---")
    st.subheader("📞 Voice Call Interface")
    
    # Ensure sender has Kyber keypair
    if st.session_state['sender_pk'] is None or st.session_state['sender_sk'] is None:
        st.session_state['sender_pk'], st.session_state['sender_sk'] = kyber_generate_keypair()
    
    # Initialize call handler if needed
    if st.session_state['call_handler'] is None:
        # Sender needs a username for call handler
        sender_username = st.text_input("Your username for voice calls:", key="voice_username", placeholder="e.g., bob")
        if sender_username and len(sender_username) >= 2:
            st.session_state['call_handler'] = CallHandler(sender_username, KEY_REGISTRY_URL)
    
    # Display current status
    if not st.session_state['voice_call_active']:
        
        if st.session_state['call_handler'] is None:
            st.info("Enter your username above to enable voice calls")
        else:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"📞 Ready to call **{st.session_state['fetched_receiver_username']}**")
            
            with col2:
                if st.button("📞 Start Voice Call", key="initiate_call_btn"):
                    try:
                        # Encapsulate session key with receiver's public key
                        receiver_pk = bytes.fromhex(st.session_state['fetched_receiver_pk'])
                        session_key, ciphertext = kyber_encapsulate(receiver_pk)
                        st.session_state['session_key'] = session_key
                        
                        # Initiate call
                        call_info = st.session_state['call_handler'].initiate_call(
                            callee_username=st.session_state['fetched_receiver_username'],
                            caller_listen_port=5556,
                            session_key_ciphertext=ciphertext
                        )
                        
                        if call_info:
                            st.session_state['call_id'] = call_info.get('call_id')
                            st.session_state['call_waiting'] = True
                            st.success("📞 Call initiated! Waiting for answer...")
                            st.rerun()
                        else:
                            st.error("Failed to initiate call")
                    
                    except Exception as e:
                        st.error(f"Error initiating call: {e}")
        
        # Show waiting status if call is in progress
        if st.session_state['call_waiting'] and st.session_state['call_id']:
            st.info(f"⏳ Waiting for {st.session_state['fetched_receiver_username']} to answer... (will timeout in 30 seconds)")
            
            # Check if call was answered
            if st.button("🔄 Check Answer Status", key="check_answer_btn"):
                try:
                    call_status = requests.get(
                        f"{KEY_REGISTRY_URL}/call/status/{st.session_state['call_id']}",
                        timeout=5
                    ).json()
                    
                    if call_status.get('status') == 'active':
                        st.success("✅ Call accepted!")
                        
                        # SET STATE FIRST before starting stream
                        st.session_state['voice_call_active'] = True
                        st.session_state['call_waiting'] = False
                        
                        # NOW try to start the voice stream
                        try:
                            stream = VoiceStream(
                                session_key=st.session_state['session_key'],
                                peer_ip=call_status.get('callee_ip'),
                                peer_port=call_status.get('callee_port'),
                                listen_port=5556
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
                    
                    elif call_status.get('status') == 'rejected':
                        st.error("❌ Call was rejected")
                        st.session_state['call_waiting'] = False
                        st.rerun()
                
                except Exception as e:
                    st.error(f"Error checking call status: {e}")
                    import traceback
                    st.error(traceback.format_exc())
    
    else:
        # Active call view
        st.success(f"🟢 **ACTIVE VOICE CALL** with {st.session_state['fetched_receiver_username']}")
        
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
                    st.success("✅ Call ended")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error ending call: {e}")
        
        with audio_column:
            st.info("🎤 Speaking... (your microphone is live)")

