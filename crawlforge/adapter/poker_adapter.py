"""
Poker Game Adapter - concrete adapter for video poker games.
"""

from typing import Optional
from ..core import GameState, Action, GameData, Runtime
from .base import GameAdapter, AdapterConfig


class PokerGameAdapter(GameAdapter):
    """
    Concrete video poker adapter.

    Supports Jacks or Better, Deuces Wild, and other video poker variants.
    """

    def __init__(
        self,
        runtime: Runtime,
        game_name: str = "VideoPoker",
        game_version: str = "1.0",
        variant: str = "jacks_or_better",
        config: Optional[AdapterConfig] = None,
    ):
        super().__init__(runtime, game_name, game_version, config)
        self.variant = variant
        self._held_cards: list[int] = []
        self._bet_level: int = 1
        self._last_phase: str = "unknown"

    async def detect_state(self, screenshot: bytes) -> GameState:
        """Detect poker game state."""
        import time

        # For now, return a generic state
        # In production, this would use OCR/card detection
        state = GameState(
            screen=screenshot,
            game_phase="dealt",
            raw_data={
                "held_cards": self._held_cards,
                "bet_level": self._bet_level,
                "variant": self.variant,
            },
            timestamp=time.time(),
        )
        return state

    async def generate_action(self, state: GameState, goal: str) -> Action:
        """Generate action based on goal and state."""
        goal_lower = goal.lower()

        if goal_lower in ("deal", "draw"):
            # Tap the deal/draw button (center bottom)
            return Action(action_type="tap", x=540, y=2000)

        elif goal_lower.startswith("hold"):
            # Extract card index from goal (e.g., "hold 1", "hold 2 3")
            parts = goal_lower.split()
            if len(parts) > 1:
                try:
                    indices = [int(p) - 1 for p in parts[1:]]
                    self._held_cards = indices
                except ValueError:
                    pass
            return Action(action_type="wait", duration_ms=100)

        elif goal_lower in ("bet", "bet max"):
            if goal_lower == "bet max":
                self._bet_level = 5
            else:
                self._bet_level = min(self._bet_level + 1, 5)
            return Action(action_type="tap", x=540, y=1850)

        elif goal_lower in ("collect", "collect win"):
            return Action(action_type="tap", x=540, y=1600)

        else:
            return Action(action_type="wait", duration_ms=500)

    async def extract_data(self, state: GameState) -> GameData:
        """Extract poker game data."""
        import time

        return GameData(
            game_name=self.game_name,
            data_type="poker_stats",
            value={
                "variant": self.variant,
                "bet_level": self._bet_level,
                "held_cards": self._held_cards,
                "phase": state.game_phase,
            },
            timestamp=time.time(),
        )
