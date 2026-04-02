# MODULE-04-react-loop.md — ReAct Execution Loop

> **Module ID:** 04  
> **Depends on:** MODULE-01 (foundation), MODULE-03 (ai-pipeline)  
> **Reference Influence:** Autono's ReAct loop + @ability decorator + MCP protocol

---

## Module Overview

MODULE-04 implements the **ReAct loop** (Reasoning + Acting) — the core execution engine that continuously:
1. **OBSERVE** — Capture game state via screenshot
2. **THINK** — Run the AI pipeline to generate an action plan
3. **ACT** — Execute the planned action via the runtime
4. **REFLECT** — Evaluate the result and decide next step

This module is directly inspired by Autono's `@ability` decorator pattern and MCP protocol, exposing game interaction abilities as tools that can be called by external agents.

---

## Dependencies

| Module | Dependency Type | Reason |
|---|---|---|
| MODULE-01 | **Hard** | Imports dataclasses, exceptions, enums, interfaces |
| MODULE-03 | **Hard** | Uses AIPipeline for plan generation |

### External Dependencies
```txt
# For structured async loop control
asyncio>=3.4.3

# For MCP protocol (Model Context Protocol)
mcp>=0.1.0  # or custom implementation

# Pydantic for ability schema validation
pydantic>=2.0.0
```

---

## API Design

### ReAct Loop Core

```python
class ReActLoop:
    """ReAct loop: Observe → Think → Act → Reflect."""
    
    def __init__(
        self,
        game: GameDefinition,
        runtime: Runtime,
        pipeline: AIPipeline,
        event_bus: EventBus,
        checkpoint_manager: CheckpointManager | None = None,
        config: ReActConfig | None = None
    ):
        self._game = game
        self._runtime = runtime
        self._pipeline = pipeline
        self._event_bus = event_bus
        self._checkpoint = checkpoint_manager
        self._config = config or ReActConfig()
        self._history: list[ReActStep] = []
        self._is_running = False
    
    def run(self, goal: str, max_iterations: int = 50) -> LoopResult:
        """Run the ReAct loop until goal is met or max_iterations reached."""
    
    def step(self) -> ReActStep:
        """Execute a single OBSERVE→THINK→ACT→REFLECT cycle."""
    
    def observe(self) -> ObservationResult:
        """Capture screenshot and analyze game state."""
    
    def think(self, observation: ObservationResult, goal: str) -> ActionPlan:
        """Generate action plan from observation."""
    
    def act(self, plan: ActionPlan) -> ExecutionResult:
        """Execute the action plan via runtime."""
    
    def reflect(self, execution: ExecutionResult) -> ReflectionResult:
        """Evaluate execution result and decide if loop should continue."""
    
    def stop(self) -> None:
        """Gracefully stop the loop."""
    
    @property
    def history(self) -> list[ReActStep]:
        """Return full execution history."""
```

### ReAct Step

```python
@dataclass
class ReActStep:
    """One complete cycle of the ReAct loop."""
    step_number: int
    timestamp: datetime
    observation: ObservationResult
    plan: ActionPlan
    execution: ExecutionResult
    reflection: ReflectionResult
    duration_ms: int

@dataclass
class ObservationResult:
    """Result of the OBSERVE phase."""
    screenshot: bytes
    screenshot_hash: str
    analysis: AnalysisResult           # from MODULE-03
    raw_pixels: np.ndarray | None = None  # for OpenCV processing

@dataclass
class ExecutionResult:
    """Result of executing an action plan."""
    plan_id: str
    executed_steps: list[ExecutedStep]
    final_screenshot: bytes
    balance_after: float | None
    state_changed: bool               # True if game state changed after action
    runtime_errors: list[str]

@dataclass
class ReflectionResult:
    """Result of the REFLECT phase."""
    should_continue: bool
    goal_progress: float              # 0.0 - 1.0
    reasons: list[str]
    suggested_next_action: str | None
    loop_should_stop: bool            # True if terminal state reached
```

### @ability Decorator (from Autono)

```python
from functools import wraps
from typing import Callable, Any

class AbilityRegistry:
    """Registry of all exposed abilities (tools) for external agents."""
    
    def __init__(self):
        self._abilities: dict[str, Ability] = {}
    
    def register(self, ability: Ability) -> None:
        """Register an ability."""
    
    def get(self, name: str) -> Ability | None: ...
    
    def list_abilities(self) -> list[Ability]: ...
    
    def call(self, name: str, params: dict) -> Any:
        """Call an ability by name with params."""
    
    def emit_call_event(self, ability_name: str, params: dict, result: Any) -> None:
        """Emit ability call event to event bus."""

@dataclass
class Ability:
    name: str
    description: str
    parameters: dict                   # JSON Schema for parameters
    returns: dict                      # JSON Schema for return value
    handler: Callable[..., Any]
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)

def ability(
    name: str,
    description: str,
    parameters: dict,
    returns: dict,
    tags: list[str] | None = None
):
    """Decorator to expose a method as an MCP ability."""
    def decorator(func: Callable) -> Callable:
        func._ability_metadata = Ability(
            name=name,
            description=description,
            parameters=parameters,
            returns=returns,
            handler=func,
            tags=tags or []
        )
        return func
    return decorator
```

### Built-in Abilities (Exposed via MCP)

```python
class GameAbilities:
    """Built-in abilities for game interaction."""
    
    @staticmethod
    @ability(
        name="spin",
        description="Spin the slot game reel",
        parameters={
            "type": "object",
            "properties": {
                "bet_amount": {"type": "number", "description": "Bet amount for this spin"}
            },
            "required": []
        },
        returns={"type": "object"},
        tags=["game_action", "slot"]
    )
    def spin(runtime: Runtime, bet_amount: float | None = None) -> SpinResult:
        """Execute a single spin."""
    
    @staticmethod
    @ability(
        name="collect_bonus",
        description="Collect a bonus round or promo reward",
        parameters={"type": "object", "properties": {}, "required": []},
        returns={"type": "object"},
        tags=["game_action", "bonus"]
    )
    def collect_bonus(runtime: Runtime) -> bool:
        """Tap to collect active bonus."""
    
    @staticmethod
    @ability(
        name="set_bet",
        description="Set the bet amount for subsequent spins",
        parameters={
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Bet amount"},
                "lines": {"type": "integer", "description": "Number of lines"}
            },
            "required": ["amount"]
        },
        returns={"type": "object"},
        tags=["game_action", "bet"]
    )
    def set_bet(runtime: Runtime, amount: float, lines: int = 9) -> bool:
        """Set bet level."""
    
    @staticmethod
    @ability(
        name="get_game_state",
        description="Get current game state including balance and spin count",
        parameters={"type": "object", "properties": {}, "required": []},
        returns={"type": "object"},
        tags=["game_state", "observation"]
    )
    def get_game_state(runtime: Runtime, game: GameDefinition) -> GameState:
        """Query current game state."""
```

### MCP Protocol Handler

```python
class MCPProtocolHandler:
    """Handles Model Context Protocol requests from external agents."""
    
    def __init__(self, ability_registry: AbilityRegistry, event_bus: EventBus):
        self._registry = ability_registry
        self._event_bus = event_bus
    
    def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Process an MCP request and return response."""
    
    def list_tools(self) -> list[dict]:
        """Return all abilities as MCP tool definitions."""
    
    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call an ability by name with arguments."""
    
    # MCP JSON-RPC style methods
    def tools_list(self) -> dict: ...
    def tools_call(self, name: str, arguments: dict) -> dict: ...
```

### Config

```python
@dataclass
class ReActConfig:
    """Configuration for the ReAct loop."""
    max_iterations: int = 50
    iteration_timeout_ms: int = 30000
    observe_interval_ms: int = 500        # delay between observe cycles
    reflection_threshold: float = 0.8     # confidence threshold for goal completion
    checkpoint_interval: int = 5          # save checkpoint every N iterations
    enable_mcp: bool = True               # expose abilities via MCP
    mcp_port: int = 8766                  # MCP server port
    sandbox_actions: bool = True         # validate via sandbox before acting
```

---

## Data Structures

| Structure | Fields | Purpose |
|---|---|---|
| `ReActStep` | step_number, timestamp, observation, plan, execution, reflection, duration | Single loop cycle record |
| `ObservationResult` | screenshot, hash, analysis, raw_pixels | OBSERVE phase output |
| `ExecutionResult` | plan_id, executed_steps, final_screenshot, balance, state_changed, errors | ACT phase output |
| `ReflectionResult` | should_continue, goal_progress, reasons, suggested_next, stop | REFLECT phase output |
| `Ability` | name, description, parameters, returns, handler, version, tags | Exposed tool metadata |
| `MCPRequest` | method, params, id | MCP JSON-RPC request |
| `MCPResponse` | result, error, id | MCP JSON-RPC response |
| `ReActConfig` | max_iterations, timeouts, checkpoint interval, MCP port | Loop configuration |

---

## Implementation Steps

### Step 1: ReActConfig + ReActStep Dataclasses (Day 1 - 30 min)
```bash
mkdir -p src/crawlforge/react_loop

# Write config.py
# Define all ReAct-related dataclasses
```

### Step 2: ReAct Loop Core (Day 1 - 2 hrs)
```python
# Write loop.py
# Implement ReActLoop class with OBSERVE → THINK → ACT → REFLECT
# Add history tracking
# Add graceful stop() method
# Add max_iteration guard
```

### Step 3: @ability Decorator + Registry (Day 2 - 2 hrs)
```python
# Write abilities.py
# Implement @ability decorator (inspired by Autono)
# Implement AbilityRegistry
# Register built-in abilities (spin, collect_bonus, set_bet, get_game_state)
# Add event emission on each ability call
```

### Step 4: MCP Protocol Handler (Day 2 - 2 hrs)
```python
# Write mcp_protocol.py
# Implement MCPProtocolHandler
# Support tools_list and tools_call methods
# JSON-RPC style request/response
# Connect to ability registry
```

### Step 5: Integration with AIPipeline (Day 3 - 1 hr)
```python
# ReActLoop.think() calls AIPipeline.run()
# Pass ObservationResult as PipelineContext
# Handle pipeline failures gracefully
```

### Step 6: Checkpoint Integration (Day 3 - 1 hr)
```python
# ReActLoop calls CheckpointManager every N iterations (checkpoint_interval)
# On crash recovery: ReActLoop can resume from checkpoint
# Save history + current game state
```

### Step 7: MCP Server Startup (Day 3 - 1 hr)
```python
# Add start_mcp_server() method
# Run MCP JSON-RPC server on configured port
# Accept external agent connections
# Emit events for all tool calls
```

---

## Testing Strategy

| Test | What | Method |
|---|---|---|
| `test_loop_single_step` | One complete OBSERVE→THINK→ACT→REFLECT cycle | Mock runtime + pipeline |
| `test_loop_stops_at_max_iterations` | Loop respects max_iterations | Mock |
| `test_loop_stops_on_goal_completion` | Loop stops when reflection says to stop | Mock |
| `test_ability_registry_registers_and_calls` | Abilities registered and callable | Unit test |
| `test_ability_decorator_metadata` | @ability attaches correct metadata | Unit test |
| `test_mcp_tools_list` | MCP returns correct tool definitions | Mock MCP client |
| `test_mcp_tools_call` | MCP calls ability and returns result | Mock |
| `test_loop_fires_events` | Events fired at each phase | Mock EventBus |

---

## Success Criteria

1. ✅ `ReActLoop.run(goal, max_iterations)` completes without raising
2. ✅ Each iteration completes within `iteration_timeout_ms`
3. ✅ Loop stops when `ReflectionResult.loop_should_stop = True`
4. ✅ `ReActLoop.history` returns all `ReActStep` records in order
5. ✅ All built-in abilities (`spin`, `collect_bonus`, `set_bet`, `get_game_state`) are registered
6. ✅ `@ability` decorator correctly attaches `Ability` metadata
7. ✅ MCP protocol handler returns valid JSON-RPC responses
8. ✅ Checkpoint saved every `checkpoint_interval` iterations
9. ✅ Loop gracefully handles pipeline failures without crashing
10. ✅ All loop phases emit events to EventBus
