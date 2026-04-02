# MODULE-01-foundation.md — Core Foundation

> **Module ID:** 01  
> **Depends on:** None (all modules depend on this)  
> **Reference Influence:** Core patterns from all 4 reference projects

---

## Module Overview

MODULE-01 defines the foundational building blocks for CrawlForge v3:
- **Dataclasses** for all domain models (games, sessions, spins, checkpoints)
- **Custom exceptions** with structured error context
- **Base interfaces** (protocols/ABCs) for all module contracts

This module has zero external dependencies and is the single source of truth for core data structures.

---

## Dependencies

| Module | Dependency Type | Reason |
|---|---|---|
| ALL | **Hard** | Every module imports from foundation |

This module must be implemented first. No other module should have dependencies on anything outside the standard library before this is complete.

---

## API Design

### 1. Core Enums

```python
class GameType(Enum):
    SLOT = "slot"
    CARD_GAME = "card_game"          # 棋牌类
    TABLE_GAME = "table_game"
    LIVE_CASINO = "live_casino"

class RuntimeType(Enum):
    ADB_UIAUTOMATOR2 = "adb_uiautomator2"
    PLAYWRIGHT = "playwright"
    OPENCV_VISUAL = "opencv_visual"

class SpinState(Enum):
    IDLE = "idle"
    SPINNING = "spinning"
    FREE_SPIN = "free_spin"
    BONUS_ROUND = "bonus_round"
    BIG_WIN = "big_win"

class SessionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
```

### 2. Dataclasses

#### Game Definition
```python
@dataclass
class GameDefinition:
    id: str                          # unique game identifier
    name: str                        # display name
    provider: str                    # e.g., "pragmatic_play", "pg_soft"
    game_type: GameType
    runtime: RuntimeType
    templates: GameTemplates         # paths to template images
    reel_config: ReelConfig
    activity_selectors: dict[str, str]  # CSS/XPath selectors for activity elements
    metadata: dict                   # arbitrary provider-specific data

@dataclass
class GameTemplates:
    spin_button: str | None = None
    balance_display: str | None = None
    free_spin_indicator: str | None = None
    bonus_trigger: str | None = None

@dataclass
class ReelConfig:
    rows: int = 5
    cols: int = 3
    paylines: int = 9
    rtp_expected: float = 0.96
```

#### Session
```python
@dataclass
class GameSession:
    id: str                          # UUID
    game_id: str
    started_at: datetime
    ended_at: datetime | None = None
    status: SessionStatus = SessionStatus.PENDING
    initial_balance: float
    current_balance: float
    total_spins: int = 0
    total_wins: float = 0.0
    checkpoint_path: str | None = None
```

#### Spin Record
```python
@dataclass
class SpinResult:
    session_id: str
    spin_number: int
    timestamp: datetime
    bet_amount: float
    balance_before: float
    balance_after: float
    net_win: float
    state: SpinState
    reel_stops: list[list[int]] | None = None   # symbol indices per reel
    payline_hits: list[dict] | None = None
    bonus_triggered: bool = False
    free_spins_remaining: int = 0
    raw_screenshot: str | None = None            # path to screenshot
```

#### Activity / Competitor Info
```python
@dataclass
class CompetitorActivity:
    source_game_id: str
    activity_type: str              # "promo_banner", "bonus_round", "deposit_bonus"
    title: str
    description: str
    extracted_at: datetime
    raw_text: str
    confidence: float               # 0.0 - 1.0
    screenshot_path: str | None = None
```

#### Checkpoint
```python
@dataclass
class Checkpoint:
    session_id: str
    checkpoint_id: str              # UUID
    created_at: datetime
    session_state: GameSession
    recent_spins: list[SpinResult]   # last N spins for recovery
    runtime_state: dict             # opaque runtime-specific state (JSON)
    screenshot_path: str | None = None
```

### 3. Exceptions

```python
class CrawlForgeError(Exception):
    """Base exception for all CrawlForge errors."""
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}

class GameNotFoundError(CrawlForgeError):
    """Raised when a game ID is not found in the registry."""

class RuntimeConnectionError(CrawlForgeError):
    """Raised when runtime (ADB/Playwright) connection fails."""

class TemplateMatchError(CrawlForgeError):
    """Raised when template matching fails after all fallbacks."""

class CheckpointError(CrawlForgeError):
    """Raised when checkpoint save/load fails."""

class InsufficientBalanceError(CrawlForgeError):
    """Raised when game balance is too low to continue."""

class EvolutionError(CrawlForgeError):
    """Raised when genetic evolution encounters a fatal error."""

class DataCollectionError(CrawlForgeError):
    """Raised when data collection encounters an error."""

class SchedulerError(CrawlForgeError):
    """Raised when scheduler encounters an error."""
```

### 4. Interfaces (Protocols)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Runtime(Protocol):
    """Abstract runtime that can execute game actions."""
    
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def take_screenshot(self) -> bytes: ...
    def tap(self, x: int, y: int) -> None: ...
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None: ...
    def get_orientation(self) -> str: ...  # "portrait" | "landscape"
    def is_app_open(self, package_name: str) -> bool: ...
    def execute_js(self, script: str) -> Any: ...  # Playwright only

@runtime_checkable
class TemplateMatcher(Protocol):
    """Abstract template matcher."""
    
    def match(self, screenshot: bytes, template_path: str, threshold: float) -> list[MatchResult]: ...
    def calibrate(self, reference_screenshot: bytes, template_path: str) -> float: ...

@runtime_checkable
class CheckpointManager(Protocol):
    """Abstract checkpoint saver/restorer."""
    
    def save(self, checkpoint: Checkpoint) -> str: ...   # returns path
    def load(self, checkpoint_path: str) -> Checkpoint: ...
    def list_checkpoints(self, session_id: str) -> list[Checkpoint]: ...
    def delete_old(self, session_id: str, keep_last: int = 5) -> None: ...

@runtime_checkable
class EvolutionEngine(Protocol):
    """Abstract evolution engine."""
    
    def evaluate_population(self) -> list[float]: ...
    def select_parents(self) -> list[Genome]: ...
    def crossover(self, parent1: Genome, parent2: Genome) -> Genome: ...
    def mutate(self, genome: Genome) -> Genome: ...
```

### 5. Event Bus

```python
@dataclass
class CrawlForgeEvent:
    timestamp: datetime
    module: str
    event_type: str
    payload: dict
    trace_id: str | None = None

class EventBus:
    """Central event bus for all CrawlForge modules."""
    
    def emit(self, module: str, event_type: str, payload: dict) -> None:
        """Emit an event to all subscribers."""
    
    def subscribe(self, module: str, callback: Callable[[CrawlForgeEvent], None]) -> None:
        """Subscribe to events from a module."""
    
    def unsubscribe(self, module: str, callback: Callable) -> None:
        """Unsubscribe from events."""
```

---

## Data Structures

| Structure | Fields | Purpose |
|---|---|---|
| `GameDefinition` | id, name, provider, game_type, runtime, templates, reel_config | Game registry entry |
| `GameSession` | id, game_id, status, balances, spin counts | Session lifecycle |
| `SpinResult` | spin_number, bet, balance delta, reel_stops, state | Per-spin record |
| `CompetitorActivity` | source, type, title, description, confidence | Activity extraction |
| `Checkpoint` | session_id, checkpoint_id, session_state, recent_spins, runtime_state | Recovery point |
| `GameTemplates` | spin_button, balance, free_spin, bonus paths | Visual templates |
| `ReelConfig` | rows, cols, paylines, rtp_expected | Slot math config |
| `CrawlForgeEvent` | timestamp, module, event_type, payload, trace_id | Observability |

---

## Implementation Steps

### Step 1: Enums & Dataclasses (Day 1 - 30 min)
```bash
# Create directory
mkdir -p src/crawlforge/foundation

# Write models.py with all dataclasses
# Write exceptions.py with all custom exceptions
```

### Step 2: Interfaces (Day 1 - 30 min)
```bash
# Write interfaces.py with all Protocol classes
# Verify runtime_checkable works with implementations
```

### Step 3: Event Bus (Day 1 - 30 min)
```bash
# Write events.py
# Implement synchronous in-process pub/sub
# Add trace_id propagation
```

### Step 4: Validation Helpers (Day 1 - 30 min)
```bash
# Write validators.py
# Add @dataclass validation decorators
# Ensure all enums have string serialization
```

### Step 5: Export Module (Day 1 - 30 min)
```bash
# Write __init__.py
# Export all public types
# Type checking with mypy
```

---

## Testing Strategy

| Test | What | Method |
|---|---|---|
| `test_dataclass_serialization` | All dataclasses round-trip through JSON | pytest |
| `test_exception_context` | Exceptions carry proper context | pytest |
| `test_protocol_runtime_checkable` | Protocols correctly identify implementers | pytest |
| `test_event_bus_subscription` | Subscribe/unsubscribe works correctly | pytest |
| `test_enum_serialization` | All enums serialize to string | pytest |
| `test_validator_rejects_invalid` | Validator rejects bad data | pytest |

---

## Success Criteria

1. ✅ All dataclasses importable from `crawlforge.foundation`
2. ✅ All exceptions have structured `context` dict
3. ✅ All protocols have runtime_checkable=True
4. ✅ EventBus supports multiple subscribers per module
5. ✅ All enums have `.value` string serialization
6. ✅ No external dependencies (pure stdlib)
7. ✅ 100% unit test coverage on foundation module
8. ✅ Type hints pass mypy strict mode
