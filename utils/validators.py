import re

def validate_connection_code(code: str) -> bool:
    """
    Validates connection code format:
    Length: 8-16
    Characters: A-Z, 0-9
    """
    if not code:
        return False
    if not (8 <= len(code) <= 16):
        return False
    pattern = r"^[A-Z0-9]+$"
    return bool(re.match(pattern, code))

def validate_message_length(message: str, max_length: int = 1000) -> bool:
    """
    Strict length check. Prompt says <=100 chars in pipeline, 
    but for usability we might allow slightly more, sticking to prompt 100 for now.
    """
    if not message:
        return False
    return len(message) <= max_length
