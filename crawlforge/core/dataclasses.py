"""
Core dataclasses for CrawlForge slot game automation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ActionType(Enum):
    """Supported action types for game automation."""
    TAP = "tap"
    SWIPE = "swipe"
    PRESS_BACK = "press_back"
    WAIT = "wait"
    INPUT_TEXT = "input_text"
    LONG_PRESS = "long_press"


class GamePhase(Enum):
    """Game phase states for slot games."""
    IDLE = "idle"
    SPINNING = "spinning"
    BONUS = "bonus"
    FREE_SPIN = "free_spin"
    COLLECTING = "collecting"
    FEATURE_TRIGGERED = "feature_triggered"
    UNKNOWN = "unknown"


@dataclass
class Action:
    """Represents a game action to be executed."""
    action_type: ActionType
    x: Optional[int] = None
    y: Optional[int] = None
    x1: Optional[int] = None
    y1: Optional[int] = None
    x2: Optional[int] = None
    y2: Optional[int] = None
    text: Optional[str] = None
    duration_ms: int = 300


@dataclass
class SlotGameState:
    """Slot game-specific state."""
    balance: int = 0
    last_win: int = 0
    bet_amount: int = 0
    reel_positions: list = field(default_factory=list)
    paylines: list = field(default_factory=list)
    free_spins_remaining: int = 0
    bonus_multiplier: float = 1.0


@dataclass
class GameState:
    """Generic game state with slot-specific extension."""
    screen: Optional[bytes] = None
    ui_elements: dict = field(default_factory=dict)
    game_phase: GamePhase = GamePhase.UNKNOWN
    raw_data: dict = field(default_factory=dict)
    slot_state: Optional[SlotGameState] = None


@dataclass
class Strategy:
    """Game strategy configuration."""
    name: str
    bet_strategy: str = "flat"
    max_bet: int = 100
    min_bet: int = 1
    stop_on_balance: Optional[int] = None
    max_spins: Optional[int] = None


@dataclass
class GameData:
    """Captured game data result."""
    data_type: str
    value: any
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)
