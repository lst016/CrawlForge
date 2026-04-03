"""
Base Game Adapter - abstract interface and common utilities.

All concrete game adapters must inherit from GameAdapter and implement
the required abstract methods.
"""

import time
import uuid
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Union

from ..core import GameState, Action, GameData, Runtime
from ..core.interfaces import GameAdapter as ABCGameAdapter


@dataclass
class AdapterConfig:
    """Configuration for a game adapter."""
    game_name: str
    game_version: str = "unknown"
    runtime: Optional[Runtime] = None

    # Detection settings
    confidence_threshold: float = 0.7
    max_retries: int = 3
    retry_delay_ms: int = 500

    # Action settings
    default_bet: int = 100
    max_bet: int = 10000
    auto_collect: bool = True

    # Performance
    screenshot_interval_ms: int = 200
    action_cooldown_ms: int = 300

    # Metadata
    metadata: dict = field(default_factory=dict)


@dataclass
class AdapterMetadata:
    """Metadata about an adapter's implementation."""
    adapter_id: str
    game_name: str
    game_type: str  # "slot", "card", "arcade", etc.
    version: str
    supported_phases: list[str] = field(default_factory=list)
    required_sensors: list[str] = field(default_factory=list)
    author: str = "unknown"
    description: str = ""
    capabilities: list[str] = field(default_factory=list)

    @property
    def adapter_hash(self) -> str:
        return hashlib.md5(
            f"{self.adapter_id}:{self.game_name}:{self.version}".encode()
        ).hexdigest()[:8]


class GameAdapter(ABCGameAdapter):
    """
    Abstract base class for all game adapters.

    Subclasses must implement:
    - detect_state()
    - generate_action()
    - extract_data()

    Optional overrides:
    - validate_environment()
    - calibrate()
    - get_capabilities()

    Usage:
        class MyGameAdapter(GameAdapter):
            async def detect_state(self, screenshot: bytes) -> GameState:
                # ... detection logic
                return state

            async def generate_action(self, state: GameState, goal: str) -> Action:
                # ... action selection logic
                return action

            async def extract_data(self, state: GameState) -> GameData:
                # ... data extraction logic
                return data
    """

    def __init__(
        self,
        runtime: Runtime,
        game_name: str = "UnknownGame",
        game_version: str = "1.0",
        config: Optional[AdapterConfig] = None,
    ):
        super().__init__(runtime)
        self.game_name = game_name
        self.game_version = game_version
        self.config = config or AdapterConfig(game_name=game_name, runtime=runtime)

        # Runtime state
        self._session_id: str = str(uuid.uuid4())[:12]
        self._session_start: Optional[datetime] = None
        self._spin_count: int = 0
        self._action_count: int = 0
        self._errors: int = 0
        self._last_action_time: float = 0.0

        # Performance tracking
        self._total_detection_time_ms: float = 0.0
        self._total_action_time_ms: float = 0.0

    # -------------------------------------------------------------------------
    # Abstract methods (must be implemented by subclasses)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def detect_state(self, screenshot: bytes) -> GameState:
        """
        Detect the current game state from a screenshot.

        Args:
            screenshot: Raw screenshot bytes

        Returns:
            GameState with detected phase, balance, and raw data
        """
        ...

    @abstractmethod
    async def generate_action(self, state: GameState, goal: str) -> Action:
        """
        Generate the next action based on current state and goal.

        Args:
            state: Current game state
            goal: Goal description ("spin", "collect", "max bet", etc.)

        Returns:
            Action to execute
        """
        ...

    @abstractmethod
    async def extract_data(self, state: GameState) -> GameData:
        """
        Extract structured data from the current game state.

        Args:
            state: Current game state

        Returns:
            GameData with extracted values
        """
        ...

    # -------------------------------------------------------------------------
    # Optional overrides
    # -------------------------------------------------------------------------

    async def validate_environment(self) -> tuple[bool, str]:
        """
        Validate that the runtime environment is correctly set up.

        Returns:
            (is_valid, error_message)
        """
        if self.runtime is None:
            return False, "No runtime configured"

        if not self.runtime.is_alive():
            try:
                await self.runtime.start()
            except Exception as e:
                return False, f"Failed to start runtime: {e}"

        return True, ""

    async def calibrate(self, calibration_data: Optional[dict] = None) -> bool:
        """
        Calibrate adapter based on environment or calibration data.

        Args:
            calibration_data: Optional calibration parameters

        Returns:
            True if calibration succeeded
        """
        return True

    def get_capabilities(self) -> list[str]:
        """
        Return list of capabilities this adapter supports.

        Default capabilities:
        - "auto_spin": Can automatically spin
        - "bet_adjust": Can adjust bet amount
        - "collect": Can collect winnings
        - "free_spin": Can trigger/fill free spins
        """
        return [
            "auto_spin",
            "bet_adjust",
            "collect",
            "free_spin",
        ]

    async def pre_action(self, action: Action) -> None:
        """
        Hook called before each action execution.
        Override to add pre-action logic (e.g., cooldown, validation).
        """
        # Enforce action cooldown
        now = time.time() * 1000
        elapsed = now - self._last_action_time
        if elapsed < self.config.action_cooldown_ms:
            await self._wait_ms(self.config.action_cooldown_ms - elapsed)
        self._last_action_time = time.time() * 1000

    async def post_action(self, action: Action, result: Any) -> None:
        """
        Hook called after each action execution.
        Override to add post-action logic (e.g., logging, data recording).
        """
        self._action_count += 1

    async def on_error(self, error: Exception, context: str) -> None:
        """
        Handle an error that occurred during execution.

        Args:
            error: The exception that was raised
            context: Where the error occurred ("detect", "action", "extract", etc.)
        """
        self._errors += 1

    # -------------------------------------------------------------------------
    # Session management
    # -------------------------------------------------------------------------

    async def start_session(self, session_id: Optional[str] = None) -> str:
        """Start a new game session."""
        self._session_id = session_id or str(uuid.uuid4())[:12]
        self._session_start = datetime.now()
        self._spin_count = 0
        self._action_count = 0
        self._errors = 0
        return self._session_id

    async def end_session(self) -> dict:
        """End the current session and return summary."""
        summary = {
            "session_id": self._session_id,
            "game_name": self.game_name,
            "game_version": self.game_version,
            "duration_seconds": (
                (datetime.now() - self._session_start).total_seconds()
                if self._session_start else 0
            ),
            "spin_count": self._spin_count,
            "action_count": self._action_count,
            "error_count": self._errors,
            "avg_detection_ms": (
                self._total_detection_time_ms / max(1, self._spin_count)
            ),
            "avg_action_ms": (
                self._total_action_time_ms / max(1, self._action_count)
            ),
        }
        self._session_start = None
        return summary

    # -------------------------------------------------------------------------
    # Common utilities for subclasses
    # -------------------------------------------------------------------------

    def get_session_id(self) -> str:
        """Return current session ID."""
        return self._session_id

    def get_spin_count(self) -> int:
        """Return current spin count."""
        return self._spin_count

    def increment_spin_count(self) -> int:
        """Increment and return spin count."""
        self._spin_count += 1
        return self._spin_count

    async def _wait_ms(self, ms: float) -> None:
        """Wait for specified milliseconds."""
        import asyncio
        await asyncio.sleep(ms / 1000)

    def _track_detection_time(self, elapsed_ms: float) -> None:
        """Track detection timing."""
        self._total_detection_time_ms += elapsed_ms

    def _track_action_time(self, elapsed_ms: float) -> None:
        """Track action timing."""
        self._total_action_time_ms += elapsed_ms

    def get_stats(self) -> dict:
        """Return adapter statistics."""
        return {
            "session_id": self._session_id,
            "spin_count": self._spin_count,
            "action_count": self._action_count,
            "error_count": self._errors,
            "avg_detection_ms": (
                self._total_detection_time_ms / max(1, self._spin_count)
            ),
            "avg_action_ms": (
                self._total_action_time_ms / max(1, self._action_count)
            ),
        }


class GameAdapterMixin:
    """
    Optional mixin providing common game-specific utilities.

    Use alongside GameAdapter for games that need:
    - Balance tracking
    - Spin history
    - Win/loss analysis
    """

    def __init__(self):
        self._balance_history: list[tuple[float, datetime]] = []
        self._spin_history: list[dict] = []
        self._initial_balance: Optional[float] = None

    def track_balance(self, balance: float) -> None:
        """Record a balance change."""
        if self._initial_balance is None:
            self._initial_balance = balance
        self._balance_history.append((balance, datetime.now()))

    def track_spin(
        self,
        bet: float,
        win: float,
        balance_before: float,
        balance_after: float,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record a spin result."""
        self._spin_history.append({
            "timestamp": datetime.now(),
            "bet": bet,
            "win": win,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "net": win - bet,
            "metadata": metadata or {},
        })

    def get_balance_history(self) -> list[tuple[float, datetime]]:
        return self._balance_history.copy()

    def get_spin_history(self) -> list[dict]:
        return self._spin_history.copy()

    def get_net_profit(self) -> float:
        """Calculate net profit from spin history."""
        if not self._spin_history:
            return 0.0
        return sum(s["net"] for s in self._spin_history)

    def get_roi(self) -> float:
        """Calculate return on investment percentage."""
        total_bet = sum(s["bet"] for s in self._spin_history)
        total_win = sum(s["win"] for s in self._spin_history)
        if total_bet == 0:
            return 0.0
        return (total_win / total_bet - 1) * 100
