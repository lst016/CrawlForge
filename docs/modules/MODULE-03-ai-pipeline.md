# MODULE-03-ai-pipeline.md — AI Generation Pipeline

> **Module ID:** 03  
> **Depends on:** MODULE-01 (foundation), MODULE-02 (runtime)  
> **Reference Influence:** PantheonOS AI pipeline + Autono's structured tool generation

---

## Module Overview

The AI Pipeline transforms a **game screenshot** into an **executable action plan** through a 4-stage pipeline:

```
Analyze → Generate → Sandbox → Test
```

1. **Analyze** — Vision model reads the screenshot, extracts UI state, identifies actionable elements
2. **Generate** — LLM generates a structured action plan (sequence of taps/swipes)
3. **Sandbox** — Action plan is dry-run in a simulated environment to check for obvious errors
4. **Test** — The action is executed against the actual runtime, with result verification

This module powers MODULE-04's ReAct loop (Observation → Thought → Action) and MODULE-06's evolution engine.

---

## Dependencies

| Module | Dependency Type | Reason |
|---|---|---|
| MODULE-01 | **Hard** | Imports dataclasses, exceptions |
| MODULE-02 | **Hard** | Uses Runtime for screenshot capture |

### External Dependencies
```txt
# LLM API client (configurable: OpenAI, Anthropic, local)
openai>=1.0.0
# or anthropic>=0.20.0

# Local MLX support (optional)
mlx>=0.0.9

# AI Router (airouter) for multi-model routing
# Configured via TOOLS.md: http://localhost:18888

# Pydantic for structured output validation
pydantic>=2.0.0
```

---

## API Design

### AIPipeline

```python
class AIPipeline:
    """4-stage AI pipeline for game automation."""
    
    def __init__(
        self, 
        config: PipelineConfig,
        runtime: Runtime,
        event_bus: EventBus,
        vision_model: str = "qwen2.5-vl-3b",  # local MLX
        llm_model: str = "qwen3.5-27b"          # local MLX
    ):
        self._config = config
        self._runtime = runtime
        self._event_bus = event_bus
        self._vision_model = vision_model
        self._llm_model = llm_model
        self._router = AIRouter()  # from airouter client
    
    def run(self, context: PipelineContext) -> ActionPlan:
        """Run full pipeline: Analyze → Generate → Sandbox → Test."""
    
    def analyze(self, screenshot: bytes, prompt: str | None = None) -> AnalysisResult:
        """Stage 1: Vision analysis of screenshot."""
    
    def generate(self, analysis: AnalysisResult, goal: str) -> ActionPlan:
        """Stage 2: LLM generates action plan from analysis."""
    
    def sandbox(self, plan: ActionPlan) -> SandboxResult:
        """Stage 3: Dry-run validation in sandbox."""
    
    def test(self, plan: ActionPlan) -> TestResult:
        """Stage 4: Execute plan and verify result."""
```

### Stage 1: Analysis (Analyze)

```python
@dataclass
class AnalysisResult:
    """Vision model output for a game screenshot."""
    screenshot_hash: str              # SHA256 of input screenshot
    timestamp: datetime
    detected_elements: list[UIElement]
    game_state: GameState
    confidence: float                 # overall confidence 0.0-1.0
    raw_vision_output: str            # raw model text output
    suggestions: list[str]            # AI-suggested actions

@dataclass
class UIElement:
    element_type: str                 # "button", "text", "image", "icon"
    label: str
    bounds: BoundingBox               # x, y, width, height
    is_actionable: bool
    confidence: float

@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

@dataclass  
class GameState:
    balance: float | None = None
    bet_level: int | None = None
    spin_button_visible: bool = False
    free_spins_count: int = 0
    bonus_round_active: bool = False
    minigame_active: bool = False
```

### Stage 2: Generation (Generate)

```python
@dataclass
class ActionPlan:
    """LLM-generated plan for game interaction."""
    plan_id: str                      # UUID
    goal: str                         # e.g., "collect bonus and spin"
    steps: list[ActionStep]
    estimated_duration_ms: int
    confidence: float
    reasoning: str                    # LLM's explanation of the plan

@dataclass
class ActionStep:
    step_number: int
    action_type: ActionType
    params: dict                      # e.g., {"x": 540, "y": 1200} for tap
    description: str                  # human-readable description
    expected_outcome: str             # what should happen after this step

class ActionType(Enum):
    TAP = "tap"
    SWIPE = "swipe"
    WAIT = "wait"
    COMPARE_SCREENSHOT = "compare_screenshot"
    WAIT_FOR_CHANGE = "wait_for_change"
    COLLECT_BONUS = "collect_bonus"
    SET_BET = "set_bet"
```

### Stage 3: Sandbox (Sandbox)

```python
@dataclass
class SandboxResult:
    """Sandbox dry-run validation result."""
    is_valid: bool
    validated_steps: list[ValidatedStep]
    errors: list[SandboxError]
    warnings: list[str]

@dataclass
class ValidatedStep:
    step: ActionStep
    status: Literal["valid", "warning", "error"]
    reason: str | None = None

@dataclass
class SandboxError:
    step_number: int
    error_type: SandboxErrorType
    message: str

class SandboxErrorType(Enum):
    OUT_OF_BOUNDS = "out_of_bounds"       # tap coordinates outside screen
    AMBIGUOUS_TARGET = "ambiguous_target" # multiple matching elements
    IMPOSSIBLE_SEQUENCE = "impossible_sequence"  # e.g., swipe before tap
    MISSING_ELEMENT = "missing_element"   # referenced element not in sandbox
```

### Stage 4: Test (Test)

```python
@dataclass
class TestResult:
    """Result of executing an action plan against the real runtime."""
    plan_id: str
    executed_steps: list[ExecutedStep]
    success: bool
    final_screenshot: bytes | None
    unexpected_states: list[str]
    retry_recommended: bool

@dataclass
class ExecutedStep:
    step: ActionStep
    status: Literal["success", "failed", "skipped"]
    screenshot: bytes | None = None
    error: str | None = None
    duration_ms: int = 0
```

### Pipeline Context

```python
@dataclass
class PipelineConfig:
    """Configuration for the AI pipeline."""
    vision_model: str = "qwen2.5-vl-3b"
    llm_model: str = "qwen3.5-27b"
    max_retries: int = 3
    sandbox_enabled: bool = True
    test_timeout_ms: int = 30000
    vision_temperature: float = 0.1
    llm_temperature: float = 0.2

@dataclass
class PipelineContext:
    """Context passed into the pipeline for a single run."""
    game: GameDefinition
    goal: str                         # e.g., "spin 10 times", "collect bonus"
    previous_screenshot: bytes | None = None
    session_history: list[SpinResult] | None = None
    user_prompt: str | None = None    # additional natural language instruction
```

---

## Data Structures

| Structure | Fields | Purpose |
|---|---|---|
| `AnalysisResult` | elements, game_state, confidence, raw_output | Vision analysis output |
| `UIElement` | type, label, bounds, actionable, confidence | Detected UI element |
| `GameState` | balance, bet, spin visible, free spins, bonus | Parsed game state |
| `ActionPlan` | plan_id, goal, steps, duration, confidence | LLM-generated plan |
| `ActionStep` | step_number, action_type, params, description | Single step in plan |
| `SandboxResult` | is_valid, validated_steps, errors, warnings | Sandbox validation |
| `SandboxError` | step_number, error_type, message | Sandbox error detail |
| `TestResult` | plan_id, executed_steps, success, final_screenshot | Execution result |
| `PipelineConfig` | model names, retry count, timeouts | Pipeline configuration |
| `PipelineContext` | game, goal, history, prompt | Pipeline input context |

---

## Implementation Steps

### Step 1: Config + Context (Day 1 - 1 hr)
```bash
mkdir -p src/crawlforge/ai_pipeline

# Write config.py and context.py
# Define all dataclasses for stages 1-4
# Implement PipelineConfig and PipelineContext
```

### Step 2: Vision Analyzer (Day 1 - 2 hrs)
```python
# Implement AIPipeline.analyze()
# Use qwen2.5-vl-3b via local MLX or airouter
# Prompt template for slot game UI parsing:
# "Analyze this screenshot. Identify: spin button, balance, 
#  bet level, free spin count, bonus indicators."
# Parse output into AnalysisResult dataclass
```

### Step 3: LLM Plan Generator (Day 2 - 2 hrs)
```python
# Implement AIPipeline.generate()
# Use qwen3.5-27b via local MLX or airouter
# System prompt: slot game action planning
# Output: structured JSON validated by Pydantic
# Convert to ActionPlan dataclass
```

### Step 4: Sandbox Validator (Day 2 - 2 hrs)
```python
# Implement AIPipeline.sandbox()
# Validate:
#   - All tap coordinates within screen bounds
#   - Wait steps have reasonable durations (100ms - 5000ms)
#   - No impossible sequences
#   - Referenced elements exist in previous_screenshot (optional)
# Return SandboxResult
```

### Step 5: Test Executor (Day 3 - 2 hrs)
```python
# Implement AIPipeline.test()
# Execute each step via runtime
# Capture screenshot after each step
# Compare final state with expected_outcome
# Return TestResult with retry recommendation
```

### Step 6: Full Pipeline Integration (Day 3 - 1 hr)
```python
# Implement AIPipeline.run()
# Chain: analyze → generate → sandbox → test
# On sandbox failure: regenerate with error context
# On test failure: retry up to max_retries
# Emit events at each stage
```

### Step 7: Error Handling + Recovery (Day 3 - 1 hr)
```python
# On vision failure: fallback to MODULE-07 template matching
# On LLM failure: use rule-based fallback plan
# On sandbox errors: refine plan with error feedback
# On test failure: recommend human review
```

---

## Testing Strategy

| Test | What | Method |
|---|---|---|
| `test_analyze_returns_valid_structure` | Analyze returns valid AnalysisResult | Mock vision model |
| `test_generate_returns_valid_plan` | Generate returns valid ActionPlan | Mock LLM |
| `test_sandbox_rejects_out_of_bounds` | Sandbox catches OOB coordinates | Unit test |
| `test_sandbox_accepts_valid_plan` | Sandbox passes a valid plan | Unit test |
| `test_pipeline_runs_full_stages` | Full pipeline executes all 4 stages | Integration test |
| `test_pipeline_retries_on_failure` | Pipeline retries on test failure | Mock runtime |
| `test_pipeline_fires_events` | Events fired at each stage | Mock EventBus |

---

## Success Criteria

1. ✅ `AIPipeline.analyze()` returns `AnalysisResult` with `detected_elements` and `game_state` within 3 seconds
2. ✅ `AIPipeline.generate()` returns `ActionPlan` with valid `ActionStep` sequences
3. ✅ `AIPipeline.sandbox()` catches out-of-bounds coordinates and impossible sequences
4. ✅ `AIPipeline.test()` executes plan and returns `TestResult` with per-step status
5. ✅ Full pipeline completes within 30 seconds end-to-end
6. ✅ Pipeline falls back to rule-based plan if LLM is unavailable
7. ✅ All stages emit events to EventBus
8. ✅ Retry logic activates on test failure (up to `max_retries`)
