# MODULE-05-checkpoint.md — Checkpoint & Recovery System

> **Module ID:** 05  
> **Depends on:** MODULE-01 (foundation)  
> **Reference Influence:** Hive's checkpoint recovery + WebSocket observability

---

## Module Overview

MODULE-05 implements **persistent checkpointing** for crash recovery and session resumption. Inspired by Hive:

- **Save checkpoints** after each spin cycle or every N ReAct iterations
- **WebSocket streaming** of checkpoint events to a live dashboard
- **Automatic recovery** on startup if a previous session was interrupted
- **Self-healing**: on crash, reconnect runtime and resume from last checkpoint

The checkpoint system stores session state (balance, spin count, runtime state) to disk as JSON + screenshots.

---

## Dependencies

| Module | Dependency Type | Reason |
|---|---|---|
| MODULE-01 | **Hard** | Imports dataclasses, exceptions, GameSession, Checkpoint |

### External Dependencies
```txt
# WebSocket server for event streaming
websockets>=12.0

# JSON serialization
orjson>=3.9.0  # faster than stdlib json

# Screenshot compression
Pillow>=10.0.0

# File locking for safe concurrent writes
filelock>=3.12.0
```

---

## API Design

### CheckpointManager

```python
class CheckpointManager:
    """Manages checkpoint save/load and WebSocket event streaming."""
    
    def __init__(
        self,
        checkpoint_dir: Path,
        event_bus: EventBus,
        config: CheckpointConfig | None = None
    ):
        self._dir = checkpoint_dir
        self._event_bus = event_bus
        self._config = config or CheckpointConfig()
        self._websocket_clients: set[WebSocketClient] = set()
        self._lock = FileLock(checkpoint_dir / ".checkpoint.lock")
    
    # ── Core Checkpoint Operations ──
    
    def save(self, checkpoint: Checkpoint) -> str:
        """Save a checkpoint. Returns checkpoint path. Thread-safe."""
    
    def load(self, checkpoint_path: str) -> Checkpoint:
        """Load a checkpoint from disk."""
    
    def load_latest(self, session_id: str) -> Checkpoint | None:
        """Load the most recent checkpoint for a session."""
    
    def list_checkpoints(self, session_id: str) -> list[CheckpointMetadata]:
        """List all checkpoints for a session (without loading full data)."""
    
    def delete(self, checkpoint_path: str) -> None:
        """Delete a specific checkpoint."""
    
    def delete_old(self, session_id: str, keep_last: int = 5) -> None:
        """Delete old checkpoints, keeping the N most recent."""
    
    # ── Auto-Recovery ──
    
    def get_recoverable_session(self) -> RecoveryInfo | None:
        """Check if there's an interrupted session that can be recovered."""
    
    def prepare_recovery(self, recovery_info: RecoveryInfo) -> Checkpoint:
        """Prepare runtime and load checkpoint for recovery."""
    
    # ── WebSocket Event Streaming ──
    
    async def start_websocket_server(self, host: str = "localhost", port: int = 8765) -> None:
        """Start WebSocket server streaming checkpoint events."""
    
    async def broadcast(self, event: CheckpointEvent) -> None:
        """Broadcast an event to all connected WebSocket clients."""
    
    def add_client(self, client: WebSocketClient) -> None: ...
    def remove_client(self, client: WebSocketClient) -> None: ...
```

### Checkpoint Operations

```python
@dataclass
class CheckpointConfig:
    """Configuration for checkpoint behavior."""
    checkpoint_dir: Path = Path("~/.crawlforge/checkpoints").expanduser()
    max_checkpoints_per_session: int = 20
    compress_screenshots: bool = True
    screenshot_quality: int = 70       # JPEG quality 0-100
    save_interval_spins: int = 5        # checkpoint every N spins
    save_interval_seconds: int = 300    # or every N seconds (whichever first)
    websocket_enabled: bool = True
    websocket_port: int = 8765

@dataclass
class CheckpointMetadata:
    """Lightweight checkpoint metadata (without loading full data)."""
    checkpoint_id: str
    session_id: str
    created_at: datetime
    spin_number: int
    balance: float
    screenshot_thumbnail: bytes | None  # small preview
    path: str                          # disk path

@dataclass
class RecoveryInfo:
    """Information about a recoverable interrupted session."""
    session_id: str
    last_checkpoint: CheckpointMetadata
    interrupted_at: datetime
    runtime_state: dict                # what runtime was active

@dataclass
class CheckpointEvent:
    """Event streamed over WebSocket."""
    event_type: CheckpointEventType
    session_id: str
    checkpoint_id: str | None
    timestamp: datetime
    payload: dict

class CheckpointEventType(Enum):
    SAVED = "checkpoint_saved"
    LOADED = "checkpoint_loaded"
    RECOVERED = "checkpoint_recovered"
    DELETED = "checkpoint_deleted"
    ERROR = "checkpoint_error"
    SESSION_INTERRUPTED = "session_interrupted"
    SESSION_RESUMED = "session_resumed"
```

### Recovery Workflow

```python
class CheckpointRecovery:
    """Handles the recovery workflow after a crash or interruption."""
    
    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        runtime_manager: RuntimeManager,
        event_bus: EventBus
    ):
        self._cm = checkpoint_manager
        self._rm = runtime_manager
        self._event_bus = event_bus
    
    def try_recover(self) -> RecoveryResult | None:
        """Attempt to recover an interrupted session."""
    
    def recover_session(
        self,
        checkpoint: Checkpoint,
        runtime: Runtime
    ) -> RecoveryResult:
        """Execute the full recovery workflow."""
    
    def verify_runtime_state(self, checkpoint: Checkpoint, runtime: Runtime) -> bool:
        """Verify runtime is in a consistent state for recovery."""
    
    def reinitialize_runtime(self, checkpoint: Checkpoint, runtime: Runtime) -> None:
        """Reconnect runtime and navigate to game state from checkpoint."""

@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    success: bool
    recovered_session: GameSession | None
    last_checkpoint: Checkpoint | None
    resume_spin_number: int
    current_balance: float | None
    errors: list[str]
    recovered_at: datetime
```

### Self-Healing

```python
class SelfHealingMonitor:
    """Monitors runtime health and triggers self-healing on failure."""
    
    def __init__(
        self,
        runtime: Runtime,
        checkpoint_manager: CheckpointManager,
        event_bus: EventBus,
        config: SelfHealingConfig | None = None
    ):
        self._runtime = runtime
        self._cm = checkpoint_manager
        self._event_bus = event_bus
        self._config = config or SelfHealingConfig()
        self._failure_count = 0
    
    def monitor_loop(self) -> None:
        """Run monitoring loop. Blocks. Calls self.heal() on failures."""
    
    def heal(self, error: Exception) -> HealingResult:
        """Attempt to heal from a runtime failure."""
    
    def should_retry(self) -> bool:
        """Check if retry is warranted based on failure history."""
    
    async def heal_async(self, error: Exception) -> HealingResult:
        """Async version of heal() for WebSocket-integrated healing."""

@dataclass
class SelfHealingConfig:
    """Configuration for self-healing behavior."""
    max_retries: int = 3
    base_delay_ms: int = 1000          # exponential backoff base
    max_delay_ms: int = 30000
    screenshot_on_failure: bool = True   # capture failure screenshot
    always_checkpoint_before_heal: bool = True

@dataclass
class HealingResult:
    """Result of a self-healing attempt."""
    healed: bool
    attempts: int
    actions_taken: list[str]             # e.g., ["reconnect_adb", "relaunch_app"]
    final_error: str | None
    recovery_checkpoint: Checkpoint | None
```

---

## Data Structures

| Structure | Fields | Purpose |
|---|---|---|
| `CheckpointConfig` | dir, max count, compression, intervals, WebSocket port | Checkpoint settings |
| `CheckpointMetadata` | id, session, timestamp, spin, balance, thumbnail, path | Lightweight checkpoint info |
| `RecoveryInfo` | session, last checkpoint, interrupted time, runtime state | Recovery eligibility |
| `CheckpointEvent` | event_type, session_id, checkpoint_id, timestamp, payload | WebSocket event |
| `CheckpointEventType` | enum of checkpoint event types | Event classification |
| `RecoveryResult` | success, session, checkpoint, resume spin, balance, errors | Recovery outcome |
| `SelfHealingConfig` | max_retries, delay, screenshot flag | Healing settings |
| `HealingResult` | healed, attempts, actions, error, checkpoint | Healing outcome |

---

## Implementation Steps

### Step 1: Directory + Config (Day 1 - 30 min)
```bash
mkdir -p src/crawlforge/checkpoint

# Write config.py with CheckpointConfig and SelfHealingConfig
# Create checkpoint directory on init if not exists
```

### Step 2: CheckpointManager Core (Day 1 - 1.5 hrs)
```python
# Write saver.py (CheckpointManager implementation)
# Implement save() with FileLock for thread safety
# Save: JSON (checkpoint data) + screenshot files
# Compress screenshots with Pillow (JPEG quality)
# Implement load() with orjson for fast JSON parsing
```

### Step 3: Checkpoint Listing + Cleanup (Day 1 - 1 hr)
```python
# Implement list_checkpoints() — lightweight metadata only
# Implement delete_old() — keep only N most recent
# Use directory listing + mtime sorting (no full load needed)
```

### Step 4: WebSocket Server (Day 2 - 2 hrs)
```python
# Write websocket_events.py
# Implement start_websocket_server() with asyncio
# Accept WebSocket connections
# Broadcast CheckpointEvent to all clients
# Handle client connect/disconnect gracefully
# Ping/pong for connection health
```

### Step 5: Recovery Workflow (Day 2 - 2 hrs)
```python
# Write recovery.py (CheckpointRecovery class)
# Implement try_recover() — check for interrupted sessions
# Implement recover_session() — full recovery sequence
# Verify runtime state matches checkpoint
# Reinitialize runtime if needed
```

### Step 6: Self-Healing Monitor (Day 3 - 2 hrs)
```python
# Write self_healing.py (SelfHealingMonitor class)
# Implement monitor_loop() with heartbeat ping
# Implement heal() with exponential backoff
# On failure: checkpoint → reconnect runtime → retry action
# Emit healing events to event bus
```

### Step 7: Integration (Day 3 - 1 hr)
```python
# Integrate with MODULE-04 ReActLoop (checkpoint_interval)
# Integrate with MODULE-10 Scheduler (auto-recovery on startup)
# Test full recovery from simulated crash
```

---

## Testing Strategy

| Test | What | Method |
|---|---|---|
| `test_save_and_load_roundtrip` | Checkpoint saves and loads correctly | Unit test with temp dir |
| `test_save_thread_safe` | Concurrent saves don't corrupt | Threading test |
| `test_delete_old_keeps_n` | delete_old() keeps correct count | Unit test |
| `test_list_checkpoints_returns_metadata` | list returns lightweight metadata | Unit test |
| `test_recovery_loads_correct_state` | Recovery restores correct balance/spin | Mock runtime |
| `test_self_healing_retries_with_backoff` | Exponential backoff respected | Mock time |
| `test_websocket_broadcast` | WS server broadcasts to all clients | Mock WS server |
| `test_compress_screenshot_size` | Compressed screenshot < threshold | Unit test |

---

## Success Criteria

1. ✅ `CheckpointManager.save()` completes in < 500ms (excluding large screenshots)
2. ✅ `CheckpointManager.load()` correctly restores all session state fields
3. ✅ `list_checkpoints()` is fast (no full checkpoint loading)
4. ✅ `delete_old()` keeps the N most recent checkpoints
5. ✅ WebSocket server accepts multiple concurrent clients
6. ✅ All checkpoint events broadcast to all connected clients
7. ✅ `try_recover()` correctly identifies interrupted sessions
8. ✅ Self-healing retries with exponential backoff (1s, 2s, 4s... up to 30s)
9. ✅ After `max_retries` failures, healing stops and emits CRITICAL event
10. ✅ Checkpoint saved automatically before any self-healing attempt
