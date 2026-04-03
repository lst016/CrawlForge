"""
Arcade Game Adapter - concrete adapter for arcade-style games.
"""

from typing import Optional
from ..core import GameState, Action, GameData, Runtime
from .base import GameAdapter, AdapterConfig


class ArcadeGameAdapter(GameAdapter):
    """
    Concrete arcade game adapter.

    Suitable for tap-based arcade games, runner games, and casual games.
    """

    def __init__(
        self,
        runtime: Runtime,
        game_name: str = "ArcadeGame",
        game_version: str = "1.0",
        config: Optional[AdapterConfig] = None,
    ):
        super().__init__(runtime, game_name, game_version, config)
        self._last_phase = "unknown"
        self._score: int = 0
        self._lives: int = 3

    async def detect_state(self, screenshot: bytes) -> GameState:
        """Detect arcade game state."""
        import time

        state = GameState(
            screen=screenshot,
            game_phase="playing",
            raw_data={
                "score": self._score,
                "lives": self._lives,
            },
            timestamp=time.time(),
        )
        return state

    async def generate_action(self, state: GameState, goal: str) -> Action:
        """Generate action based on goal and state."""
        goal_lower = goal.lower()

        if goal_lower in ("tap", "play"):
            # Tap center of screen
            return Action(action_type="tap", x=540, y=960)

        elif goal_lower in ("left", "swipe left"):
            return Action(
                action_type="swipe",
                x1=200, y1=960,
                x2=540, y2=960,
            )

        elif goal_lower in ("right", "swipe right"):
            return Action(
                action_type="swipe",
                x1=880, y1=960,
                x2=540, y2=960,
            )

        elif goal_lower in ("jump", "up"):
            return Action(
                action_type="swipe",
                x1=540, y1=1200,
                x2=540, y2=600,
            )

        elif goal_lower in ("pause", "stop"):
            return Action(action_type="tap", x=980, y=100)

        else:
            return Action(action_type="wait", duration_ms=500)

    async def extract_data(self, state: GameState) -> GameData:
        """Extract arcade game data."""
        import time

        return GameData(
            game_name=self.game_name,
            data_type="arcade_stats",
            value={
                "score": state.raw_data.get("score", self._score),
                "lives": state.raw_data.get("lives", self._lives),
                "phase": state.game_phase,
            },
            timestamp=time.time(),
        )
