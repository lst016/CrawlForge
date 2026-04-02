"""
CrawlForge - AI-Driven Multi-Game Crawler Framework
"""

__version__ = "0.1.0"
__author__ = "CrawlForge Team"

# Import core components
from .core.dataclasses import (
    Action,
    ActionType,
    GameData,
    GamePhase,
    GameState,
    SlotGameState,
    Strategy,
)
from .core.exceptions import (
    AdapterError,
    CrawlForgeError,
    DetectionError,
    EvolutionError,
    RuntimeError,
)
from .core.interfaces import GameAdapter, GameDetector, Runtime

__all__ = [
    # dataclasses
    "Action",
    "ActionType",
    "GameData",
    "GamePhase",
    "GameState",
    "SlotGameState",
    "Strategy",
    # exceptions
    "CrawlForgeError",
    "RuntimeError",
    "AdapterError",
    "EvolutionError",
    "DetectionError",
    # interfaces
    "GameAdapter",
    "GameDetector",
    "Runtime",
]
