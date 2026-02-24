
import time
import os
import crypto_utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def benchmark():
    print("--- PQC Voice Chat Cryptographic Benchmarks ---")
    
    # 1. Kyber Handshake
    start = time.perf_counter()
    pk, sk = crypto_utils.kyber_generate_keypair()
    end = time.perf_counter()
    gen_time = (end - start) * 1000
    print(f"Kyber-512 Key Generation: {gen_time:.3f} ms")
    
    start = time.perf_counter()
    ss_sender, ct = crypto_utils.kyber_encapsulate(pk)
    end = time.perf_counter()
    encap_time = (end - start) * 1000
    print(f"Kyber-512 Encapsulation: {encap_time:.3f} ms")
    
    start = time.perf_counter()
    ss_receiver = crypto_utils.kyber_decapsulate(ct, sk)
    end = time.perf_counter()
    decap_time = (end - start) * 1000
    print(f"Kyber-512 Decapsulation: {decap_time:.3f} ms")
    
    # 2. Audio Processing (Chunk of 1024 bytes = 64ms of audio)
    audio_chunk = os.urandom(1024)
    session_key = ss_sender
    aesgcm = AESGCM(session_key)
    nonce = os.urandom(12)
    idx = 1234
    
    # Obfuscation
    start = time.perf_counter()
    obf = crypto_utils.obfuscate_audio(audio_chunk, session_key, idx)
    end = time.perf_counter()
    obf_time = (end - start) * 1000
    print(f"Identity Obfuscation (XOR - 1024 bytes): {obf_time:.3f} ms")
    
    # Encryption
    start = time.perf_counter()
    ct_audio = aesgcm.encrypt(nonce, obf, idx.to_bytes(4, 'big'))
    end = time.perf_counter()
    enc_time = (end - start) * 1000
    print(f"AES-256-GCM Encryption (1024 bytes): {enc_time:.3f} ms")
    
    # Decryption
    start = time.perf_counter()
    dec_audio = aesgcm.decrypt(nonce, ct_audio, idx.to_bytes(4, 'big'))
    end = time.perf_counter()
    dec_time = (end - start) * 1000
    print(f"AES-256-GCM Decryption (1024 bytes): {dec_time:.3f} ms")
    
    # De-obfuscation
    start = time.perf_counter()
    clear = crypto_utils.deobfuscate_audio(dec_audio, session_key, idx)
    end = time.perf_counter()
    deobf_time = (end - start) * 1000
    print(f"De-obfuscation (XOR - 1024 bytes): {deobf_time:.3f} ms")
    
    total_processing_per_chunk = obf_time + enc_time + dec_time + deobf_time
    print(f"\nTotal Cryptographic overhead per audio chunk: {total_processing_per_chunk:.3f} ms")
    print(f"Percentage of chunk duration (64ms): {(total_processing_per_chunk/64)*100:.2f}%")

if __name__ == "__main__":
    benchmark()
