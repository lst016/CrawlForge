# MODULE-10-scheduler.md — Multi-Game Scheduler & Resource Pool

> **Module ID:** 10  
> **Depends on:** MODULE-01, MODULE-02, MODULE-05, MODULE-08, MODULE-09  
> **Reference Influence:** PantheonOS multi-agent scheduling + Hive resource pooling

---

## Module Overview

MODULE-10 orchestrates **multi-game concurrent execution** with intelligent resource management:

- **Multi-game queue**: manage concurrent sessions across multiple slot games
- **Resource pool**: limit concurrent ADB devices / browser instances
- **Scheduling strategy**: round-robin, priority-based, ROI-optimized
- **Evolution integration**: apply evolved strategies from MODULE-06
- **Checkpoint-driven recovery**: auto-recover interrupted sessions on startup

This is the top-level orchestrator that MODULE-06 evolution and MODULE-09 data collection plug into.

---

## Dependencies

| Module | Dependency Type | Reason |
|---|---|---|
| MODULE-01 | **Hard** | All dataclasses, exceptions |
| MODULE-02 | **Hard** | RuntimeManager for runtime allocation |
| MODULE-05 | **Hard** | CheckpointManager for session recovery |
| MODULE-08 | **Hard** | SlotGameAdapter for game execution |
| MODULE-09 | **Hard** | DataCollector for session data |

### External Dependencies
```txt
# Async scheduling
asyncio>=3.4.3

# Priority queues
heapq  # stdlib

# Periodic tasks
schedule>=1.2.0  # or asyncio built-in

# Resource limiting
# (custom semaphore implementation)
```

---

## API Design

### Scheduler

```python
class Scheduler:
    """
    Top-level orchestrator for multi-game scheduling.
    Manages game queue, resource allocation, and session lifecycle.
    """
    
    def __init__(
        self,
        runtime_manager: RuntimeManager,
        checkpoint_manager: CheckpointManager,
        data_collector: DataCollector,
        evolution_engine: EvolutionEngine | None,
        event_bus: EventBus,
        config: SchedulerConfig | None = None
    ):
        self._rm = runtime_manager
        self._cm = checkpoint_manager
        self._dc = data_collector
        self._evolution = evolution_engine
        self._event_bus = event_bus
        self._config = config or SchedulerConfig()
        self._game_queue: PriorityQueue[QueuedGame] = PriorityQueue()
        self._active_sessions: dict[str, GameSession] = {}
        self._resource_pool: ResourcePool
        self._is_running = False
        self._evolution_applier: EvolutionApplier | None = None
    
    # ── Lifecycle ──
    
    def start(self) -> None:
        """Start the scheduler. Begins processing the game queue."""
    
    def stop(self, graceful: bool = True) -> None:
        """Stop the scheduler. If graceful, finish active sessions first."""
    
    def pause(self) -> None:
        """Pause scheduling (queue continues filling)."""
    
    def resume(self) -> None:
        """Resume scheduling from paused state."""
    
    # ── Game Queue ──
    
    def enqueue_game(self, game_id: str, priority: int = 5) -> None:
        """Add a game to the execution queue."""
    
    def enqueue_games(self, game_ids: list[str], priority: int = 5) -> None:
        """Add multiple games to the queue (batch)."""
    
    def dequeue_game(self) -> QueuedGame | None:
        """Remove and return the highest priority game from queue."""
    
    def get_queue_size(self) -> int: ...
    
    # ── Session Management ──
    
    def start_session(self, game_id: str) -> GameSession:
        """Start a new session for a game (acquires resources, inits adapter)."""
    
    def end_session(self, session_id: str) -> GameSession:
        """End a session, release resources, record data."""
    
    def pause_session(self, session_id: str) -> None:
        """Pause an active session (checkpoint + release resources)."""
    
    def resume_session(self, session_id: str) -> None:
        """Resume a paused session (reload checkpoint, reacquire resources)."""
    
    # ── Resource Pool ──
    
    def acquire_resource(self, runtime_type: RuntimeType) -> Runtime:
        """Acquire a runtime from the pool (blocks if none available)."""
    
    def release_resource(self, runtime: Runtime) -> None:
        """Return a runtime to the pool."""
    
    def get_available_resources(self) -> dict[RuntimeType, int]: ...
    
    # ── Evolution Integration ──
    
    def apply_evolved_strategy(self, genome: Genome) -> None:
        """Apply an evolved strategy genome to future sessions."""
    
    def should_use_evolved_strategy(self, game_id: str) -> bool:
        """Check if evolved strategy should be used for a game."""
    
    # ── Recovery ──
    
    def recover_interrupted_sessions(self) -> list[RecoveryResult]:
        """On startup, recover any sessions that were interrupted."""
    
    def get_active_sessions(self) -> list[GameSession]: ...
```

### Supporting Classes

```python
@dataclass
class QueuedGame:
    """A game waiting in the execution queue."""
    game_id: str
    priority: int                        # lower = higher priority (heap)
    enqueued_at: datetime
    enqueued_by: str | None = None      # "user", "evolution", "scheduler"
    estimated_duration_minutes: int | None = None

@dataclass(order=True)
class PrioritizedSession:
    """A session with scheduling priority."""
    priority: int
    session: GameSession = field(compare=False)

class ResourcePool:
    """
    Pool of reusable runtimes with capacity limits.
    Prevents over-subscription of physical devices/browsers.
    """
    
    def __init__(self, config: ResourcePoolConfig):
        self._config = config
        self._runtimes: dict[RuntimeType, list[Runtime]] = defaultdict(list)
        self._available: dict[RuntimeType, asyncio.Semaphore] = {}
        self._in_use: dict[RuntimeType, set[Runtime]] = defaultdict(set)
    
    def add_runtime(self, runtime: Runtime) -> None:
        """Add a runtime instance to the pool."""
    
    def acquire(self, runtime_type: RuntimeType) -> Runtime:
        """Acquire a runtime (blocks until one is available)."""
    
    async def acquire_async(self, runtime_type: RuntimeType) -> Runtime:
        """Async version of acquire."""
    
    def release(self, runtime: Runtime) -> None:
        """Release a runtime back to the pool."""
    
    def get_in_use_count(self, runtime_type: RuntimeType) -> int: ...
    
    def get_available_count(self, runtime_type: RuntimeType) -> int: ...

@dataclass
class ResourcePoolConfig:
    """Configuration for resource pool sizes."""
    max_adb_devices: int = 2             # physical device limit
    max_playwright_browsers: int = 3    # browser instance limit
    max_concurrent_sessions: int = 5    # total session limit
    idle_timeout_seconds: int = 300     # release idle runtimes after this

@dataclass
class SchedulerConfig:
    """Configuration for the scheduler."""
    max_concurrent_sessions: int = 5
    session_timeout_minutes: int = 60
    checkpoint_interval_spins: int = 5
    evolve_strategy_applied: bool = True
    evolve_interval_minutes: int = 60
    recover_on_startup: bool = True
    queue_check_interval_seconds: int = 10

@dataclass
class EvolutionApplier:
    """Applies evolved strategies to the scheduler."""
    
    def __init__(self, scheduler: Scheduler, evolution_engine: EvolutionEngine):
        self._scheduler = scheduler
        self._engine = evolution_engine
        self._pending_genome: Genome | None = None
    
    def on_new_best_genome(self, genome: Genome) -> None:
        """Called when evolution finds a new best genome."""
    
    def apply_pending_strategy(self) -> None:
        """Apply the pending evolved strategy to future sessions."""
```

### Multi-Game Queue

```python
class MultiGameQueue:
    """
    Priority queue for managing multiple games.
    Supports priority boosting and fairness mechanisms.
    """
    
    def __init__(self, config: QueueConfig | None = None):
        self._config = config or QueueConfig()
        self._queue: list[QueuedGame] = []
        self._game_last_run: dict[str, datetime] = {}   # for fairness
        self._total_enqueued = 0
    
    def enqueue(self, game_id: str, priority: int = 5) -> None:
        """Add game to queue."""
    
    def dequeue(self) -> QueuedGame | None:
        """Remove and return highest priority game."""
    
    def peek(self) -> QueuedGame | None:
        """View next game without removing."""
    
    def boost_priority(self, game_id: str, boost: int) -> None:
        """Boost priority of a specific game in queue."""
    
    def get_position(self, game_id: str) -> int | None:
        """Get queue position of a game (1-indexed)."""
    
    def remove(self, game_id: str) -> bool:
        """Remove a specific game from queue."""
    
    @property
    def size(self) -> int: ...

@dataclass
class QueueConfig:
    """Configuration for multi-game queue."""
    max_queue_size: int = 100
    fairness_window_minutes: int = 30   # prevent same game dominating
    priority_decay_enabled: bool = True  # lower priority over time in queue
    priority_decay_rate: float = 0.1    # per-minute decay rate
```

### Session Lifecycle Hooks

```python
class SessionLifecycleHooks:
    """Hooks for session lifecycle events (for external integrations)."""
    
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
    
    def on_session_start(self, session: GameSession) -> None:
        """Called when a new session starts."""
        self._event_bus.emit("scheduler", "session_started", {"session_id": session.id})
    
    def on_session_end(self, session: GameSession) -> None:
        """Called when a session ends."""
        self._event_bus.emit("scheduler", "session_ended", {"session_id": session.id})
    
    def on_session_paused(self, session: GameSession) -> None:
        """Called when a session is paused."""
    
    def on_resource_acquired(self, session_id: str, runtime_type: RuntimeType) -> None:
        """Called when a resource is acquired for a session."""
    
    def on_resource_released(self, session_id: str, runtime_type: RuntimeType) -> None:
        """Called when a resource is released."""
```

---

## Data Structures

| Structure | Fields | Purpose |
|---|---|---|
| `QueuedGame` | game_id, priority, enqueued_at, enqueued_by, estimated_duration | Queue entry |
| `PrioritizedSession` | priority (sort key), session | Sortable session wrapper |
| `ResourcePool` | runtimes, available, in_use per RuntimeType | Runtime resource management |
| `ResourcePoolConfig` | max_adb, max_playwright, max_sessions, idle_timeout | Pool limits |
| `SchedulerConfig` | concurrency, timeout, checkpoint interval, evolution settings | Scheduler configuration |
| `EvolutionApplier` | scheduler, engine, pending_genome | Evolution → Scheduler bridge |
| `MultiGameQueue` | queue, game_last_run, config | Queue with fairness |
| `QueueConfig` | max_size, fairness_window, priority_decay | Queue configuration |

---

## Implementation Steps

### Step 1: Config + ResourcePool (Day 1 - 1.5 hrs)
```bash
mkdir -p src/crawlforge/scheduler

# Write config.py with SchedulerConfig, ResourcePoolConfig, QueueConfig
# Write resource_pool.py
# Implement ResourcePool with Semaphore-based concurrency control
# Add runtime instances, track in_use vs available
```

### Step 2: MultiGameQueue (Day 1 - 1.5 hrs)
```python
# Write multi_game_queue.py
# Implement MultiGameQueue using heapq
# Implement fairness: track last_run time, adjust priority
# Implement boost_priority() and remove()
# Priority: heap (lower number = higher priority)
```

### Step 3: Scheduler Core (Day 2 - 2.5 hrs)
```python
# Write scheduler.py (main Scheduler class)
# Implement start() / stop() / pause() / resume()
# Implement enqueue_game() / enqueue_games()
# Implement start_session() — acquire resource, init adapter, start ReActLoop
# Implement end_session() — record data, release resource
# Main loop: poll queue, start sessions up to max_concurrent_sessions
```

### Step 4: Session Lifecycle + Hooks (Day 2 - 1 hr)
```python
# Write session_hooks.py
# Implement SessionLifecycleHooks
# Emit events on session start/end/pause/resume
# Connect to CheckpointManager for auto-checkpointing
```

### Step 5: Evolution Integration (Day 3 - 1.5 hrs)
```python
# Write evolution_applier.py (EvolutionApplier class)
# Listen for evolution best_genome events
# implement on_new_best_genome() — store pending genome
# implement apply_pending_strategy() — update scheduler's active strategy
# Make should_use_evolved_strategy() check game_id compatibility
```

### Step 6: Recovery on Startup (Day 3 - 1.5 hrs)
```python
# Implement recover_interrupted_sessions()
# Call CheckpointManager.get_recoverable_session() on startup
# For each recoverable session: load checkpoint, reacquire resource, resume
# Emit SESSION_RESUMED events
```

### Step 7: Testing + Integration (Day 3 - 1.5 hrs)
```python
# Test: start 3 sessions concurrently (respects max_concurrent_sessions)
# Test: queue fairness prevents single game from dominating
# Test: evolution genome applied to new sessions
# Test: interrupted session recovered correctly
```

---

## Testing Strategy

| Test | What | Method |
|---|---|---|
| `test_resource_pool_respects_limits` | ADB pool max 2, Playwright max 3 | Mock runtimes |
| `test_resource_pool_blocks_when_full` | acquire blocks when all in use | Mock Semaphore |
| `test_resource_pool_releases_correctly` | release returns runtime to available | Unit test |
| `test_multi_game_queue_priority` | Highest priority dequeued first | heapq property test |
| `test_multi_game_queue_fairness` | Same game not dequeued twice in fairness window | Mock time |
| `test_scheduler_respects_max_concurrent` | Never exceeds max_concurrent_sessions | Mock resource pool |
| `test_scheduler_starts_and_stops` | start/stop lifecycle correct | Integration test |
| `test_evolution_applier_stores_pending` | pending_genome stored on new best | Mock engine |
| `test_evolution_applier_applies_to_sessions` | New sessions use evolved strategy | Mock |
| `test_recovery_restores_correct_session` | Recovered session matches checkpoint | Mock checkpoint |
| `test_hook_fires_on_session_start` | EventBus receives session_started | Mock EventBus |

---

## Success Criteria

1. ✅ `Scheduler.start()` begins processing queue without blocking
2. ✅ `Scheduler.stop(graceful=True)` waits for active sessions to complete
3. ✅ `enqueue_game()` adds game to priority queue
4. ✅ `start_session()` acquires resource from pool (blocks if at capacity)
5. ✅ `end_session()` releases resource back to pool
6. ✅ ResourcePool never exceeds max limits per runtime type
7. ✅ MultiGameQueue respects fairness window (same game not over-represented)
8. ✅ EvolutionApplier stores pending genome and applies to new sessions
9. ✅ `recover_interrupted_sessions()` restores all interrupted sessions
10. ✅ Scheduler emits session lifecycle events to EventBus
11. ✅ Pause/resume preserves session state correctly
12. ✅ Evolution genome is game-specific (only applied to matching game_id)
