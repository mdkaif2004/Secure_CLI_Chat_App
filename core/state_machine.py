from enum import Enum, auto

class AppState(Enum):
    INIT = auto()
    INPUT_VALIDATION = auto()
    SEARCHING = auto()
    USER_FOUND = auto()
    KEY_SETUP = auto()
    CONFIRMATION = auto() # Prompt mentioned this
    CONNECTED = auto()
    CHAT_ACTIVE = auto() # Maybe same as connected?
    DISCONNECTED = auto()
    SESSION_DESTROYED = auto()

class StateMachine:
    def __init__(self):
        self.current_state = AppState.INIT

    def transition_to(self, new_state: AppState):
        # Strict transition logic could go here
        # For now, we just log/update
        self.current_state = new_state
        # In a real app, we'd validate if the transition is allowed (e.g. INIT -> CONNECTED is illegal)
