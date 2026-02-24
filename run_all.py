"""
Startup script for PQC Audio system
Starts:
1. Key Registry Server (Flask) on port 5001
2. Receiver App (Streamlit) on port 8501
3. Sender App (Streamlit) on port 8502

Run this script to start the entire system at once.
"""

import subprocess
import time
import sys
import os

def run_command(command, description, port=None):
    """Run a command in a new terminal window."""
    print(f"🚀 Starting {description}...")
    
    if sys.platform == "win32":
        # Windows: use 'start' command to open new terminal
        if port:
            full_command = f'start "PQC Audio - {description}" cmd /k "{command}"'
        else:
            full_command = f'start "PQC Audio - {description}" cmd /k "{command}"'
        os.system(full_command)
    else:
        # Linux/Mac: use gnome-terminal or similar
        os.system(f'{command} &')
    
    time.sleep(2)  # Wait for process to start

def main():
    print("\n" + "="*70)
    print("🔐 PQC AUDIO SYSTEM - STARTUP")
    print("="*70)
    print()
    
    # Get the current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print(f"📂 Working directory: {script_dir}")
    print()
    
    # Check if required files exist
    required_files = [
        'key_registry_server.py',
        'receiver_app.py',
        'sender_app.py',
        'crypto_utils.py',
        'server.py'
    ]
    
    print("✅ Checking required files...")
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✓ {file}")
        else:
            print(f"   ✗ {file} - MISSING!")
    print()
    
    # Start Key Registry Server
    print("─" * 70)
    print("1️⃣  KEY REGISTRY SERVER")
    print("─" * 70)
    run_command(
        'python key_registry_server.py',
        "Key Registry Server (Port 5001)"
    )
    print("   ✓ Server starting at http://localhost:5001")
    print()
    
    # Start Receiver App
    print("─" * 70)
    print("2️⃣  RECEIVER APP")
    print("─" * 70)
    run_command(
        'streamlit run receiver_app.py --server.port 8501',
        "Receiver App (Port 8501)"
    )
    print("   ✓ Receiver app starting at http://localhost:8501")
    print()
    
    # Start Sender App
    print("─" * 70)
    print("3️⃣  SENDER APP")
    print("─" * 70)
    run_command(
        'streamlit run sender_app.py --server.port 8502',
        "Sender App (Port 8502)"
    )
    print("   ✓ Sender app starting at http://localhost:8502")
    print()
    
    # Print summary
    print("="*70)
    print("✅ ALL SERVICES STARTED!")
    print("="*70)
    print()
    print("📍 ACCESS POINTS:")
    print("   • Key Registry Server: http://localhost:5001")
    print("   • Receiver App:        http://localhost:8501")
    print("   • Sender App:          http://localhost:8502")
    print()
    print("📋 WORKFLOW:")
    print("   1. Open Receiver App → Generate Keypair → Register with username")
    print("   2. Open Sender App → Enter receiver username → Fetch Public Key")
    print("   3. Upload audio file → Send to receiver")
    print()
    print("💡 TIPS:")
    print("   • Make sure Key Registry Server is running before apps")
    print("   • Both apps connect to localhost:5001 for key exchange")
    print("   • You can run multiple receiver/sender instances")
    print()
    print("⚠️  Press Ctrl+C to stop any service. Ctrl+C in this window won't stop them.")
    print("="*70)
    print()
    
    print("✋ This window will remain open.")
    print("Close individual service windows to stop them.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutdown signal received. Please close individual windows manually.")

if __name__ == '__main__':
    main()
