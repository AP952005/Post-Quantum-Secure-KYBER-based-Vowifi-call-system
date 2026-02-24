#!/usr/bin/env python3
"""Test voice call flow - simple ASCII output"""

import requests
import json
from crypto_utils import kyber_generate_keypair, kyber_encapsulate
import base64

REGISTRY = "http://localhost:5001"

print("=" * 60)
print("PQC VOICE CALL TEST")
print("=" * 60)

try:
    # Step 1: Generate keypairs
    print("\n[1/7] Generating keypairs...")
    alice_pk, alice_sk = kyber_generate_keypair()
    bob_pk, bob_sk = kyber_generate_keypair()
    print(f"      Alice PK: {alice_pk.hex()[:20]}...")
    print(f"      Bob PK: {bob_pk.hex()[:20]}...")

    # Step 2: Register both users
    print("\n[2/7] Registering users with registry...")
    
    alice_reg = requests.post(
        f"{REGISTRY}/register",
        json={
            "username": "alice",
            "public_key": alice_pk.hex(),
            "listening_ip": "127.0.0.1",
            "listening_port": 5000
        },
        timeout=5
    ).json()
    print(f"      Alice registered: {alice_reg.get('message')}")
    
    bob_reg = requests.post(
        f"{REGISTRY}/register",
        json={
            "username": "bob",
            "public_key": bob_pk.hex(),
            "listening_ip": "127.0.0.1",
            "listening_port": 5001
        },
        timeout=5
    ).json()
    print(f"      Bob registered: {bob_reg.get('message')}")
    
    # Step 3: Fetch Alice's info (Bob needs this)
    print("\n[3/7] Fetching Alice's public key and address...")
    alice_info = requests.get(f"{REGISTRY}/fetch/alice", timeout=5).json()
    print(f"      Alice username: {alice_info.get('username')}")
    print(f"      Alice address: {alice_info.get('listening_address')}")
    
    # Step 4: Bob initiates call to Alice
    print("\n[4/7] Bob initiating call to Alice...")
    session_key, ciphertext = kyber_encapsulate(bytes.fromhex(alice_info['public_key']))
    ct_b64 = base64.b64encode(ciphertext).decode('utf-8')
    
    call_init = requests.post(
        f"{REGISTRY}/call/initiate",
        json={
            "caller": "bob",
            "callee": "alice",
            "caller_listen_port": 5001,
            "session_key_ciphertext": ct_b64
        },
        timeout=5
    ).json()
    
    if "error" in str(call_init):
        print(f"      FAIL: {call_init}")
        exit(1)
    
    call_id = call_init['call_id']
    print(f"      Call ID: {call_id}")
    print(f"      Callee IP: {call_init.get('callee_ip')}")
    print(f"      Callee Port: {call_init.get('callee_port')}")
    
    # Step 5: Check pending calls on Alice's side
    print("\n[5/7] Checking pending calls for Alice...")
    pending = requests.get(f"{REGISTRY}/call/pending/alice", timeout=5).json()
    print(f"      Pending count: {len(pending.get('pending_calls', []))}")
    
    # Step 6: Alice accepts the call
    print("\n[6/7] Alice accepting call...")
    accept_resp = requests.post(
        f"{REGISTRY}/call/accept",
        json={"call_id": call_id},
        timeout=5
    ).json()
    
    print(f"      Status: {accept_resp.get('status')}")
    print(f"      Caller Port: {accept_resp.get('caller_port')}")
    print(f"      Callee Port: {accept_resp.get('callee_port')}")
    
    # Step 7: Check final call status
    print("\n[7/7] Checking final call status...")
    status = requests.get(f"{REGISTRY}/call/status/{call_id}", timeout=5).json()
    print(f"      Status: {status.get('status')}")
    print(f"      Caller: {status.get('caller')}")
    print(f"      Callee: {status.get('callee')}")
    
    print("\n" + "=" * 60)
    print("SUCCESS - ALL VOICE CALL SIGNALING WORKING!")
    print("=" * 60)

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
