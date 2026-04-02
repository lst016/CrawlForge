"""
ReAct Loop data models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

from ..ai_pipeline import AnalysisResult, ActionPlan, ExecutedStep


@dataclass
class ReActConfig:
    """Configuration for ReAct loop."""
    max_iterations: int = 50
    step_delay_ms: int = 500
    confidence_threshold: float = 0.7
    stop_on_error: bool = True


@dataclass
class ReActState:
    """Current state of the ReAct loop."""
    goal: str
    current_plan: Optional[ActionPlan] = None
    last_execution: Optional["ExecutionResult"] = None
    last_reflection: Optional["ReflectionResult"] = None
    iteration: int = 0


@dataclass
class ObservationResult:
    """Result of the OBSERVE phase."""
    screenshot: bytes
    screenshot_hash: str
    analysis: AnalysisResult
    raw_pixels: Any = None  # np.ndarray for OpenCV processing


@dataclass
class ExecutionResult:
    """Result of executing an action plan."""
    plan_id: str
    executed_steps: list[ExecutedStep] = field(default_factory=list)
    final_screenshot: Optional[bytes] = None
    balance_after: Optional[float] = None
    state_changed: bool = False
    runtime_errors: list[str] = field(default_factory=list)


@dataclass
class ReflectionResult:
    """Result of the REFLECT phase."""
    should_continue: bool = True
    goal_progress: float = 0.0
    reasons: list[str] = field(default_factory=list)
    suggested_next_action: Optional[str] = None
    loop_should_stop: bool = False


@dataclass
class ReActStep:
    """One complete cycle of the ReAct loop."""
    step_number: int
    timestamp: datetime
    observation: ObservationResult
    plan: ActionPlan
    execution: ExecutionResult
    reflection: ReflectionResult
    duration_ms: float = 0.0


@dataclass
class LoopResult:
    """Result of a complete ReAct loop run."""
    goal: str
    total_iterations: int
    history: list[ReActStep] = field(default_factory=list)
    final_state: Optional[ReActState] = None
    total_duration_ms: float = 0.0
    success: bool = False


@dataclass
class Ability:
    """An MCP-exposed ability/tool."""
    name: str
    description: str
    parameters: dict  # JSON Schema
    returns: dict    # JSON Schema
    handler: Any
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)


class AbilityRegistry:
    """Registry of all exposed abilities (MCP tools)."""

    def __init__(self):
        self._abilities: dict[str, Ability] = {}

    def register(self, ability: Ability) -> None:
        """Register an ability."""
        self._abilities[ability.name] = ability

    def get(self, name: str) -> Optional[Ability]:
        """Get ability by name."""
        return self._abilities.get(name)

    def list_abilities(self) -> list[Ability]:
        """List all abilities."""
        return list(self._abilities.values())

    def call(self, name: str, params: dict, handler_context: Any = None) -> Any:
        """Call an ability by name."""
        ability = self._abilities.get(name)
        if ability is None:
            raise ValueError(f"Unknown ability: {name}")
        return ability.handler(handler_context, **params)

    def emit_call_event(self, ability_name: str, params: dict, result: Any) -> None:
        """Emit ability call event."""
        # No-op by default; connected to EventBus in full implementation
        pass


def ability(
    name: str,
    description: str,
    parameters: dict,
    returns: dict,
    tags: list[str] = None,
):
    """Decorator to expose a method as an MCP ability."""
    def decorator(func):
        func._ability_metadata = Ability(
            name=name,
            description=description,
            parameters=parameters,
            returns=returns,
            handler=func,
            tags=tags or [],
        )
        return func
    return decorator
