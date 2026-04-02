"""
Abstract interfaces for CrawlForge components.
"""

from abc import ABC, abstractmethod
from typing import Optional

from .dataclasses import GameState, Action, GameData, GamePhase


class GameAdapter(ABC):
    """Abstract game adapter interface."""

    @abstractmethod
    async def detect_state(self, screenshot: bytes) -> GameState:
        """Detect current game state from screenshot."""
        ...

    @abstractmethod
    async def generate_action(self, state: GameState, goal: str) -> Action:
        """Generate next action based on state and goal."""
        ...

    @abstractmethod
    async def extract_data(self, state: GameState) -> GameData:
        """Extract game data from state."""
        ...


class Runtime(ABC):
    """Abstract runtime interface."""

    @abstractmethod
    async def screenshot(self) -> bytes:
        """Capture screenshot."""
        ...

    @abstractmethod
    async def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        ...

    @abstractmethod
    async def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300
    ) -> None:
        """Swipe from (x1, y1) to (x2, y2)."""
        ...

    @abstractmethod
    async def press_back(self) -> None:
        """Press back button."""
        ...

    @abstractmethod
    def is_alive(self) -> bool:
        """Check if runtime is alive/connected."""
        ...


class GameDetector(ABC):
    """Abstract game state detector interface."""

    @abstractmethod
    def detect_phase(self, screenshot: bytes) -> GamePhase:
        """Detect game phase from screenshot."""
        ...

    @abstractmethod
    def extract_balance(self, screenshot: bytes) -> int:
        """Extract balance from screenshot."""
        ...

    @abstractmethod
    def detect_spin_button(self, screenshot: bytes) -> Optional[tuple]:
        """Find spin button coordinates."""
        ...

    @abstractmethod
    def detect_bonus_round(self, screenshot: bytes) -> bool:
        """Detect if bonus round is active."""
        ...
