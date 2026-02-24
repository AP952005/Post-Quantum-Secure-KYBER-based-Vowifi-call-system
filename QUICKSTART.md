# ⚡ Quick Start - Voice Call System (5 Minutes)

## 🎯 Goal
Make a voice call across WiFi with post-quantum encryption.

---

## 📋 Checklist (Do in Order)

### Step 1: Get Your IP Address (1 min)

**Windows - In PowerShell:**
```powershell
ipconfig
```
Find the "IPv4 Address" under your WiFi adapter (e.g., `192.168.1.100`)

**Mac/Linux:**
```bash
ifconfig | grep inet
```

Write down:
- **Machine A IP:** _______ (Will run Registry + Receiver)
- **Machine B IP:** _______ (Will run Sender)

---

### Step 2: Start Registry (1 min)

**On Machine A, Terminal 1:**
```bash
cd 50_pqvoice
python key_registry_server.py
```

You should see:
```
 * Running on http://0.0.0.0:5001
```

✅ Keep this running!

---

### Step 3: Start Receiver App (1 min)

**On Machine A, Terminal 2:**
```bash
streamlit run receiver_app.py
```

Browser opens to `http://localhost:8501`

**In the web interface:**
1. Click "Generate Kyber512 Keypair"
2. Enter username: **alice**
3. Click "Register"

✅ Now alice is registered and listening!

---

### Step 4: Start Sender App (1 min)

**On Machine B:**
```bash
streamlit run sender_app.py
```

Browser opens to `http://localhost:8501`

---

### Step 5: Make First Call (1 min)

**In Sender App (Machine B):**

1. Scroll to "Fetch Public Key from Registry"
2. Enter: **alice**
3. Click "Fetch"
   - Should show: ✅ "Public key fetched"

4. Scroll to "Voice Call Interface"
5. Enter your username: **bob**
6. Click "📞 Start Voice Call"

**Back in Receiver App (Machine A):**

1. Scroll to "Voice Call Interface"  
2. Click "🔄 Check for Calls"
   - Should show: alice calling
3. Click "✅ Accept"

**Both Apps:**
- Show: 🟢 **ACTIVE VOICE CALL**
- Speak into microphone
- Hear the other person

4. Click "❌ End Call" to disconnect

---

## ✅ Done!

You now have a **post-quantum voice call system**!

### What Just Happened:

1. **Registry** coordinated the call (centralized signaling)
2. **Sender** encapsulated session key using **Kyber512** (quantum-safe)
3. **Receiver** decapsulated the session key
4. **Audio** encrypted with **AES-256-GCM**
5. **Per-frame obfuscation** hides identity
6. **UDP streaming** for low latency (50-70ms)

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to registry" | Check that Terminal 1 is still running the registry server |
| "No audio" | Install PyAudio: `pip install PyAudio` |
| "Call won't answer" | Make sure receiver clicked "Check for Calls" |
| "Audio is choppy" | Reduce background WiFi use, try closer to router |

---

## 📚 Learn More

- See `VOICE_CALL_WIFI_GUIDE.md` for detailed setup
- See `test_voice_call.py` to validate everything works
- See `ARCHITECTURE.md` for how it works
- See `SECURITY_ANALYSIS.md` for security details

---

## 🎉 Next Steps

After successful call:

1. **Test across different WiFi** (roaming)
2. **Test with 3+ participants** (group calls)
3. **Add call recording** (save encrypted audio)
4. **Optimize latency** (tune buffer sizes)

---

**Questions? Run the test:**
```bash
python test_voice_call.py
```

This will validate all components and show any issues.

