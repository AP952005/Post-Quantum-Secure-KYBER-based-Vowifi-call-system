# 🔐 PQC Audio - College Project Setup Guide

## Overview

PQC Audio is a quantum-safe audio communication system that:
- ✅ Encrypts audio using **Kyber512** (post-quantum cryptography)
- ✅ Obfuscates audio identity so the sender cannot be identified
- ✅ Encrypts metadata to prevent information leakage
- ✅ Uses automatic key exchange via local **Key Registry Server** (no manual copy-paste!)

---

## System Architecture

```
┌──────────────────────────────────────────────────┐
│  Your Local Machine (Laptop/PC)                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Key Registry Server (Flask)             │   │
│  │  localhost:5001                          │   │
│  │  - Stores username ↔ public_key mappings│   │
│  │  - Auto-fetches keys for senders        │   │
│  └──────────────────────────────────────────┘   │
│           ▲            ▲                        │
│           │            │                        │
│      ┌────┴────┐  ┌────┴────┐                   │
│      │ Receiver │  │ Sender  │                   │
│      │ App      │  │ App     │                   │
│      │ :8501   │  │ :8502  │                   │
│      └──────────┘  └─────────┘                   │
│      (Streamlit) (Streamlit)                    │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## Installation & Setup

### Step 1: Install Python Dependencies

Make sure you have Python 3.7+ installed, then install requirements:

```bash
cd c:\Users\Lenovo\Desktop\50_pqvoice
pip install -r requirements.txt
```

**Required packages:**
- `streamlit` - Web UI framework
- `cryptography` - AES-GCM encryption
- `pydub` - Audio processing (requires ffmpeg)
- `pypqc` - Kyber512 post-quantum cryptography
- `flask` - Key registry server
- `requests` - HTTP client for apps

### Step 2: Install FFmpeg (for pydub)

**Windows:**
```bash
# Using choco (if installed)
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
# Then add to PATH
```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### Step 3: Verify Installation

Test that all imports work:
```bash
python -c "import streamlit; import flask; import cryptography; from pydub import AudioSegment; from pqc.kem import kyber512; print('✅ All dependencies installed!')"
```

---

## Running the System

### Option 1: All-in-One (Recommended for Testing)

Run the startup script that launches all three services:

```bash
python run_all.py
```

This will:
1. Start Key Registry Server on http://localhost:5001
2. Start Receiver App on http://localhost:8501
3. Start Sender App on http://localhost:8502

All in separate terminal windows.

### Option 2: Manual Start (For Debugging)

**Terminal 1 - Key Registry Server:**
```bash
python key_registry_server.py
```
Expected output:
```
============================================================
🔐 PQC Key Registry Server
============================================================
Starting server on http://localhost:5001
...
```

**Terminal 2 - Receiver App:**
```bash
streamlit run receiver_app.py --server.port 8501
```

**Terminal 3 - Sender App:**
```bash
streamlit run sender_app.py --server.port 8502
```

---

## Usage Workflow

### 🎯 Complete Workflow

#### Step 1: Receiver Setup
1. Open http://localhost:8501 (Receiver App)
2. Click "Generate Receiver Kyber Keypair"
3. Enter a username (e.g., `alice`)
4. Click "🔗 Register Public Key to Server"
5. **✅ Status**: "Registered as 'alice'"

#### Step 2: Sender Setup
1. Open http://localhost:8502 (Sender App)
2. Upload a WAV audio file
3. Enter receiver's username in the text input (e.g., `alice`)
4. Click "🔍 Fetch Public Key from Registry"
5. **✅ Status**: "Public key fetched for 'alice'"

#### Step 3: Transmission
1. Review the encrypted workflow in expanders:
   - Kyber Key Encapsulation
   - Audio Chunking
   - AES-GCM Encryption
   - Obfuscated Audio Preview
   - Metadata Encryption
2. Click "Start Transmission"
3. **✅ Status**: "Transmission complete!"

#### Step 4: Receiver Gets Audio
1. In Receiver App, click "Listen for Incoming Transmission"
2. Audio will be received and processed:
   - Ciphertext decapsulated (Kyber)
   - Metadata decrypted
   - Audio chunks decrypted
   - **First listen**: Obfuscated audio (unrecognizable noise)
   - **Second listen**: Original audio (fully reconstructed)

---

## Key Features

### 🛡️ Security Features

| Feature | Implementation |
|---------|---|
| **Key Exchange** | Kyber512 (post-quantum secure) |
| **Audio Encryption** | AES-GCM (authenticated encryption) |
| **Identity Obfuscation** | XOR with SHA256-derived key |
| **Metadata Protection** | AES-GCM encrypted |
| **Key Registry** | Local server, automatic lookup |

### 🔄 Workflow Features

| Feature | Benefit |
|---------|---------|
| **Auto-Discovery** | No copy-paste of public keys |
| **Username Registry** | Simple memorable identifiers |
| **Obfuscation Preview** | See the "noise" being sent |
| **Dual Audio Playback** | Hear both obfuscated and original |
| **Progress Indicators** | Track encryption/decryption |

---

## File Structure

```
50_pqvoice/
├── key_registry_server.py      # Flask API for key management
├── sender_app.py               # Streamlit sender UI
├── receiver_app.py             # Streamlit receiver UI
├── crypto_utils.py             # Encryption/obfuscation logic
├── server.py                   # TCP socket communication
├── run_all.py                  # One-command startup script
├── requirements.txt            # Python dependencies
├── key_registry.json           # Persistent key storage (auto-created)
├── OBFUSCATION_ALGORITHM.md    # Algorithm documentation
└── README.md                   # This file
```

---

## Troubleshooting

### ❌ "Cannot connect to Key Registry Server"

**Cause**: Flask server not running or not on localhost:5001

**Solution**:
1. Start Flask server: `python key_registry_server.py`
2. Check http://localhost:5001 in browser
3. Should see API info page

### ❌ "User 'username' not found in registry"

**Cause**: Receiver hasn't registered yet

**Solution**:
1. Open Receiver App (http://localhost:8501)
2. Generate keypair
3. Register with a username
4. Then sender can fetch

### ❌ Audio file upload fails

**Cause**: FFmpeg not installed or audio format not WAV

**Solution**:
1. Install FFmpeg (see Installation section)
2. Ensure audio file is in WAV format
3. Restart Streamlit apps

### ❌ "Address already in use" error

**Cause**: Port already running something else

**Solution**:
- Change port in manual startup: `streamlit run receiver_app.py --server.port 8503`
- Or kill process: `netstat -ano | findstr :5001` (Windows) then `taskkill /PID <pid> /F`

### ❌ Receiver not getting audio

**Cause**: Sender and receiver not on same port, or firewall blocking

**Solution**:
1. Verify receiver IP/port match sender's target
2. Default: 127.0.0.1:5000
3. Check Windows Firewall settings

---

## API Reference

### Key Registry Server (http://localhost:5001)

#### POST /register
Register a public key

```bash
curl -X POST http://localhost:5001/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "public_key": "a3b4c5d6..."}'
```

#### GET /fetch/<username>
Fetch a public key

```bash
curl http://localhost:5001/fetch/alice
```

#### GET /list
List all registered users

```bash
curl http://localhost:5001/list
```

#### DELETE /unregister/<username>
Unregister a user

```bash
curl -X DELETE http://localhost:5001/unregister/alice
```

#### GET /health
Health check

```bash
curl http://localhost:5001/health
```

---

## Performance Notes

| Operation | Time |
|-----------|------|
| Keypair generation | ~1 second |
| Register public key | <1 second |
| Fetch public key | <1 second |
| Kyber encapsulation | ~1 second |
| Audio chunking (2s chunks) | ~1 second per 10MB |
| Encryption (AES-GCM) | ~2 seconds per 10MB |
| Transmission (local) | ~5-10 seconds per 10MB |
| Decryption + De-obfuscation | ~2 seconds per 10MB |

---

## College Project Use Cases

### 🎓 In-Lab Setup
```
All students on same Wi-Fi network
├─ Each student can run receiver_app independently
├─ Share usernames (alice, bob, charlie, etc.)
└─ Send encrypted audio between lab machines
```

### 🏃 Demo Setup
```
Presenter runs all three:
├─ Key registry on presentation machine
├─ Receiver app demo (incoming audio)
└─ Sender app demo (outgoing audio)
Show encryption workflow live
```

### 📊 Security Analysis
```
Use for cryptography course:
├─ Observe obfuscation_algorithm.md
├─ Analyze key_registry_server.py
├─ Study crypto_utils.py
└─ Understand post-quantum cryptography
```

---

## Additional Commands

### View Registered Users
```bash
cat key_registry.json
```

### Clear All Registrations
```bash
rm key_registry.json
# Restart server
python key_registry_server.py
```

### Test Audio with Different Sizes
```bash
# 10 second audio
ffmpeg -f lavfi -i sine=f=440:d=10 test_audio.wav

# 30 second audio
ffmpeg -f lavfi -i sine=f=440:d=30 test_audio.wav
```

---

## Documentation

- **OBFUSCATION_ALGORITHM.md** - Complete explanation of identity obfuscation, XOR operation, SHA-256 derivation, and security analysis

---

## License & Credits

College Project - PQC Audio System
- Kyber512: Post-Quantum Cryptography
- AES-GCM: NIST standard authenticated encryption
- Identity Obfuscation: Custom XOR-based approach

---

## Questions?

Refer to:
1. **OBFUSCATION_ALGORITHM.md** - Algorithm details
2. **code comments** - Each function has docstrings
3. **API endpoints** - http://localhost:5001 shows all endpoints

---

## Next Steps

After getting this running:
1. ✅ Test with multiple users
2. ✅ Record presentations
3. ✅ Analyze encrypted traffic
4. ✅ Extend with file logging
5. ✅ Add user authentication (optional)
6. ✅ Deploy on college server (optional)

---

**Happy encrypting! 🔐**
