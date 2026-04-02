"""
CrawlForge - AI-Driven Multi-Game Crawler Framework
"""

__version__ = "0.1.0"
__author__ = "CrawlForge Team"

from .orchestrator import CrawlForge
from .adapter import GameAdapter, GameState, Action, GameData
from .registry import AdapterRegistry

__all__ = [
    "CrawlForge",
    "GameAdapter",
    "GameState",
    "Action",
    "GameData",
    "AdapterRegistry",
]
