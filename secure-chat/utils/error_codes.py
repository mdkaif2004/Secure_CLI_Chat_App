class ErrorCodes:
    SUCCESS = 0
    ERR_NETWORK = 101
    ERR_CRYPTO_GEN = 201
    ERR_CRYPTO_DECRYPT = 202
    ERR_SESSION_TIMEOUT = 301
    ERR_SESSION_INVALID = 302
    ERR_PEER_DISCONNECT = 303
    ERR_SECURITY_VIOLATION = 401
    ERR_INTERNAL = 500

class SecureChatError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")
