"""
Core interfaces and abstractions.
"""

from abc import ABC, abstractmethod
from .models import GameState, Action, ActionResult


class Runtime(ABC):
    """Abstract runtime interface."""

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    async def screenshot(self) -> bytes:
        ...

    @abstractmethod
    async def execute(self, action: Action) -> ActionResult:
        ...

    @abstractmethod
    def is_alive(self) -> bool:
        ...


class GameAdapter(ABC):
    """Abstract game adapter interface."""

    def __init__(self, runtime: Runtime):
        self.runtime = runtime
        self.game_name: str = "unknown"
        self.game_version: str = "unknown"

    @abstractmethod
    async def detect_state(self, screenshot: bytes) -> GameState:
        ...

    @abstractmethod
    async def generate_action(self, state: GameState, goal: str) -> Action:
        ...
