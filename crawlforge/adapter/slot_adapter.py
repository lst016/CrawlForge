"""
Slot Game Adapter - concrete adapter for slot games.
"""

from typing import Optional
from ..core import GameState, Action, GameData, Runtime
from .base import GameAdapter, AdapterConfig


class SlotGameAdapter(GameAdapter):
    """
    Concrete slot game adapter.

    Implements the GameAdapter interface for slot game automation,
    using SlotGameDetector for state detection when available.
    """

    def __init__(
        self,
        runtime: Runtime,
        game_name: str = "GenericSlot",
        game_version: str = "1.0",
        config: Optional[AdapterConfig] = None,
    ):
        super().__init__(runtime, game_name, game_version, config)
        self._last_detection = None
        self._total_wins: float = 0
        self._free_spins_triggered: int = 0

        # Try to use the slot detector if available
        self._detector = None
        try:
            from ..detector import SlotGameDetector, SlotDetectionResult
            self._detector = SlotGameDetector(runtime, game_name)
        except ImportError:
            pass

    async def detect_state(self, screenshot: bytes) -> GameState:
        """Detect slot game state from screenshot."""
        import time

        detection_result = None
        if self._detector is not None and hasattr(self.runtime, "dump_hierarchy"):
            try:
                hierarchy = await self.runtime.dump_hierarchy()
                detection_result = await self._detector.detect(hierarchy)
            except Exception:
                pass

        if detection_result is None:
            # Fallback: basic state
            from ..detector import SlotDetectionResult, SlotPhase
            detection_result = SlotDetectionResult(
                phase=SlotPhase.GAME_READY,
                confidence=0.0,
            )

        phase_value = (
            detection_result.phase.value
            if detection_result.phase else "unknown"
        )
        self._last_detection = detection_result

        state = GameState(
            screen=screenshot,
            game_phase=phase_value,
            gold_amount=detection_result.balance,
            raw_data={
                "spin_state": (
                    detection_result.spin_state.value
                    if detection_result.spin_state else "idle"
                ),
                "win_amount": detection_result.win_amount or 0,
                "free_spins": detection_result.free_spins_remaining or 0,
                "reel_positions": getattr(detection_result, "reel_positions", []),
            },
            timestamp=time.time(),
        )
        return state

    async def generate_action(self, state: GameState, goal: str) -> Action:
        """Generate action based on goal and state."""
        goal_lower = goal.lower()

        # Spin actions
        if goal_lower in ("spin", "start", "play", "go"):
            return Action(action_type="tap", x=540, y=2050)

        elif goal_lower in ("auto", "auto spin", "autoplay"):
            return Action(action_type="tap", x=800, y=2050)

        elif goal_lower in ("stop", "stop spin"):
            return Action(action_type="tap", x=540, y=960)

        # Bet adjustments
        elif goal_lower in ("bet min", "min bet", "min"):
            return Action(action_type="tap", x=200, y=2050)

        elif goal_lower in ("bet max", "max bet", "max"):
            return Action(action_type="tap", x=880, y=2050)

        elif goal_lower in ("bet up", "increase bet"):
            return Action(action_type="tap", x=700, y=2050)

        elif goal_lower in ("bet down", "decrease bet"):
            return Action(action_type="tap", x=380, y=2050)

        # Collection
        elif goal_lower in ("collect", "claim", "collect win", "collect all"):
            return Action(action_type="tap", x=540, y=1200)

        elif goal_lower in ("skip", "skip bonus"):
            return Action(action_type="tap", x=880, y=200)

        # Feature triggers
        elif goal_lower in ("gamble", "red black", "double"):
            return Action(action_type="tap", x=270, y=1200)

        elif goal_lower in ("gamble black"):
            return Action(action_type="tap", x=810, y=1200)

        # Free spin actions
        elif goal_lower in ("free spin", "fs"):
            return Action(action_type="tap", x=540, y=1600)

        else:
            return Action(action_type="wait", duration_ms=1000)

    async def extract_data(self, state: GameState) -> GameData:
        """Extract game data from current state."""
        import time

        self.increment_spin_count()
        win_amount = state.raw_data.get("win_amount") or 0
        free_spins = state.raw_data.get("free_spins") or 0

        if win_amount > 0:
            self._total_wins += win_amount
        if free_spins > 0:
            self._free_spins_triggered += 1

        return GameData(
            game_name=self.game_name,
            data_type="slot_session",
            value={
                "spins": self.get_spin_count(),
                "total_wins": self._total_wins,
                "balance": state.gold_amount,
                "game_phase": state.game_phase,
                "win_amount": win_amount,
                "free_spins_triggered": self._free_spins_triggered,
                "free_spins_remaining": state.raw_data.get("free_spins", 0),
            },
            timestamp=time.time(),
        )

    def get_capabilities(self) -> list[str]:
        """Return slot adapter capabilities."""
        base = super().get_capabilities()
        base.extend([
            "bet_min",
            "bet_max",
            "bet_up",
            "bet_down",
            "auto_spin",
            "stop_spin",
            "gamble",
            "skip_bonus",
        ])
        return base
