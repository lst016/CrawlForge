"""
Slot Game Adapter - concrete adapter for slot games.
"""

from typing import Optional
from ..core import GameState, Action, GameData, Runtime
from ..core.interfaces import GameAdapter
from ..detector import SlotGameDetector, SlotDetectionResult


class SlotGameAdapter(GameAdapter):
    """
    Concrete slot game adapter.

    Implements the GameAdapter interface for slot game automation,
    using SlotGameDetector for state detection.
    """

    def __init__(self, runtime: Runtime, game_name: str = "GenericSlot"):
        super().__init__(runtime)
        self.game_name = game_name
        self.detector = SlotGameDetector(runtime, game_name)
        self._last_detection: Optional[SlotDetectionResult] = None
        self._spin_count: int = 0
        self._total_wins: int = 0

    async def detect_state(self, screenshot: bytes) -> GameState:
        """Detect slot game state."""
        import time
        if hasattr(self.runtime, 'dump_hierarchy'):
            try:
                hierarchy = await self.runtime.dump_hierarchy()
                detection = await self.detector.detect(hierarchy)
            except Exception:
                detection = SlotDetectionResult(
                    phase=None,
                    confidence=0.0,
                )
        else:
            detection = SlotDetectionResult(
                phase=None,
                confidence=0.0,
            )

        self._last_detection = detection

        state = GameState(
            screen=screenshot,
            game_phase=detection.phase.value if detection.phase else "unknown",
            gold_amount=detection.balance,
            raw_data={
                "spin_state": detection.spin_state.value if detection.spin_state else "idle",
                "win_amount": detection.win_amount,
                "free_spins": detection.free_spins_remaining,
            },
            timestamp=time.time(),
        )
        return state

    async def generate_action(self, state: GameState, goal: str) -> Action:
        """Generate action based on goal and state."""
        if goal.lower() in ("spin", "start", "play"):
            return Action(action_type="tap", x=540, y=2050)
        elif goal.lower() in ("collect", "claim"):
            return Action(action_type="tap", x=540, y=1200)
        elif goal.lower() == "auto":
            return Action(action_type="tap", x=800, y=2050)
        else:
            return Action(action_type="wait", duration_ms=1000)

    async def extract_data(self, state: GameState) -> GameData:
        """Extract game data."""
        import time
        self._spin_count += 1
        win = state.raw_data.get("win_amount") or 0
        self._total_wins += win

        return GameData(
            game_name=self.game_name,
            data_type="session_stats",
            value={
                "spins": self._spin_count,
                "total_wins": self._total_wins,
                "balance": state.gold_amount,
            },
            timestamp=time.time(),
        )
