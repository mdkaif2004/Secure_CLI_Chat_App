from nacl.public import Box
from nacl.exceptions import CryptoError
from crypto.key_manager import KeyManager

class EncryptionHandler:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.box = None

    def setup_secure_channel(self):
        """Creates the NaCl Box using local private key and peer public key."""
        if not self.key_manager.get_private_key() or not self.key_manager.peer_public_key:
            raise ValueError("Keys missing for secure channel setup")
        
        self.box = Box(self.key_manager.get_private_key(), self.key_manager.peer_public_key)

    def encrypt_message(self, plaintext: str) -> bytes:
        if not self.box:
            raise ValueError("Secure channel not established")
        
        # Determine strict length check here or in pipeline. 
        # Prompt says "Plain Text -> Length Check" before encrypt.
        # We assume bytes encoding happens here.
        return self.box.encrypt(plaintext.encode('utf-8'))

    def decrypt_message(self, encrypted_blob: bytes) -> str:
        if not self.box:
            raise ValueError("Secure channel not established")
        
        try:
            decrypted_bytes = self.box.decrypt(encrypted_blob)
            return decrypted_bytes.decode('utf-8')
        except CryptoError:
            raise ValueError("Decryption failed: integrity check failed")
