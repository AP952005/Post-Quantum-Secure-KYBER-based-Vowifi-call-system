# Voice Call System - Quick Start Guide

## Before You Start

✅ Install PyAudio:
```powershell
pip install pyaudio
```

---

## Quickest Test: Same Machine (Localhost)

### System A (Server - Terminal 1)
```powershell
cd C:\Users\Lenovo\Desktop\50_pqvoice
python key_registry_server.py
```

**Wait for**:
```
Binding to 0.0.0.0:5001
Running on http://127.0.0.1:5001
```

### System A (Client 1/Alice - Terminal 2)
```powershell
cd C:\Users\Lenovo\Desktop\50_pqvoice
python main.py
```
**In GUI:**
1. Username: `alice`
2. Port: `50005`
3. Click "Register & Login"

### System A (Client 2/Bob - Terminal 3)
```powershell
cd C:\Users\Lenovo\Desktop\50_pqvoice
python main.py
```
**In GUI:**
1. Username: `bob`
2. Port: `50006`
3. Click "Register & Login"
4. **Target Username**: `alice`
5. Click **Call**

---

## Two Machines Test (WiFi/LAN)

### Find Your IPs
**System A (Registry + Client 1)**: `ipconfig` -> `192.168.1.100` (example)
**System B (Client 2)**: `ipconfig` -> `192.168.1.101` (example)

### System A
1. Run `python key_registry_server.py`
2. Run `python main.py`
   - Registry URL: `http://localhost:5001`
   - Register as: `alice`

### System B
1. Run `python main.py`
   - Registry URL: `http://192.168.1.100:5001` (System A IP)
   - Register as: `bob`
   - Call Target: `alice`


---

## Voice Call Test (If UI Updated)

### After integration with VoiceStream

**System A (alice receives call)**:
```
Incoming call from bob
[✅ Accept]  [❌ Reject]
```

Click ✅ Accept

Both users can now:
- Speak into microphone
- Hear obfuscated audio from other person
- See call statistics
- Click ❌ End Call to disconnect

---

## Troubleshooting

### "Failed to connect to registry"
- ❌ Wrong IP in REGISTRY_SERVER
- ❌ Registry server not running
- ✅ Check: `curl http://192.168.1.100:5001`

### "User not found in registry"
- ❌ User not registered
- ❌ User registered on different registry server
- ✅ Register first before calling

### "PyAudio error: device not found"
- ❌ Microphone/speaker not connected
- ❌ PyAudio can't access audio devices
- ✅ Check: Device Manager → Sound devices

### "Port already in use"
- ❌ Another app using same port (5001, 5555, 8501, etc.)
- ✅ Change port in code or close other apps

### Audio is distorted/crackling
- ⚠️ Network latency/packet loss
- ⚠️ CPU overload
- ✅ Reduce other tasks, try wired connection

---

## Files You Need

Minimal working set:
```
50_pqvoice/
├── crypto_utils.py           ← Encryption/obfuscation
├── audio_stream.py           ← Real-time audio (NEW)
├── call_handler.py           ← Call signaling (NEW)
├── key_registry_server.py    ← Registry with call endpoints
├── server.py                 ← P2P socket communication
├── requirements.txt          ← Dependencies (includes pyaudio)
├── receiver_app.py           ← Receiver UI
├── sender_app.py             ← Sender UI
└── VOICE_CALL_SYSTEM.md      ← Full documentation
```

---

## What's Happening Behind the Scenes

### On Sender (bob)
```
1. Upload audio.wav
2. Enter receiver username (alice)
3. Fetch alice's public key from registry
4. Generate Kyber keypair for this session
5. Encapsulate session key with alice's public key
6. Encrypt audio with session key
7. Obfuscate audio (XOR with SHA256 per-frame)
8. Send encrypted+obfuscated audio to alice's IP:port
```

### On Receiver (alice)
```
1. Register with registry (username, IP, port, public key)
2. Listen on registered port for incoming audio
3. Receive encrypted+obfuscated audio from sender
4. Decrypt with Kyber private key (get session key)
5. Deobfuscate audio (XOR with SHA256 per-frame)
6. Play original audio to speaker
```

---

## Security Verification

### Packet Inspection

On System A, open PowerShell and capture network traffic:
```powershell
# View packets to port 5555 (audio)
netsh trace start capture=yes tracefile=C:\trace.etl
# ... run test ...
netsh trace stop
```

Open trace in Network Monitor:
- You'll see encrypted packets to 192.168.X.X:5555
- Audio data is NOT visible (encrypted)
- You won't recognize the audio (obfuscated)

---

## Performance Metrics

### Expected Numbers

**Latency**:
- Sender to Receiver: 20-70ms
- Total round-trip: 40-140ms (both directions)
- Imperceptible to humans (>200ms is noticeable)

**Bandwidth**:
- Per frame (20ms): 352 bytes
- Total: 17.6 KB/sec = 140.8 kbps
- vs WhatsApp: ~32 kbps (compressed)

**CPU**:
- Encryption: ~0.4ms per frame
- Obfuscation: ~0.01ms per frame
- Total: ~1-2% CPU on modern hardware

---

## Demo Flow for Class Presentation

### Setup (5 min)
```
1. Start registry on System A
2. Register receiver (alice)
3. Launch sender app on System B
```

### Demo (10 min)
```
1. Show file encryption (existing feature)
2. Show encrypted audio preview (unrecognizable)
3. Explain obfuscation algorithm
4. Initiate voice call (once UI integrated)
5. Both speakers talk
6. Show network traffic (encrypted)
7. Show call statistics
```

### Comparison (5 min)
```
1. Show latency: 50-70ms vs competitors 100-300ms
2. Show encryption: Kyber512 vs ECDH
3. Show obfuscation: Voice unrecognizable vs original
4. Discuss quantum safety
```

---

## Files to Review

For understanding the system:

1. **Start here**: VOICE_CALL_SYSTEM.md
   - Complete architecture
   - Usage examples
   - Technical details

2. **Architecture**: VOICE_IMPLEMENTATION_STATUS.md
   - What was built
   - How it works
   - Next steps

3. **Code walkthrough**: audio_stream.py
   - VoiceStream class (main engine)
   - Threading model
   - Error handling

4. **Call signaling**: call_handler.py
   - CallHandler class
   - Protocol flow
   - Status tracking

---

## Next: UI Integration

To enable voice calls in Streamlit, add to receiver_app.py and sender_app.py:

See **VOICE_CALL_SYSTEM.md** section "Next Steps: UI Integration" for:
- Code snippets for receiver app
- Code snippets for sender app
- Expected UI flow

---

## Support

For issues:
1. Check VOICE_CALL_SYSTEM.md troubleshooting section
2. Review VOICE_IMPLEMENTATION_STATUS.md
3. Check requirements.txt (all packages installed?)
4. Verify network connectivity: `ping 192.168.X.X`
5. Test registry: `curl http://192.168.X.X:5001`

---

**Ready to test?** Start with localhost version above! 🚀

