# Multi-System Voice Call Setup Guide

## Overview

This guide explains how to run the PQC voice call system across **2 different machines** on a local network.

---

## Architecture

```
┌─────────────────────────────┐       ┌─────────────────────────────┐
│   SYSTEM A (Receiver)       │       │   SYSTEM B (Sender)         │
│   IP: 192.168.1.100         │       │   IP: 192.168.1.101         │
├─────────────────────────────┤       ├─────────────────────────────┤
│ ✅ Key Registry (port 5001) │       │ Sender App (port 8502)      │
│ ✅ Receiver App (port 8501) │◄─────►│                             │
│ Listens: 192.168.1.100:5000 │       │ Audio P2P Connection        │
└─────────────────────────────┘       └─────────────────────────────┘
```

### Design Principles

- **Registry**: Runs on System A (receiver's machine) - acts as discovery service
- **Audio**: P2P direct connection between systems - registry never touches audio data
- **Port 5001**: Registry server (HTTP for metadata/discovery)
- **Port 5000**: Audio listener (receiver system only)
- **Ports 8501/8502**: Streamlit web UIs (local access only)

---

## Step 1: Find Your Machine IPs

### On System A (Receiver):
```powershell
ipconfig
```
Look for **IPv4 Address** under your network adapter (e.g., `192.168.1.100`)

### On System B (Sender):
```powershell
ipconfig
```
Note your IP (e.g., `192.168.1.101`)

---

## Step 2: Prepare System A (Receiver)

### 2a. Start the Registry Server

On System A, run:
```powershell
cd C:\Users\Lenovo\Desktop\50_pqvoice
set REGISTRY_HOST=0.0.0.0
set REGISTRY_PORT=5001
python key_registry_server.py
```

**Expected output:**
```
============================================================
🔐 PQC Key Registry Server
============================================================
Binding to 0.0.0.0:5001
API Documentation available at http://localhost:5001
For remote access, use your machine IP (check 'ipconfig')
============================================================
```

⚠️ **Leave this terminal open** - it must stay running.

### 2b. Start the Receiver App

Open a **new terminal** on System A:
```powershell
cd C:\Users\Lenovo\Desktop\50_pqvoice
set REGISTRY_SERVER=http://192.168.1.100:5001
streamlit run receiver_app.py --server.port=8501
```

**Note:** Replace `192.168.1.100` with System A's actual IP from Step 1.

**Expected output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
```

✅ **Keep this running.**

---

## Step 3: Prepare System B (Sender)

### 3a. Start the Sender App

On System B, open a terminal:
```powershell
cd C:\Users\Lenovo\Desktop\50_pqvoice
set REGISTRY_SERVER=http://192.168.1.100:5001
streamlit run sender_app.py --server.port=8502
```

**Note:** Replace `192.168.1.100` with System A's IP address (not System B's).

**Expected output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8502
```

✅ **Keep this running.**

---

## Step 4: Test the Connection

### 4a. Verify Registry is Accessible from System B

On System B, open PowerShell:
```powershell
curl http://192.168.1.100:5001
```

**Expected output:**
```
{"api_version":"1.0","status":"healthy","description":"PQC Key Registry Server ..."}
```

If this fails:
- ❌ Check System A's IP is correct
- ❌ Ensure registry server is running (Step 2a)
- ❌ Check Windows Firewall isn't blocking port 5001

### 4b. Register Receiver (on System A's Streamlit)

1. Open browser: `http://localhost:8501` (on System A)
2. Enter username (e.g., **alice**)
3. Click **"🔗 Register Public Key to Server"**
4. Should see: **"✅ Registered as alice @ 192.168.1.100:5000"**

### 4c. Send Audio from System B (on System B's Streamlit)

1. Open browser: `http://localhost:8502` (on System B)
2. Upload a WAV file
3. Enter receiver username: **alice**
4. Click **"🔍 Fetch Public Key & Address from Registry"**
5. Should see receiver's public key and address appear
6. Click **"🔄 Encrypt & Send to Receiver"**
7. Should see: **"✅ Audio sent successfully!"**

### 4d. Receive Audio on System A

On System A's receiver app, you should see:
- **"📥 Received encrypted audio from sender"**
- Obfuscated audio preview (unrecognizable noise)
- Final audio playback (original voice)

---

## Step 5: Troubleshooting

### Registry Connection Failed

```
⚠️ Error: Failed to fetch from registry
```

**Fix:**
1. Verify System A's registry is running: `python key_registry_server.py`
2. Test connection from System B: `curl http://[SystemA_IP]:5001`
3. Check System A's IP is correct (use `ipconfig`)
4. Ensure Windows Firewall allows port 5001

### Audio Send Failed

```
⚠️ Error: Failed to send audio to receiver
```

**Fix:**
1. Verify receiver is registered in registry (check Step 4b)
2. Verify receiver app is running on System A
3. Check receiver IP and port in registry match receiver's listening settings

### Firewall Issues

On System A, allow ports through Windows Firewall:

```powershell
netsh advfirewall firewall add rule name="PQC Registry" dir=in action=allow protocol=tcp localport=5001
netsh advfirewall firewall add rule name="PQC Audio" dir=in action=allow protocol=tcp localport=5000
```

---

## Step 6: Environment Variable Quick Reference

### System A (Receiver)

```powershell
# Terminal 1: Registry Server
set REGISTRY_HOST=0.0.0.0
set REGISTRY_PORT=5001
python key_registry_server.py

# Terminal 2: Receiver App
set REGISTRY_SERVER=http://192.168.1.100:5001
streamlit run receiver_app.py --server.port=8501
```

### System B (Sender)

```powershell
set REGISTRY_SERVER=http://192.168.1.100:5001
streamlit run sender_app.py --server.port=8502
```

---

## Network Diagram: Data Flow

```
System B (Sender)                Registry Server (SystemA:5001)              System A (Receiver)
─────────────────                ──────────────────────────────              ───────────────────

[User uploads audio]
        │
        ├──► Enter username "alice"
        │
        └──► GET /fetch/alice ────────────────────────────────────┐
                                                                    │
                                         [Lookup alice in registry] │
                                                                    ▼
             ◄────────────────────────── Returns:                  │
             │                           - public_key              │
             │                           - listening_ip: 192.168.1.100
             │                           - listening_port: 5000
             │
             ▼
        [Encrypt audio with Kyber512 + AES-GCM]
             │
             ├─────────────────────────────────────────────────────────────────────────────┐
             │                                                                              │
             │  TCP Connection: System B → 192.168.1.100:5000                              │
             │                                                                              │
             └─────────────────────────────────────────────────────────────────────────────►
                                                                             (Listening)
                                                                              │
                                                                              ▼
                                                                   [Receive encrypted data]
                                                                              │
                                                                              ▼
                                                                   [Decrypt with Kyber512]
                                                                              │
                                                                              ▼
                                                                   [De-obfuscate audio]
                                                                              │
                                                                              ▼
                                                                   [Play audio to speaker]
```

---

## Verification Checklist

- [ ] System A IP confirmed (ipconfig)
- [ ] System B IP confirmed (ipconfig)
- [ ] Registry running on System A (port 5001)
- [ ] Receiver app running on System A (port 8501)
- [ ] Sender app running on System B (port 8502)
- [ ] Curl test succeeds: `curl http://[SystemA_IP]:5001`
- [ ] Receiver registered in registry
- [ ] Sender can fetch receiver details
- [ ] Audio sent successfully
- [ ] Audio received and played

---

## Notes

- **Same Network Required**: Both systems must be on the same WiFi or local network
- **Registry Always on Receiver System**: Receiver hosts registry for P2P discovery
- **Port Forwarding**: Not needed for local network; only if accessing across internet
- **Firewall**: May need to allow port 5001 and 5000 through Windows Firewall

