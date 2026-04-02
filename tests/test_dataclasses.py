"""
Tests for core dataclasses.
"""

import pytest
from crawlforge.core.dataclasses import (
    Action,
    ActionType,
    GameData,
    GamePhase,
    GameState,
    SlotGameState,
    Strategy,
)


class TestActionType:
    def test_action_types_exist(self):
        assert ActionType.TAP.value == "tap"
        assert ActionType.SWIPE.value == "swipe"
        assert ActionType.PRESS_BACK.value == "press_back"
        assert ActionType.WAIT.value == "wait"


class TestGamePhase:
    def test_game_phases_exist(self):
        assert GamePhase.IDLE.value == "idle"
        assert GamePhase.SPINNING.value == "spinning"
        assert GamePhase.BONUS.value == "bonus"
        assert GamePhase.FREE_SPIN.value == "free_spin"
        assert GamePhase.COLLECTING.value == "collecting"
        assert GamePhase.UNKNOWN.value == "unknown"


class TestAction:
    def test_tap_action(self):
        action = Action(action_type=ActionType.TAP, x=100, y=200)
        assert action.action_type == ActionType.TAP
        assert action.x == 100
        assert action.y == 200
        assert action.duration_ms == 300  # default

    def test_swipe_action(self):
        action = Action(
            action_type=ActionType.SWIPE,
            x1=100, y1=200, x2=300, y2=400,
            duration_ms=500,
        )
        assert action.action_type == ActionType.SWIPE
        assert action.x1 == 100
        assert action.y1 == 200
        assert action.x2 == 300
        assert action.y2 == 400
        assert action.duration_ms == 500


class TestSlotGameState:
    def test_default_values(self):
        state = SlotGameState()
        assert state.balance == 0
        assert state.last_win == 0
        assert state.bet_amount == 0
        assert state.reel_positions == []
        assert state.free_spins_remaining == 0
        assert state.bonus_multiplier == 1.0

    def test_with_values(self):
        state = SlotGameState(
            balance=1000,
            last_win=50,
            bet_amount=10,
            reel_positions=[1, 2, 3, 4, 5],
            free_spins_remaining=5,
            bonus_multiplier=2.0,
        )
        assert state.balance == 1000
        assert state.last_win == 50
        assert state.free_spins_remaining == 5


class TestGameState:
    def test_default_game_state(self):
        state = GameState()
        assert state.screen is None
        assert state.game_phase == GamePhase.UNKNOWN
        assert state.slot_state is None

    def test_game_state_with_slot(self):
        slot = SlotGameState(balance=500)
        state = GameState(game_phase=GamePhase.IDLE, slot_state=slot)
        assert state.game_phase == GamePhase.IDLE
        assert state.slot_state.balance == 500


class TestStrategy:
    def test_default_strategy(self):
        strategy = Strategy(name="test")
        assert strategy.name == "test"
        assert strategy.bet_strategy == "flat"
        assert strategy.max_bet == 100
        assert strategy.min_bet == 1
        assert strategy.stop_on_balance is None

    def test_custom_strategy(self):
        strategy = Strategy(
            name="aggressive",
            bet_strategy="martingale",
            max_bet=500,
            min_bet=10,
            stop_on_balance=5000,
            max_spins=100,
        )
        assert strategy.bet_strategy == "martingale"
        assert strategy.max_bet == 500


class TestGameData:
    def test_game_data_creation(self):
        data = GameData(
            data_type="balance",
            value=1000,
            timestamp=1234567890.0,
        )
        assert data.data_type == "balance"
        assert data.value == 1000
        assert data.timestamp == 1234567890.0
        assert data.metadata == {}

    def test_game_data_with_metadata(self):
        data = GameData(
            data_type="spin_result",
            value={"win": True, "amount": 50},
            metadata={"spin_number": 10},
        )
        assert data.metadata["spin_number"] == 10
