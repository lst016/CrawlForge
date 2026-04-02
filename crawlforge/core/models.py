"""
Core data models for CrawlForge.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


class RuntimeType(Enum):
    """Supported runtime types."""
    PLAYWRIGHT = "playwright"
    ADB = "adb"
    WIN32 = "win32"
    HTTP = "http"
    UIAUTO = "uiauto"


@dataclass
class GameState:
    """Game state snapshot."""
    screen: Optional[bytes] = None
    screen_b64: Optional[str] = None
    ui_elements: list = field(default_factory=list)
    game_phase: str = "unknown"
    gold_amount: Optional[int] = None
    player_level: Optional[int] = None
    raw_data: dict = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class Action:
    """Game action to execute."""
    action_type: str
    x: Optional[int] = None
    y: Optional[int] = None
    x1: Optional[int] = None
    y1: Optional[int] = None
    x2: Optional[int] = None
    y2: Optional[int] = None
    text: Optional[str] = None
    duration_ms: int = 300
    key: Optional[str] = None


@dataclass
class GameData:
    """Extracted game data."""
    game_name: str
    data_type: str
    value: Any
    game_version: str = "unknown"
    timestamp: float = 0.0
    raw: dict = field(default_factory=dict)


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    screenshot_after: Optional[bytes] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class DetectionResult:
    """Result of game state detection."""
    state: GameState
    confidence: float = 1.0
    matched_template: Optional[str] = None
    detection_method: str = "ai"
