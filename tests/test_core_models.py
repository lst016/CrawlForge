"""
Tests for core data models.
"""

import pytest
from crawlforge.core.models import (
    GameState, Action, GameData, ActionResult,
    DetectionResult, RuntimeType,
)


def test_game_state_defaults():
    state = GameState()
    assert state.screen is None
    assert state.screen_b64 is None
    assert state.ui_elements == []
    assert state.game_phase == "unknown"
    assert state.gold_amount is None


def test_game_state_with_values():
    state = GameState(screen=b"fake", game_phase="playing", gold_amount=1000)
    assert state.screen == b"fake"
    assert state.game_phase == "playing"
    assert state.gold_amount == 1000


def test_action_tap():
    action = Action(action_type="tap", x=100, y=200)
    assert action.action_type == "tap"
    assert action.x == 100
    assert action.y == 200


def test_action_swipe():
    action = Action(action_type="swipe", x1=100, y1=200, x2=300, y2=400, duration_ms=500)
    assert action.action_type == "swipe"
    assert action.x1 == 100
    assert action.x2 == 300


def test_action_text():
    action = Action(action_type="text", text="hello")
    assert action.action_type == "text"
    assert action.text == "hello"


def test_game_data():
    data = GameData(game_name="Test", data_type="gold", value=5000)
    assert data.game_name == "Test"
    assert data.value == 5000


def test_action_result_success():
    result = ActionResult(success=True, duration_ms=150.0)
    assert result.success is True


def test_action_result_failure():
    result = ActionResult(success=False, error="oops")
    assert result.success is False
    assert result.error == "oops"


def test_runtime_type_enum():
    assert RuntimeType.PLAYWRIGHT.value == "playwright"
    assert RuntimeType.ADB.value == "adb"
    assert RuntimeType.UIAUTO.value == "uiauto"
