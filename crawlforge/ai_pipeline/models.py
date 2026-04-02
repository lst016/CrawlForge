"""
AI Pipeline data models.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Literal
from enum import Enum
from datetime import datetime


class ActionType(Enum):
    """Action step types."""
    TAP = "tap"
    SWIPE = "swipe"
    WAIT = "wait"
    COMPARE_SCREENSHOT = "compare_screenshot"
    WAIT_FOR_CHANGE = "wait_for_change"
    COLLECT_BONUS = "collect_bonus"
    SET_BET = "set_bet"
    INPUT_TEXT = "input_text"
    PRESS_KEY = "press_key"


class SandboxErrorType(Enum):
    """Sandbox validation error types."""
    OUT_OF_BOUNDS = "out_of_bounds"
    AMBIGUOUS_TARGET = "ambiguous_target"
    IMPOSSIBLE_SEQUENCE = "impossible_sequence"
    MISSING_ELEMENT = "missing_element"


class PipelineStage(Enum):
    """Pipeline execution stages."""
    ANALYZE = "analyze"
    GENERATE = "generate"
    SANDBOX = "sandbox"
    TEST = "test"


@dataclass
class BoundingBox:
    """Bounding box for UI element."""
    x: int
    y: int
    width: int
    height: int

    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class PipelineConfig:
    """Configuration for the AI pipeline."""
    vision_model: str = "qwen2.5-vl-3b"
    llm_model: str = "qwen3.5-27b"
    max_retries: int = 3
    sandbox_enabled: bool = True
    confidence_threshold: float = 0.7


@dataclass
class PipelineContext:
    """Context for a pipeline run."""
    goal: str
    screenshot: bytes
    game_name: str = "unknown"
    metadata: dict = field(default_factory=dict)


@dataclass
class UIElementResult:
    """Detected UI element from vision analysis."""
    element_type: str  # button, text, image, icon
    label: str
    bounds: BoundingBox
    is_actionable: bool = False
    confidence: float = 0.0
    resource_id: str = ""


@dataclass
class AnalysisResult:
    """Vision model output for a game screenshot."""
    screenshot_hash: str
    timestamp: datetime
    detected_elements: list[UIElementResult] = field(default_factory=list)
    balance: Optional[float] = None
    bet_level: Optional[int] = None
    spin_button_visible: bool = False
    free_spins_count: int = 0
    bonus_round_active: bool = False
    minigame_active: bool = False
    confidence: float = 0.0
    raw_vision_output: str = ""
    suggestions: list[str] = field(default_factory=list)

    @property
    def game_state_dict(self) -> dict:
        return {
            "balance": self.balance,
            "bet_level": self.bet_level,
            "spin_button_visible": self.spin_button_visible,
            "free_spins_count": self.free_spins_count,
            "bonus_round_active": self.bonus_round_active,
            "minigame_active": self.minigame_active,
        }


@dataclass
class ActionStep:
    """A single step in an action plan."""
    step_number: int
    action_type: ActionType
    params: dict  # {"x": 540, "y": 1200} for tap
    description: str
    expected_outcome: str = ""


@dataclass
class ActionPlan:
    """LLM-generated plan for game interaction."""
    plan_id: str
    goal: str
    steps: list[ActionStep] = field(default_factory=list)
    estimated_duration_ms: int = 0
    confidence: float = 0.0
    reasoning: str = ""

    def to_actions(self) -> list[dict]:
        """Convert plan steps to runtime action dicts."""
        return [
            {
                "action_type": s.action_type.value,
                **{k: v for k, v in s.params.items()}
            }
            for s in self.steps
        ]


@dataclass
class SandboxError:
    """Sandbox validation error."""
    step_number: int
    error_type: SandboxErrorType
    message: str


@dataclass
class ValidatedStep:
    """Result of validating a single step."""
    step: ActionStep
    status: Literal["valid", "warning", "error"] = "valid"
    reason: Optional[str] = None


@dataclass
class SandboxResult:
    """Sandbox dry-run validation result."""
    is_valid: bool
    validated_steps: list[ValidatedStep] = field(default_factory=list)
    errors: list[SandboxError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExecutedStep:
    """Result of executing a single step."""
    step: ActionStep
    status: Literal["success", "failed", "skipped"] = "success"
    screenshot: Optional[bytes] = None
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class TestResult:
    """Result of executing an action plan."""
    plan_id: str
    executed_steps: list[ExecutedStep] = field(default_factory=list)
    success: bool = False
    final_screenshot: Optional[bytes] = None
    unexpected_states: list[str] = field(default_factory=list)
    retry_recommended: bool = False
