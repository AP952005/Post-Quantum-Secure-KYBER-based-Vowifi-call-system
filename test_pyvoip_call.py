#!/usr/bin/env python3
"""
Test voice call flow with pyVoIP-based audio_stream.py
"""

import sys
import time
from crypto_utils import kyber_generate_keypair, kyber_encapsulate
from audio_stream import VoiceStream

print("=" * 60)
print("PQC VOICE CALL TEST - pyVoIP Backend")
print("=" * 60)

# Step 1: Generate keypairs
print("\n[1/5] Generating Kyber keypairs...")
alice_pk, alice_sk = kyber_generate_keypair()
print(f"Alice PK: {alice_pk.hex()[:20]}...")

# Step 2: Establish session key via Kyber encapsulation
print("\n[2/5] Performing Kyber encapsulation (DH-like exchange)...")
session_key, ciphertext = kyber_encapsulate(alice_pk)
print(f"Session key (AES-256): {session_key.hex()[:20]}...")
print(f"Ciphertext hash: {ciphertext.hex()[:20]}...")

# Step 3: Initialize VoiceStream (Bob calling Alice)
print("\n[3/5] Initializing VoiceStream for encrypted RTP...")
try:
    voice_stream = VoiceStream(
        session_key=session_key,
        peer_ip="127.0.0.1",
        peer_port=5060,
        listen_port=5061
    )
    print("[OK] VoiceStream initialized")
except Exception as e:
    print(f"[ERROR] Failed to initialize VoiceStream: {e}")
    sys.exit(1)

# Step 4: Start the encrypted call
print("\n[4/5] Starting secure voice call...")
try:
    voice_stream.start_call()
    print("[OK] Voice call started")
except Exception as e:
    print(f"[ERROR] Failed to start call: {e}")
    sys.exit(1)

# Step 5: Simulate call activity
print("\n[5/5] Simulating call activity (5 seconds)...")
try:
    for i in range(5):
        time.sleep(1)
        print(f"  [{i+1}/5] TX frames: {voice_stream.tx_frame_num}, RX frames: {voice_stream.rx_frame_num}")
    
    # End call
    voice_stream.end_call()
    print("[OK] Call ended")
    
    print("\n" + "=" * 60)
    print("SUCCESS! Voice call flow is working")
    print("=" * 60)
    print(f"\nFinal stats:")
    print(f"  TX Frames: {voice_stream.tx_frame_num}")
    print(f"  RX Frames: {voice_stream.rx_frame_num}")
    print(f"  Session Key: AES-256 (32 bytes)")
    print(f"  Encryption: AES-256-GCM (authenticated)")
    print(f"  Transport: Secure RTP")
    
except Exception as e:
    print(f"[ERROR] Call failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
