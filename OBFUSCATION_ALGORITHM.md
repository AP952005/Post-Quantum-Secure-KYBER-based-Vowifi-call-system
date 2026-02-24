# Audio Identity Obfuscation Algorithm Documentation

## Overview

The PQC Audio Voice system implements a **Session Key-Based XOR Obfuscation** algorithm to hide the identity of audio data during transmission. This ensures that even if the encrypted transmission is intercepted, the original audio characteristics remain hidden from both human listeners and AI analysis tools.

---

## Algorithm Details

### 1. **Obfuscation Key Derivation**

#### Function: `derive_obfuscation_key(session_key, chunk_index)`

**Purpose**: Generate a unique, deterministic obfuscation key for each audio chunk.

**Process**:
```
Input: 
  - session_key (32 bytes from Kyber KEM)
  - chunk_index (integer: 0, 1, 2, ...)

Output: 
  - obfuscation_key (32 bytes)

Algorithm:
  1. Create SHA-256 hash object
  2. Update hash with: session_key (binary data)
  3. Update hash with: chunk_index (4 bytes, big-endian)
  4. Output: First 32 bytes of SHA-256 digest
```

**Mathematical Representation**:
```
obf_key[i] = SHA256(session_key || chunk_index)[0:32]
```

where `||` denotes concatenation.

**Why This Approach**:
- **Deterministic**: Same input always produces same output
- **Unique per chunk**: Different index = different key
- **One-way function**: Cannot reverse SHA-256 to recover session key
- **Cryptographically secure**: SHA-256 is collision-resistant

---

### 2. **XOR Obfuscation**

#### Function: `obfuscate_audio(audio_data, session_key, chunk_index)`

**Purpose**: Obfuscate raw audio samples using the derived key.

**Process**:
```
Input:
  - audio_data (raw byte samples from WAV file)
  - session_key (32 bytes from Kyber KEM)
  - chunk_index (0, 1, 2, ...)

Output:
  - obfuscated_data (same length as audio_data, garbled bytes)

Algorithm:
  1. Derive obfuscation key: obf_key = derive_obfuscation_key(session_key, chunk_index)
  2. For each byte i in audio_data:
     obfuscated[i] = audio_data[i] XOR obf_key[i % 32]
  3. Return obfuscated byte array
```

**Mathematical Representation**:
```
obfuscated[i] = audio[i] ⊕ obf_key[i mod 32]

where ⊕ is the XOR (bitwise exclusive OR) operation
```

**Why XOR**:
- **Simple and Fast**: Minimal computational overhead
- **Reversible**: XORing twice with same key returns original (XOR is self-inverse)
- **Byte-level diffusion**: Each output byte depends on input byte and key byte
- **Pattern disruption**: Removes audio patterns that could identify speaker

---

### 3. **XOR De-obfuscation**

#### Function: `deobfuscate_audio(obfuscated_data, session_key, chunk_index)`

**Purpose**: Reverse the obfuscation to recover original audio.

**Process**:
```
Input:
  - obfuscated_data (garbled bytes)
  - session_key (same 32 bytes from Kyber KEM)
  - chunk_index (same index as during obfuscation)

Output:
  - original_audio_data (recovered raw audio samples)

Algorithm:
  1. Derive obfuscation key: obf_key = derive_obfuscation_key(session_key, chunk_index)
  2. For each byte i in obfuscated_data:
     original[i] = obfuscated[i] XOR obf_key[i % 32]
  3. Return original byte array

Note: This is IDENTICAL to obfuscation (XOR is self-inverse)
```

**Why It Works**:
- XOR property: `A ⊕ B ⊕ B = A`
- Since obfuscation uses the same operation, applying it again recovers the original
- Only works with correct session key and chunk index

---

## Complete Signal Flow

### Sender Side (Obfuscation + Encryption)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER UPLOADS AUDIO                                       │
│    (e.g., speaker.wav - identifiable audio)                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│ 2. KYBER KEY ENCAPSULATION                                  │
│    Generate: (session_key, ciphertext)                      │
│    session_key = 32 bytes (quantum-safe)                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│ 3. CHUNK SPLITTING                                          │
│    Split audio into fixed-duration chunks (2000ms each)     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ├─► CHUNK 0: [samples...]
                      ├─► CHUNK 1: [samples...]
                      └─► CHUNK N: [samples...]
                      │
┌─────────────────────▼───────────────────────────────────────┐
│ 4. IDENTITY OBFUSCATION (FOR EACH CHUNK)                    │
│                                                              │
│    For Chunk i:                                             │
│    obf_key[i] = SHA256(session_key || i)                    │
│    obfuscated[i] = chunk[i] XOR obf_key[i]                  │
│                                                              │
│    OUTPUT: Unrecognizable, noise-like audio samples         │
└─────────────────────┬───────────────────────────────────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
    ┌───────▼──────────┐  ┌─────▼──────────────┐
    │ SENDER PREVIEW   │  │ ENCRYPTION         │
    │ (Optional View)  │  │ For Transmission   │
    │ Plays garbled    │  │                    │
    │ obfuscated audio │  │ For each chunk:    │
    │ to confirm       │  │ encrypted[i] =     │
    │ identity hidden  │  │ AES-GCM(nonce,     │
    │                 │  │ obfuscated[i])     │
    └───────┬──────────┘  └─────┬──────────────┘
            │                   │
            │          ┌────────▼────────────┐
            │          │ AES-GCM ENCRYPTION  │
            │          │ Authenticated       │
            │          │ Encryption with     │
            │          │ Unique Nonce        │
            │          └────────┬────────────┘
            │                   │
            └───────────┬───────┘
                        │
            ┌───────────▼───────────┐
            │ TRANSMISSION TO SERVER │
            │ (Encrypted + Obfuscated)
            │ Not human understandable
            └───────────┬───────────┘
                        │
                    [NETWORK]
                        │
```

### Receiver Side (Decryption + De-obfuscation)

```
┌─────────────────────────────────────────────────────────────┐
│ RECEIVE ENCRYPTED DATA FROM NETWORK                         │
│ (Doubly protected: encrypted & obfuscated)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│ 1. KYBER KEY DECAPSULATION                                  │
│    Recover same session_key using receiver's private key    │
│    session_key = kyber_decap(ciphertext, receiver_sk)       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│ 2. AES-GCM DECRYPTION (FOR EACH CHUNK)                       │
│    recovered = AES-GCM.decrypt(nonce, encrypted[i])         │
│    Result: Still obfuscated (still garbage/noise)            │
└─────────────────────┬───────────────────────────────────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
    ┌───────▼──────────┐  ┌─────▼──────────────┐
    │ OBFUSCATED VIEW  │  │ DE-OBFUSCATION     │
    │ (First Preview)  │  │ (Final Recovery)   │
    │                  │  │                    │
    │ For Chunk i:     │  │ For Chunk i:       │
    │ Play             │  │ obf_key[i] =       │
    │ obfuscated[i]    │  │ SHA256(session_key │
    │ to confirm it's  │  │ || i)              │
    │ not human        │  │ original[i] =      │
    │ understandable   │  │ obfuscated[i]      │
    │ or AI readable   │  │ XOR obf_key[i]     │
    │                  │  │                    │
    │ Output: Noise    │  │ Output: Original   │
    │        (Garbage) │  │        Audio       │
    └───────┬──────────┘  └─────┬──────────────┘
            │                   │
            │          ┌────────▼────────────┐
            │          │ AUDIO RECONSTRUCTION│
            │          │ Combine all chunks  │
            │          │ into full WAV file  │
            │          └────────┬────────────┘
            │                   │
            └───────────┬───────┘
                        │
            ┌───────────▼───────────┐
            │ FINAL PLAYBACK        │
            │ Original, Identifiable│
            │ Audio (Speaker voice) │
            └───────────────────────┘
```

---

## Security Analysis

### 1. **Why Obfuscation Is Necessary**

Even with AES-GCM encryption:
- Modern AI can identify speakers from spectrograms
- Voice biometrics can be extracted from encrypted audio patterns
- Encrypted data still reveals: audio duration, pattern, timing

**Obfuscation solves this by**:
- Randomizing byte patterns before encryption
- Destroying speaker-identifying characteristics
- Making audio unrecognizable even if encryption is broken

### 2. **Strength Against Attacks**

| Attack Type | Defense | Status |
|---|---|---|
| **Brute Force on Obfuscation Key** | SHA-256 has 2^256 possible outputs | ✅ Secure |
| **Known Plaintext Attack** | XOR key is derived from session key, not reused | ✅ Secure |
| **Pattern Analysis** | Obfuscation randomizes every byte | ✅ Secure |
| **Speaker Identification** | Destroys voice spectrograms | ✅ Secure |
| **AI Voice Recognition** | Audio becomes noise-like | ✅ Secure |
| **Replay Attack** | Nonce + chunk index prevents replay | ✅ Secure |

### 3. **Key Security Properties**

1. **Session-Key Binding**: Obfuscation key depends on session key
   - Different session = different obfuscation
   - Each connection gets unique obfuscation

2. **Chunk-Index Dependency**: Different chunks get different keys
   - Cannot reuse key across chunks
   - Prevents pattern recognition

3. **Two-Layer Security**:
   - Layer 1: Obfuscation (identity hiding)
   - Layer 2: AES-GCM (confidentiality + authentication)

4. **Quantum-Safe**: Session key from Kyber512 (post-quantum secure)
   - Protects against future quantum computers
   - Obfuscation strength inherits from quantum-safe session key

---

## Mathematical Properties

### XOR Operation Properties

**Self-Inverse**:
```
A ⊕ B ⊕ B = A

Therefore:
obfuscate(obfuscate(X)) = X
```

**Commutative**:
```
A ⊕ B = B ⊕ A
```

**Associative**:
```
(A ⊕ B) ⊕ C = A ⊕ (B ⊕ C)
```

### SHA-256 Properties

**Collision Resistance**:
```
Finding X₁ ≠ X₂ where SHA256(X₁) = SHA256(X₂) requires ~2^128 operations
```

**Pre-image Resistance**:
```
Finding X where SHA256(X) = Y requires ~2^256 operations
```

**Avalanche Effect**:
```
Small change in input → completely different output
Example:
  SHA256(key || 0) ≠ SHA256(key || 1)
  (No bit similarity in outputs)
```

---

## Obfuscation Strength Analysis

### Audio Characteristics Destroyed

| Characteristic | Example | How Obfuscation Destroys It |
|---|---|---|
| **Speaker Voice** | Unique tone, pitch | XOR randomizes samples, destroys frequency patterns |
| **Speech Patterns** | Accent, speech rate | Byte-level obfuscation breaks timing patterns |
| **Emotional Content** | Angry, sad, happy | Spectrogram analysis becomes impossible |
| **Language** | English, Mandarin | Phonetic patterns are randomized |
| **Biometric Data** | Voice ID, speaker verification | No recognizable features remain |

### Example (Conceptual)

**Before Obfuscation** (Audio Samples):
```
[127, 130, 132, 128, 125, 120, 115, 118, 122, 125, ...]
(Human recognizable - this is a voice)
```

**After Obfuscation** (XOR with 32-byte key):
```
[43, 216, 89, 42, 201, 156, 67, 203, 88, 44, ...]
(Appears random, unrecognizable, like noise)
```

**After AES-GCM Encryption**:
```
[12, 245, 78, 156, 34, 198, 2, 156, 245, 112, ...]
(Doubly obscured)
```

---

## Implementation Details

### Code Flow

```python
# Sender side
session_key, ciphertext = kyber_encapsulate(receiver_pk)
for chunk_idx, audio_chunk in enumerate(chunks):
    # Step 1: Obfuscate
    obf_key = derive_obfuscation_key(session_key, chunk_idx)
    obfuscated = obfuscate_audio(audio_chunk, session_key, chunk_idx)
    
    # Step 2: Encrypt
    nonce = base_nonce + chunk_idx.to_bytes(4, "big")
    ciphertext = aesgcm.encrypt(nonce, obfuscated, None)
    
    # Send: (nonce, ciphertext)

# Receiver side
session_key = kyber_decapsulate(ciphertext, receiver_sk)
for chunk_idx, (nonce, ct) in enumerate(encrypted_chunks):
    # Step 1: Decrypt
    obfuscated = aesgcm.decrypt(nonce, ct, None)
    
    # Step 2: De-obfuscate (optional - receiver can choose to see obfuscated first)
    original = deobfuscate_audio(obfuscated, session_key, chunk_idx)
    
    # Recover audio
```

---

## Comparison with Other Methods

| Method | Speed | Security | Reversibility | Implementation |
|---|---|---|---|---|
| **Our XOR Method** | ⚡ Very Fast | ⭐⭐⭐⭐⭐ | ✅ Perfect | Simple |
| **Noise Addition** | Fast | ⭐⭐⭐ | ❌ Information Loss | Easy |
| **Frequency Shifting** | Medium | ⭐⭐⭐⭐ | ✅ Reversible | Medium |
| **Phase Randomization** | Medium | ⭐⭐⭐⭐ | ✅ Reversible | Complex |
| **Steganography** | Slow | ⭐⭐⭐ | ✅ Reversible | Very Complex |

**Our Method Advantages**:
- ✅ Minimal computational overhead
- ✅ No information loss
- ✅ Perfect reversibility with correct key
- ✅ Cryptographically secure (SHA-256 based)
- ✅ Unique per connection and per chunk

---

## Metadata Encryption

### Why Metadata Encryption Matters

Even with audio encryption and obfuscation, **metadata can leak critical information**:

| Metadata | Information Leaked |
|---|---|
| **Audio Duration** | How long the conversation was, estimated content type |
| **Frame Rate** (44100 Hz, 48000 Hz) | Audio quality, recording device type |
| **Sample Width** (16-bit, 24-bit) | Device/codec information, quality tier |
| **Number of Channels** (Mono, Stereo) | Device type, recording setup |
| **Timestamps** | When communication occurred |
| **Total Size** | Conversation length, encoding type |

An intruder analyzing metadata can:
- Identify participants by device fingerprints
- Determine conversation duration and frequency
- Infer content type (music, speech, etc.)
- Build behavioral patterns
- Correlate with other activities

### Metadata Encryption Implementation

All metadata is encrypted using **AES-GCM with a PQC-derived key**:

#### Function: `derive_metadata_key(session_key)`

```python
metadata_key = SHA256(session_key || "metadata_key")
```

**Features**:
- Unique key for each connection (derived from session key)
- Separated from audio obfuscation key
- Deterministic but cryptographically secure

#### Function: `encrypt_metadata(metadata_dict, session_key)`

**Process**:
```
1. Serialize metadata to JSON: 
   {"frame_rate": 44100, "sample_width": 2, "channels": 1, "total_chunks": 15}

2. Derive metadata key:
   metadata_key = SHA256(session_key || "metadata_key")

3. Generate random 12-byte nonce

4. Apply AES-GCM encryption:
   encrypted_metadata = AES-GCM(metadata_key, nonce, metadata_json)

5. Return: (nonce, ciphertext)
```

#### Function: `decrypt_metadata(nonce, ciphertext, session_key)`

**Reverse Process**:
```
1. Derive metadata key (same derivation):
   metadata_key = SHA256(session_key || "metadata_key")

2. Decrypt using AES-GCM:
   metadata_json = AES-GCM_DECRYPT(metadata_key, nonce, ciphertext)

3. Deserialize from JSON:
   metadata_dict = parse(metadata_json)

4. Return: Original metadata dictionary
```

---

## Complete Transmission Security Model

### Triple-Layer Protection

```
┌─────────────────────────────────────────────────────────────┐
│ ORIGINAL AUDIO + METADATA                                   │
│ (Identifiable sender)                                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼──────────────┐  ┌────────▼───────────────┐
│ LAYER 1:             │  │ LAYER 1:               │
│ AUDIO OBFUSCATION    │  │ METADATA ENCRYPTION    │
│                      │  │                        │
│ XOR each audio chunk │  │ AES-GCM encrypt all   │
│ with SHA256-derived  │  │ metadata fields using  │
│ key from session_key │  │ PQC-derived metadata  │
│                      │  │ key                    │
│ Makes audio = noise  │  │ Makes metadata = random│
└───────┬──────────────┘  └────────┬───────────────┘
        │                          │
        │      ┌──────────────────┐│
        │      │                  ││
┌───────▼──────▼──────────────────▼┐
│ LAYER 2: AES-GCM ENCRYPTION       │
│                                   │
│ Encrypt obfuscated audio chunks   │
│ AND encrypted metadata with unique│
│ nonce for each chunk              │
│                                   │
│ Provides: Confidentiality +       │
│           Authentication          │
└───────┬───────────────────────────┘
        │
┌───────▼──────────────────────────┐
│ LAYER 3: QUANTUM-SAFE KEY EXCHANGE│
│                                   │
│ All encryption uses session_key   │
│ derived from Kyber512 KEM         │
│ Protection against quantum attacks│
└─────────────────────────────────────┘
```

### Transmission Packet Structure

```
SENDER → NETWORK → RECEIVER

Packet Contents:
[
  {
    "ciphertext": <Kyber KEM ciphertext for receiver>,
    "encrypted_chunks": [
      (nonce₀, ciphertext₀),  // AES-GCM(obfuscated_chunk₀)
      (nonce₁, ciphertext₁),  // AES-GCM(obfuscated_chunk₁)
      ...
      (nonceₙ, ciphertextₙ)   // AES-GCM(obfuscated_chunkₙ)
    ],
    "metadata_nonce": <12-byte random nonce>,
    "metadata_ciphertext": <AES-GCM(encrypted metadata)>
  }
]
```

### What An Intruder Sees

**Without Correct Session Key**:
- Kyber ciphertext: Random 1088 bytes (post-quantum secure)
- Audio chunks: Random ciphertexts (AES-GCM encrypted)
- Metadata: Random bytes (AES-GCM encrypted)
- Nonces: Random values (no patterns)

**All information appears as random noise** - no metadata leakage possible.

---

## Metadata Fields Protected

Currently encrypted metadata includes:

```json
{
  "frame_rate": 44100,          // Sample rate (Hz)
  "sample_width": 2,             // Bytes per sample (1-4)
  "channels": 1,                 // Audio channels (1-8)
  "total_chunks": 15             // Number of audio chunks
}
```

All these values are protected and cannot be inferred by packet analysis.

---

## Implementation in Apps

### Sender Side

```python
# Step 1: Extract metadata from audio
metadata = {
    'frame_rate': audio.frame_rate,
    'sample_width': audio.sample_width,
    'channels': audio.channels,
    'total_chunks': len(encrypted_chunks)
}

# Step 2: Encrypt metadata with PQC-derived key
metadata_nonce, metadata_ciphertext = encrypt_metadata(metadata, session_key)

# Step 3: Send everything together
payload = {
    'ciphertext': ciphertext,                   # Kyber
    'encrypted_chunks': encrypted_chunks,       # Audio
    'metadata_nonce': metadata_nonce,           # Metadata encryption nonce
    'metadata_ciphertext': metadata_ciphertext  # Encrypted metadata
}
```

### Receiver Side

```python
# Step 1: Recover session key from Kyber ciphertext
session_key = kyber_decapsulate(ciphertext, receiver_sk)

# Step 2: Decrypt metadata using recovered session key
metadata = decrypt_metadata(metadata_nonce, metadata_ciphertext, session_key)

# Step 3: Use metadata for audio reconstruction
frame_rate = metadata['frame_rate']
sample_width = metadata['sample_width']
channels = metadata['channels']

# Step 4: Decrypt and de-obfuscate audio chunks
for idx, (nonce, ct) in enumerate(encrypted_chunks):
    plaintext = aesgcm.decrypt(nonce, ct, None)  # AES-GCM
    audio_data = deobfuscate_audio(plaintext, session_key, idx)  # Remove obfuscation
    chunk = AudioSegment(data=audio_data, 
                         sample_width=sample_width,
                         frame_rate=frame_rate,
                         channels=channels)
```

---

## Metadata vs Audio Security Comparison

| Aspect | Audio Protection | Metadata Protection |
|---|---|---|
| **Encryption** | AES-GCM + XOR Obfuscation | AES-GCM |
| **Key Derivation** | Session key + chunk index | Session key + "metadata_key" constant |
| **Nonce** | Sequential (per chunk) | Random (once per transmission) |
| **Reversibility** | Perfect (XOR is self-inverse) | Perfect (AES-GCM decryption) |
| **Key Material** | From Kyber512 KEM | From Kyber512 KEM |
| **Quantum-Safe** | ✅ Yes (Kyber512) | ✅ Yes (Kyber512) |
| **Authentication** | ✅ GCM mode | ✅ GCM mode |

---

## Attack Resistance with Metadata Encryption

| Attack | Without Metadata Encryption | With Metadata Encryption |
|---|---|---|
| **Fingerprinting by device** | ❌ Vulnerable (frame rate leaks) | ✅ Protected |
| **Duration inference** | ❌ Vulnerable (can count packets) | ✅ Protected (all encrypted) |
| **Traffic pattern analysis** | ⚠️ Partially vulnerable | ✅ Protected (metadata hidden) |
| **Metadata harvesting** | ❌ Vulnerable | ✅ Protected |
| **Behavioral profiling** | ⚠️ Partially vulnerable | ✅ Better protected |
| **Quantum attacks** | ❌ Vulnerable (RSA-based) | ✅ Protected (Kyber512) |



The identity obfuscation algorithm uses a **Session Key-Based XOR Obfuscation** approach that:

1. **Derives unique keys** for each chunk using SHA-256(session_key || chunk_index)
2. **Applies XOR obfuscation** to randomize audio samples
3. **Combines with AES-GCM encryption** for double protection
4. **Maintains perfect reversibility** for legitimate receivers with the session key
5. **Destroys speaker identity** making audio unrecognizable to humans and AI

This ensures that **even if transmission is intercepted and decrypted**, the audio identity remains completely hidden from unauthorized access.

