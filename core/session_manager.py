import asyncio
import base64
from crypto.key_manager import KeyManager
from crypto.encryption import EncryptionHandler
from network.transport import TransportLayer
from core.state_machine import StateMachine, AppState
from utils.error_codes import ErrorCodes, SecureChatError
from security.rate_limiter import RateLimiter

class SessionManager:
    def __init__(self, ui_callback=None):
        self.state_machine = StateMachine()
        self.key_manager = KeyManager()
        self.encryption = EncryptionHandler(self.key_manager)
        self.transport = TransportLayer()
        self.ui_callback = ui_callback
        self.rate_limiter = RateLimiter(max_calls=5, period=1.0) # 5 msgs/sec
        
        # Wire up transport callbacks
        self.transport.on_peer_found_callback = self.on_peer_found
        self.transport.on_peer_lost_callback = self.on_peer_lost
        self.transport.on_message_callback = self.on_network_message

    async def start_session(self, room_code: str):
        self.state_machine.transition_to(AppState.SEARCHING)
        if self.ui_callback: self.ui_callback("SEARCHING")
        
        success = await self.transport.connect(room_code)
        if not success:
            raise SecureChatError(ErrorCodes.ERR_NETWORK, "Could not connect to relay")

    def on_peer_found(self):
        self.state_machine.transition_to(AppState.USER_FOUND)
        if self.ui_callback: self.ui_callback("USER_FOUND")
        
        # Immediately start key exchange
        asyncio.create_task(self.perform_handshake())

    def on_peer_lost(self):
        self.state_machine.transition_to(AppState.DISCONNECTED)
        if self.ui_callback: self.ui_callback("DISCONNECTED")
        asyncio.create_task(self.destroy_session())

    async def perform_handshake(self):
        self.state_machine.transition_to(AppState.KEY_SETUP)
        if self.ui_callback: self.ui_callback("KEY_SETUP")

        # 1. Generate Local Ephemeral Keys
        self.key_manager.generate_ephemeral_keys()
        
        # 2. Send Public Key
        pub_key = self.key_manager.get_public_key_bytes()
        # Encode to base64 for JSON transport
        pub_key_b64 = base64.b64encode(pub_key).decode('utf-8')
        
        await self.transport.send_signal({
            "kind": "KEY_EXCHANGE",
            "key": pub_key_b64
        })

    async def on_network_message(self, data: dict):
        kind = data.get("kind")
        
        if kind == "KEY_EXCHANGE":
            # Received Peer Public Key
            peer_key_b64 = data.get("key")
            peer_key_bytes = base64.b64decode(peer_key_b64)
            
            self.key_manager.load_peer_public_key(peer_key_bytes)
            
            # Setup Encryption Box
            self.encryption.setup_secure_channel()
            
            # If we have both keys, we are ready
            if self.encryption.box:
                self.state_machine.transition_to(AppState.CONNECTED)
                if self.ui_callback: self.ui_callback("CONNECTED")

        elif kind == "MSG":
            # Received Encrypted Message
            encrypted_payload_b64 = data.get("payload")
            encrypted_bytes = base64.b64decode(encrypted_payload_b64)
            
            try:
                plaintext = self.encryption.decrypt_message(encrypted_bytes)
                if self.ui_callback: self.ui_callback("MESSAGE", plaintext)
            except Exception:
                if self.ui_callback: self.ui_callback("ERROR", "Decryption Failed")

    async def send_message(self, text: str):
        if self.state_machine.current_state != AppState.CONNECTED:
            return

        if not self.rate_limiter.check():
             if self.ui_callback: self.ui_callback("ERROR", "Rate limit exceeded. Slow down.")
             return

        encrypted = self.encryption.encrypt_message(text)
        encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
        
        await self.transport.send_signal({
            "kind": "MSG",
            "payload": encrypted_b64
        })

    async def destroy_session(self):
        self.state_machine.transition_to(AppState.SESSION_DESTROYED)
        await self.transport.disconnect()
        self.key_manager.wipe_keys()
        self.encryption.box = None
        if self.ui_callback: self.ui_callback("DESTROYED")
