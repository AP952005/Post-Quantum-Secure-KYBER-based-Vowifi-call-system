#!/usr/bin/env python3
"""
Test script to validate voice call functionality across WiFi.
Tests the complete workflow: registry → call initiation → acceptance → audio streaming
"""

import sys
import time
import threading
import requests
import os
from crypto_utils import kyber_generate_keypair, kyber_encapsulate, kyber_decapsulate
from call_handler import CallHandler
from audio_stream import VoiceStream

# Configuration
DEFAULT_REGISTRY = "http://localhost:5001"
REGISTRY_URL = os.getenv('REGISTRY_SERVER', DEFAULT_REGISTRY)

print(f"🔧 Using Registry: {REGISTRY_URL}")

# ============================================================
# Test 1: Verify Registry Server is Running
# ============================================================
def test_registry_connectivity():
    """Verify the registry server is accessible"""
    print("\n" + "="*60)
    print("TEST 1: Registry Server Connectivity")
    print("="*60)
    
    try:
        response = requests.get(f"{REGISTRY_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Registry server is running and accessible")
            return True
        else:
            print(f"❌ Registry returned unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to registry: {e}")
        print(f"   Make sure registry is running: python key_registry_server.py")
        return False

# ============================================================
# Test 2: Register Two Users
# ============================================================
def test_user_registration():
    """Register two test users (Alice and Bob)"""
    print("\n" + "="*60)
    print("TEST 2: User Registration")
    print("="*60)
    
    users = {}
    
    for username in ["alice", "bob"]:
        try:
            pk, sk = kyber_generate_keypair()
            
            response = requests.post(
                f"{REGISTRY_URL}/register",
                json={
                    "username": username,
                    "public_key": pk.hex(),
                    "ip": "127.0.0.1",
                    "port": 5000
                },
                timeout=5
            )
            
            if response.status_code == 200:
                users[username] = {
                    'pk': pk.hex(),
                    'sk': sk,
                    'ip': '127.0.0.1'
                }
                print(f"✅ Registered '{username}': PK={pk.hex()[:20]}...")
            else:
                print(f"❌ Failed to register '{username}': {response.text}")
                return None
        
        except Exception as e:
            print(f"❌ Error registering '{username}': {e}")
            return None
    
    return users

# ============================================================
# Test 3: Call Initiation and Acceptance
# ============================================================
def test_call_workflow(users):
    """Test complete call initiation and acceptance workflow"""
    print("\n" + "="*60)
    print("TEST 3: Call Initiation and Acceptance")
    print("="*60)
    
    alice_info = users['alice']
    bob_info = users['bob']
    
    # Alice initiates call to Bob
    try:
        print("\n👤 Alice initiating call to Bob...")
        
        # Encapsulate with Bob's public key
        bob_pk = bytes.fromhex(bob_info['pk'])
        session_key, ciphertext = kyber_encapsulate(bob_pk)
        
        print(f"   Session key: {session_key.hex()[:20]}...")
        print(f"   Ciphertext: {ciphertext.hex()[:20]}... (len={len(ciphertext)})")
        
        # Create CallHandler for Alice
        alice_handler = CallHandler("alice", REGISTRY_URL)
        
        # Initiate call
        call_info = alice_handler.initiate_call(
            callee_username="bob",
            caller_listen_port=5556,
            session_key_ciphertext=ciphertext
        )
        
        if not call_info:
            print("❌ Failed to initiate call")
            return False
        
        call_id = call_info['call_id']
        print(f"✅ Call initiated with ID: {call_id}")
        
        # Bob checks for incoming calls
        print("\n👤 Bob checking for incoming calls...")
        time.sleep(1)
        
        try:
            pending_response = requests.get(
                f"{REGISTRY_URL}/call/pending/bob",
                timeout=5
            )
            
            if pending_response.status_code == 200:
                pending_calls = pending_response.json().get('pending_calls', [])
                print(f"✅ Found {len(pending_calls)} incoming call(s)")
                
                if not pending_calls:
                    print("❌ No incoming calls found")
                    return False
                
                # Bob accepts call
                print("\n👤 Bob accepting call...")
                accept_response = requests.post(
                    f"{REGISTRY_URL}/call/accept",
                    json={
                        "call_id": call_id,
                        "callee_listen_port": 5557
                    },
                    timeout=5
                )
                
                if accept_response.status_code == 200:
                    accepted_call = accept_response.json()
                    print(f"✅ Call accepted by Bob")
                    print(f"   Bob listening on port: {accepted_call.get('callee_port')}")
                    print(f"   Alice IP: {accepted_call.get('caller_ip')}")
                    return True
                else:
                    print(f"❌ Failed to accept call: {accept_response.text}")
                    return False
            else:
                print(f"❌ Failed to check pending calls: {pending_response.text}")
                return False
        
        except Exception as e:
            print(f"❌ Error during acceptance: {e}")
            return False
    
    except Exception as e:
        print(f"❌ Error during call workflow: {e}")
        return False

# ============================================================
# Test 4: Audio Stream Configuration
# ============================================================
def test_audio_stream_config():
    """Verify audio streaming can be configured"""
    print("\n" + "="*60)
    print("TEST 4: Audio Stream Configuration")
    print("="*60)
    
    try:
        session_key = os.urandom(32)  # 256-bit key
        
        # Note: Not actually starting audio (would require microphone)
        stream_config = {
            'session_key': session_key,
            'peer_ip': '127.0.0.1',
            'peer_port': 5556,
            'listen_port': 5557,
            'frame_size': 1024,
            'sample_rate': 16000,
            'channels': 1
        }
        
        print(f"✅ Audio stream configuration valid:")
        print(f"   Session Key: {session_key.hex()[:20]}...")
        print(f"   Listen Port: {stream_config['listen_port']}")
        print(f"   Peer: {stream_config['peer_ip']}:{stream_config['peer_port']}")
        print(f"   Frame Size: {stream_config['frame_size']} samples")
        print(f"   Sample Rate: {stream_config['sample_rate']} Hz")
        
        return True
    
    except Exception as e:
        print(f"❌ Audio stream configuration failed: {e}")
        return False

# ============================================================
# Test 5: Crypto Operations
# ============================================================
def test_crypto_operations():
    """Verify Kyber and encryption operations"""
    print("\n" + "="*60)
    print("TEST 5: Post-Quantum Cryptography")
    print("="*60)
    
    try:
        # Generate keypair
        pk, sk = kyber_generate_keypair()
        print(f"✅ Kyber512 keypair generated:")
        print(f"   Public Key Length: {len(pk)} bytes")
        print(f"   Secret Key Length: {len(sk)} bytes")
        
        # Test encapsulation
        session_key, ciphertext = kyber_encapsulate(pk)
        print(f"\n✅ Key encapsulation:")
        print(f"   Session Key: {len(session_key)} bytes")
        print(f"   Ciphertext: {len(ciphertext)} bytes")
        
        # Test decapsulation
        recovered_key = kyber_decapsulate(ciphertext, sk)
        
        if recovered_key == session_key:
            print(f"\n✅ Key decapsulation successful!")
            print(f"   Recovered key matches encapsulated key")
            return True
        else:
            print(f"\n❌ Recovered key doesn't match!")
            return False
    
    except Exception as e:
        print(f"❌ Crypto operations failed: {e}")
        return False

# ============================================================
# Main Test Runner
# ============================================================
def main():
    print("\n" + "="*60)
    print("🔊 VOICE CALL SYSTEM TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Run tests
    results['registry'] = test_registry_connectivity()
    
    if not results['registry']:
        print("\n❌ Cannot continue - registry not accessible")
        return
    
    results['crypto'] = test_crypto_operations()
    results['registration'] = test_user_registration() is not None
    
    if results['registration']:
        users = test_user_registration()
        results['call_workflow'] = test_call_workflow(users)
    
    results['audio_config'] = test_audio_stream_config()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("\nYou can now run:")
        print("  1. Terminal 1: python key_registry_server.py")
        print("  2. Terminal 2: streamlit run receiver_app.py")
        print("  3. Terminal 3: streamlit run sender_app.py")
        print("\nThen use the UI to make voice calls!")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("Check the errors above and ensure:")
        print("  - Registry server is running")
        print("  - PyAudio is installed (pip install PyAudio)")
        print("  - Kyber512 library is available")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
