"""
Tests for AI Pipeline models.
"""

import pytest
from crawlforge.ai_pipeline.models import (
    ActionType, SandboxErrorType, ActionStep, ActionPlan,
    BoundingBox, AnalysisResult, SandboxResult, TestResult,
    PipelineConfig, UIElementResult,
)


def test_action_type_enum():
    assert ActionType.TAP.value == "tap"
    assert ActionType.SWIPE.value == "swipe"
    assert ActionType.WAIT.value == "wait"


def test_sandbox_error_type_enum():
    assert SandboxErrorType.OUT_OF_BOUNDS.value == "out_of_bounds"
    assert SandboxErrorType.AMBIGUOUS_TARGET.value == "ambiguous_target"


def test_bounding_box_center():
    bbox = BoundingBox(x=100, y=200, width=300, height=400)
    cx, cy = bbox.center()
    assert cx == 250  # 100 + 300//2
    assert cy == 400  # 200 + 400//2


def test_action_step():
    step = ActionStep(
        step_number=1,
        action_type=ActionType.TAP,
        params={"x": 540, "y": 1200},
        description="Tap spin button",
        expected_outcome="Spin starts",
    )
    assert step.action_type == ActionType.TAP
    assert step.params["x"] == 540


def test_action_plan():
    plan = ActionPlan(
        plan_id="test-123",
        goal="spin",
        steps=[],
        confidence=0.9,
        reasoning="Test plan",
    )
    assert plan.plan_id == "test-123"
    assert plan.confidence == 0.9


def test_action_plan_to_actions():
    plan = ActionPlan(
        plan_id="test-123",
        goal="spin",
        steps=[
            ActionStep(step_number=1, action_type=ActionType.TAP, params={"x": 540, "y": 1200}, description="tap"),
            ActionStep(step_number=2, action_type=ActionType.WAIT, params={"duration_ms": 2000}, description="wait"),
        ],
    )
    actions = plan.to_actions()
    assert len(actions) == 2
    assert actions[0]["action_type"] == "tap"
    assert actions[1]["action_type"] == "wait"


def test_analysis_result():
    result = AnalysisResult(
        screenshot_hash="abc123",
        timestamp=None,
        balance=5000.0,
        spin_button_visible=True,
        free_spins_count=5,
        confidence=0.95,
    )
    assert result.balance == 5000.0
    assert result.spin_button_visible is True
    assert result.free_spins_count == 5


def test_pipeline_config_defaults():
    config = PipelineConfig()
    assert config.vision_model == "qwen2.5-vl-3b"
    assert config.llm_model == "qwen3.5-27b"
    assert config.max_retries == 3
    assert config.sandbox_enabled is True


def test_ui_element_result():
    el = UIElementResult(
        element_type="button",
        label="Spin",
        bounds=BoundingBox(x=0, y=2000, width=200, height=100),
        is_actionable=True,
        confidence=0.9,
    )
    assert el.element_type == "button"
    assert el.is_actionable is True
