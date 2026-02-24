"""
Voice Call Handler - Manages call lifecycle and signaling
"""

import requests
import threading
import time
from datetime import datetime

class CallHandler:
    """Manages voice call initiation, acceptance, rejection, and termination."""
    
    def __init__(self, username, registry_server):
        """
        Initialize call handler.
        
        Args:
            username: Your registered username (str)
            registry_server: Registry server URL (str, e.g., "http://192.168.1.100:5001")
        """
        self.username = username
        self.registry_server = registry_server
        self.active_call = None
        self.incoming_call = None
        self.is_listening = False
        self.listen_thread = None
    
    def initiate_call(self, callee_username, caller_listen_port, session_key_ciphertext):
        """
        Initiate a voice call to another user.
        
        Args:
            callee_username: Recipient's username (str)
            caller_listen_port: Port to listen on for audio (int)
            session_key_ciphertext: Encrypted session key from Kyber KEM (bytes)
        
        Returns:
            call_info: Dictionary with call details {call_id, callee_ip, callee_listen_port, ...}
            or None if failed
        """
        try:
            import base64
            
            # Encode ciphertext as base64 for JSON transmission
            ct_b64 = base64.b64encode(session_key_ciphertext).decode('utf-8')
            
            # Send call initiation to registry
            response = requests.post(
                f"{self.registry_server}/call/initiate",
                json={
                    "caller": self.username,
                    "callee": callee_username,
                    "caller_listen_port": caller_listen_port,
                    "session_key_ciphertext": ct_b64
                },
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"❌ Call initiation failed: {response.json().get('message', 'Unknown error')}")
                return None
            
            call_info = response.json()
            self.active_call = call_info
            self.active_call['call_status'] = 'ringing'
            
            print(f"📞 Calling {callee_username}...")
            print(f"   Callee IP: {call_info['callee_ip']}:{call_info['callee_listen_port']}")
            
            return call_info
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Call initiation error: {e}")
            return None
        except Exception as e:
            print(f"❌ Call initiation error: {e}")
            return None
    
    def wait_for_answer(self, timeout=30):
        """
        Wait for callee to answer the call.
        
        Args:
            timeout: Maximum seconds to wait (int)
        
        Returns:
            True if answered, False if timeout or rejected
        """
        if not self.active_call:
            return False
        
        print(f"⏳ Waiting for answer... (timeout: {timeout}s)")
        
        call_id = self.active_call.get('call_id')
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check call status
                response = requests.get(
                    f"{self.registry_server}/call/status/{call_id}",
                    timeout=2
                )
                
                if response.status_code == 200:
                    status_info = response.json()
                    call_status = status_info.get('status')
                    
                    if call_status == 'active':
                        print(f"✅ Call answered!")
                        self.active_call['call_status'] = 'active'
                        self.active_call['answered_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        return True
                    elif call_status == 'rejected':
                        print(f"❌ Call rejected")
                        self.active_call = None
                        return False
                
                time.sleep(1)
            
            except Exception as e:
                print(f"⚠️ Error checking call status: {e}")
                time.sleep(1)
        
        print(f"❌ Call timeout (no answer)")
        return False
    
    def end_call(self):
        """End the active call."""
        if not self.active_call:
            return
        
        try:
            call_id = self.active_call.get('call_id')
            
            response = requests.post(
                f"{self.registry_server}/call/hangup",
                json={"call_id": call_id},
                timeout=5
            )
            
            print(f"✅ Call ended")
            self.active_call = None
        
        except Exception as e:
            print(f"⚠️ Error ending call: {e}")
            self.active_call = None
    
    def start_listening_for_calls(self):
        """Start listening for incoming calls (in background thread)."""
        if self.is_listening:
            return
        
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        
        print(f"👂 Listening for incoming calls...")
    
    def stop_listening_for_calls(self):
        """Stop listening for incoming calls."""
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
    
    def _listen_loop(self):
        """Background thread: Poll for incoming calls."""
        # Note: In a real system, would use WebSocket or server-push instead of polling
        # For now, polling every 2 seconds is acceptable for college project
        
        while self.is_listening:
            try:
                # Get registry and check for incoming calls
                # This would require registry to track pending calls for each user
                # For MVP, skip detailed implementation
                
                time.sleep(2)
            
            except Exception as e:
                print(f"⚠️ Listen loop error: {e}")
                time.sleep(2)
    
    def accept_call(self, call_id):
        """
        Accept an incoming call.
        
        Args:
            call_id: ID of the incoming call (str)
        
        Returns:
            caller_info: Dictionary with caller's IP and port, or None if failed
        """
        try:
            response = requests.post(
                f"{self.registry_server}/call/accept",
                json={"call_id": call_id},
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"❌ Call acceptance failed: {response.json().get('message', 'Unknown error')}")
                return None
            
            call_info = response.json()
            self.active_call = {
                'call_id': call_id,
                'caller_ip': call_info.get('caller_ip'),
                'caller_port': call_info.get('caller_listen_port'),
                'session_key_ciphertext': call_info.get('session_key_ciphertext'),
                'call_status': 'active',
                'direction': 'incoming'
            }
            
            print(f"✅ Call accepted")
            print(f"   Caller IP: {call_info['caller_ip']}:{call_info['caller_listen_port']}")
            
            return call_info
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Call acceptance error: {e}")
            return None
        except Exception as e:
            print(f"❌ Call acceptance error: {e}")
            return None
    
    def reject_call(self, call_id):
        """
        Reject an incoming call.
        
        Args:
            call_id: ID of the incoming call (str)
        
        Returns:
            True if rejected successfully, False otherwise
        """
        try:
            response = requests.post(
                f"{self.registry_server}/call/reject",
                json={"call_id": call_id},
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"❌ Call rejection failed: {response.json().get('message', 'Unknown error')}")
                return False
            
            print(f"✅ Call rejected")
            return True
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Call rejection error: {e}")
            return False
        except Exception as e:
            print(f"❌ Call rejection error: {e}")
            return False
    
    def get_active_call_info(self):
        """Get information about active call."""
        return self.active_call
    
    def is_call_active(self):
        """Check if there's an active call."""
        return self.active_call is not None and self.active_call.get('call_status') == 'active'
