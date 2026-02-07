import nacl.utils
from nacl.public import PrivateKey, PublicKey
from .memory_wiper import MemoryWiper

class KeyManager:
    def __init__(self):
        self._private_key = None
        self._public_key = None
        self.peer_public_key = None

    def generate_ephemeral_keys(self):
        """Generates a fresh Curve25519 keypair for this session."""
        self._private_key = PrivateKey.generate()
        self._public_key = self._private_key.public_key

    def get_public_key_bytes(self) -> bytes:
        if not self._public_key:
            raise ValueError("Keys not generated")
        return self._public_key.encode()

    def load_peer_public_key(self, raw_bytes: bytes):
        """Loads the remote peer's public key."""
        self.peer_public_key = PublicKey(raw_bytes)

    def get_private_key(self) -> PrivateKey:
        if not self._private_key:
            raise ValueError("Keys not generated")
        return self._private_key

    def wipe_keys(self):
        """
        Best-effort memory wipe. 
        Python's GC makes true memory wiping hard, but we drop references.
        """
        # In a real implementation we would hold keys in a mutable buffer (bytearray)
        # to strictly overwrite them. PyNaCl PrivateKey objects are immutable wrappers.
        # We drop the reference and force GC.
        self._private_key = None
        self._public_key = None
        self.peer_public_key = None
        MemoryWiper.force_gc()
