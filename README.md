# 🔐 Post-Quantum Encrypted and Obfuscation-Enabled Secure Voice Communication Framework

A quantum-resistant, privacy-preserving real-time voice communication framework that integrates **Post-Quantum Cryptography (PQC)** with **Voice Obfuscation** to ensure long-term confidentiality, integrity, and speaker anonymity.

---

## 📌 Overview

Modern voice communication systems rely on classical cryptographic algorithms such as RSA and ECC, which are vulnerable to emerging quantum computing threats. Additionally, AI-based voice recognition techniques pose risks to speaker identity even when call content is encrypted.

This framework addresses both challenges by combining:

- 🔑 Post-Quantum Key Encapsulation (CRYSTALS-Kyber)
- 🔐 AES-GCM Symmetric Encryption
- 🎙️ Real-Time Voice Obfuscation
- 🌐 Secure Transmission over WebRTC / Wi-Fi

The result is a secure, low-latency, and future-proof voice communication solution.

---

## 🚀 Key Features

- ✅ Quantum-resistant key exchange (Kyber KEM)
- ✅ End-to-end AES-GCM encrypted voice transmission
- ✅ Real-time speaker identity obfuscation
- ✅ Dynamic session key generation (Forward Secrecy)
- ✅ Low-latency communication (<150 ms)
- ✅ Cross-platform compatibility (Web / Mobile)
- ✅ No specialized hardware required

---

## 🏗️ System Architecture

<img width="600" height="550" alt="image" src="https://github.com/user-attachments/assets/d8cdc15d-15b9-456d-bb8b-6fa29a98dbf6" />

## Workflow 

<img width="545" height="244" alt="image" src="https://github.com/user-attachments/assets/6f6efbd4-2259-4405-a1c6-c99804e40bc5" />


---

## 🔬 Technologies Used

| Component | Technology |
|------------|------------|
| Post-Quantum Key Exchange | CRYSTALS-Kyber |
| Symmetric Encryption | AES-GCM |
| Real-Time Communication | WebRTC |
| Voice Processing | Digital Signal Processing (DSP) |
| Backend | Node.js / Python |
| Frontend | Web-Based Interface |

---

## ⚙️ Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/repository-name.git
cd repository-name
```
2️⃣ Install Dependencies

For Node.js:
```bash
npm install
```
For Python:
```bash
pip install -r requirements.txt
```
3️⃣ Run the Application

For Node.js:
```bash
npm start
```
For Python:
```bash
python run_alll.py
```

📊 Performance Metrics

🔹 Average Latency: <150 ms

🔹 Jitter: <30 ms

🔹 Packet Loss Tolerance: <1%

🔹 Optimized Quantum-Safe Handshake

📖 Research Background

The framework is based on systematic analysis of:

Wi-Fi security evolution (WEP → WPA → WPA2 → WPA3)

VoWiFi Quality of Service requirements

Denial-of-Service and MAC-layer vulnerabilities

Performance-security trade-offs

Integration of Post-Quantum Cryptography in wireless systems

🔮 Future Enhancements

-->Integration with 6G networks

-->AI-based anomaly detection

-->PQC optimization for IoT devices

-->Adaptive latency-aware encryption

-->Cross-layer security monitoring

📜 License

This project is licensed under the MIT License.

👤 Author

Abishek Palani Sivashanmugam
Secure Communication & Cybersecurity Research
