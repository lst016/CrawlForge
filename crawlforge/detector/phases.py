"""
Slot Game Phases - enum of all possible slot game states.
"""

from enum import Enum


class SlotPhase(Enum):
    """Slot game phase detection states."""
    UNKNOWN = "unknown"
    TITLE_SCREEN = "title_screen"
    LOADING = "loading"
    MAIN_LOBBY = "main_lobby"
    GAME_READY = "game_ready"
    SPINNING = "spinning"
    WIN_DISPLAY = "win_display"
    FREE_SPINS = "free_spins"
    BONUS_GAME = "bonus_game"
    SETTINGS = "settings"
    CONNECTION_ERROR = "connection_error"
    MAINTENANCE = "maintenance"


class SpinState(Enum):
    """Reel spin state."""
    IDLE = "idle"
    SPINNING = "spinning"
    STOPPING = "stopping"
    STOPPED = "stopped"


class BalanceState(Enum):
    """Balance tracking state."""
    NORMAL = "normal"
    LOW = "low"
    EMPTY = "empty"
    INSUFFICIENT = "insufficient"
