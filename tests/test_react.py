"""
Tests for ReAct Loop models.
"""

import pytest
from crawlforge.react.models import (
    ReActConfig, ReActState, ReActStep, LoopResult,
    Ability, AbilityRegistry, ReflectionResult,
)


def test_react_config_defaults():
    config = ReActConfig()
    assert config.max_iterations == 50
    assert config.step_delay_ms == 500
    assert config.confidence_threshold == 0.7
    assert config.stop_on_error is True


def test_ability_registry():
    registry = AbilityRegistry()

    def dummy_handler(ctx, **params):
        return {"result": "ok"}

    ability = Ability(
        name="test_spin",
        description="Test spin ability",
        parameters={"type": "object"},
        returns={"type": "object"},
        handler=dummy_handler,
    )
    registry.register(ability)

    assert registry.get("test_spin") is not None
    assert len(registry.list_abilities()) == 1

    result = registry.call("test_spin", {})
    assert result == {"result": "ok"}


def test_ability_registry_unknown():
    registry = AbilityRegistry()
    with pytest.raises(ValueError, match="Unknown ability"):
        registry.call("nonexistent", {})


def test_reflection_result_defaults():
    r = ReflectionResult()
    assert r.should_continue is True
    assert r.goal_progress == 0.0
    assert r.loop_should_stop is False
    assert r.reasons == []


def test_loop_result():
    result = LoopResult(
        goal="spin 100 times",
        total_iterations=10,
        total_duration_ms=5000.0,
        success=False,
    )
    assert result.goal == "spin 100 times"
    assert result.total_iterations == 10
    assert result.success is False
