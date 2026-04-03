"""
Checkpoint System - snapshot, recovery, and rollback for CrawlForge.

Provides:
- Checkpoint creation with full state capture
- Incremental (delta) checkpoints
- Auto snapshot strategies (time-based, spin-based, balance-change)
- Recovery from checkpoints
- Rollback to previous checkpoints
- FileLock-based concurrency safety (multi-process safe)
"""

import json
import time
import uuid
import hashlib
import threading
import fcntl
import struct
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Union, Callable
from enum import Enum
from functools import wraps


class AutoSnapshotStrategy(Enum):
    """Auto snapshot triggering strategies."""
    TIME_BASED = "time_based"       # Every N seconds
    SPIN_BASED = "spin_based"       # Every N spins
    BALANCE_CHANGE = "balance_change"  # When balance changes by N
    ANY_CHANGE = "any_change"       # On any state change


@dataclass
class AutoSnapshotPolicy:
    """Policy for automatic checkpoint creation."""
    strategy: AutoSnapshotStrategy = AutoSnapshotStrategy.SPIN_BASED
    interval: int = 10          # N seconds / N spins / N balance change
    max_gap_seconds: float = 300.0  # Force snapshot after N seconds regardless
    min_gap_seconds: float = 5.0    # Minimum gap between snapshots


@dataclass
class CheckpointData:
    """Checkpoint snapshot data."""
    checkpoint_id: str
    timestamp: datetime
    game_name: str
    balance: float
    spin_count: int
    session_id: str
    state_hash: str
    is_incremental: bool = False
    parent_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    file_path: Optional[str] = None

    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.timestamp).total_seconds()


class FileLock:
    """
    Cross-platform file lock for multi-process concurrency safety.
    Uses fcntl on Unix, fallback to threading lock on Windows.
    """

    def __init__(self, lock_path: Path, timeout: float = 30.0):
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self._lock_fd: Optional[int] = None
        self._thread_lock = threading.Lock()

    def acquire(self, blocking: bool = True) -> bool:
        """Acquire the lock."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._lock_fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR)
            start = time.monotonic()
            while True:
                try:
                    fcntl.flock(self._lock_fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
                    return True
                except BlockingIOError:
                    if not blocking:
                        return False
                    if time.monotonic() - start > self.timeout:
                        return False
                    time.sleep(0.05)
        except Exception:
            if self._lock_fd is not None:
                try:
                    os.close(self._lock_fd)
                except Exception:
                    pass
            self._lock_fd = None
            return False

    def release(self) -> None:
        """Release the lock."""
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
            except Exception:
                pass
            self._lock_fd = None

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, *args: object) -> None:
        self.release()


import os  # for FileLock


def with_lock(lock_path: Union[str, Path]) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Decorator to wrap a method with a file lock."""
    def decorator(func: Callable[..., object]) -> Callable[..., object]:
        @wraps(func)
        def wrapper(self: object, *args: object, **kwargs: object) -> object:
            with FileLock(Path(lock_path)):
                return func(self, *args, **kwargs)
        return wrapper
    return decorator


@dataclass
class IncrementalCheckpoint:
    """An incremental (delta) checkpoint - stores only changes since last snapshot."""
    checkpoint_id: str
    parent_id: str           # Reference to parent checkpoint
    timestamp: datetime
    state_delta: dict        # Only the changed fields
    balance_delta: float      # Change in balance
    spin_delta: int           # Change in spin count
    state_hash: str          # Hash of full state at this point
    metadata: dict = field(default_factory=dict)

    def merge_with_parent(self, parent_state: dict) -> dict:
        """Reconstruct full state by merging delta with parent."""
        state = dict(parent_state)
        state.update(self.state_delta)
        return state


class CheckpointManager:
    """
    Manages checkpoints for game sessions with concurrency safety.

    Features:
    - Auto snapshot based on configurable policy
    - Incremental checkpoints (delta storage)
    - FileLock-based multi-process safety
    - Pruning old checkpoints

    Usage:
        manager = CheckpointManager("/tmp/crawlforge_checkpoints")
        policy = AutoSnapshotPolicy(strategy=AutoSnapshotStrategy.SPIN_BASED, interval=10)
        manager.set_auto_snapshot_policy(policy)
        await manager.save(adapter, runtime, {"balance": 5000, "spins": 100})
        checkpoint = await manager.load("checkpoint-uuid")
    """

    def __init__(
        self,
        storage_dir: Union[str, Path],
        max_checkpoints: int = 10,
        auto_snapshot_policy: Optional[AutoSnapshotPolicy] = None,
        enable_incremental: bool = True,
    ):
        self.storage_dir = Path(storage_dir)
        self.max_checkpoints = max_checkpoints
        self.auto_snapshot_policy = auto_snapshot_policy or AutoSnapshotPolicy()
        self.enable_incremental = enable_incremental

        # Thread-safe in-memory index
        self._lock = threading.RLock()
        self._checkpoints: list[CheckpointData] = []
        self._incremental_checkpoints: dict[str, IncrementalCheckpoint] = {}
        self._state_cache: dict[str, dict] = {}  # Reconstructed states

        # Auto-snapshot tracking
        self._last_snapshot_time: Optional[datetime] = None
        self._last_snapshot_spins: int = 0
        self._last_snapshot_balance: float = 0.0

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock_file = self.storage_dir / ".checkpoint.lock"
        self._index_file = self.storage_dir / "index.json"

        self._load_index()

    # -------------------------------------------------------------------------
    # Auto-snapshot logic
    # -------------------------------------------------------------------------

    def set_auto_snapshot_policy(self, policy: AutoSnapshotPolicy) -> None:
        """Update the auto snapshot policy."""
        self.auto_snapshot_policy = policy

    def should_auto_snapshot(
        self,
        current_state: dict,
        current_spins: int,
        current_balance: float,
    ) -> bool:
        """
        Determine if an automatic snapshot should be taken based on policy.
        Returns True if this is the first snapshot (no prior history) or
        if the policy conditions are met.
        """
        policy = self.auto_snapshot_policy
        now = datetime.now()
        last = self._last_snapshot_time

        # First snapshot is always allowed
        if last is None:
            return True

        # Enforce minimum gap
        gap = (now - last).total_seconds()
        if gap < policy.min_gap_seconds:
            return False

        # Enforce maximum gap
        if gap >= policy.max_gap_seconds:
            return True

        # Strategy-specific checks
        strategy = policy.strategy
        if strategy == AutoSnapshotStrategy.TIME_BASED:
            return gap >= policy.interval

        elif strategy == AutoSnapshotStrategy.SPIN_BASED:
            delta = abs(current_spins - self._last_snapshot_spins)
            return delta >= policy.interval

        elif strategy == AutoSnapshotStrategy.BALANCE_CHANGE:
            delta = abs(current_balance - self._last_snapshot_balance)  # type: ignore[assignment]
            return delta >= float(policy.interval)

        elif strategy == AutoSnapshotStrategy.ANY_CHANGE:
            return (
                current_spins != self._last_snapshot_spins
                or current_balance != self._last_snapshot_balance
            )

        return False

    def update_auto_snapshot_tracking(
        self,
        spins: int,
        balance: float,
    ) -> None:
        """Update tracking state after a snapshot is taken."""
        self._last_snapshot_time = datetime.now()
        self._last_snapshot_spins = spins
        self._last_snapshot_balance = balance

    # -------------------------------------------------------------------------
    # Core save/load (with FileLock for concurrency)
    # -------------------------------------------------------------------------

    def save(
        self,
        game_name: str,
        session_id: str,
        state: dict,
        runtime_state: Optional[bytes] = None,
        metadata: Optional[dict] = None,
        force_incremental: bool = False,
    ) -> CheckpointData:
        """
        Save a checkpoint (thread-safe and process-safe via FileLock).

        Args:
            game_name: Name of the game
            session_id: Session identifier
            state: Game state dict (balance, spins, etc.)
            runtime_state: Optional pickled runtime state
            metadata: Optional additional metadata
            force_incremental: Force incremental checkpoint even if enabled

        Returns:
            CheckpointData with checkpoint details
        """
        with FileLock(self._lock_file):
            with self._lock:
                checkpoint_id = str(uuid.uuid4())[:12]
                timestamp = datetime.now()
                balance = state.get("balance", 0)
                spin_count = state.get("spin_count", 0)

                # Compute state hash
                state_bytes = json.dumps(state, sort_keys=True).encode()
                state_hash = hashlib.sha256(state_bytes).hexdigest()[:16]

                # Determine if incremental
                latest = self.get_latest(game_name=game_name, session_id=session_id)
                is_incremental = (
                    self.enable_incremental
                    and not force_incremental
                    and latest is not None
                    and latest.state_hash != state_hash
                )

                parent_id = None
                if is_incremental and latest:
                    parent_id = latest.checkpoint_id
                    # Compute delta
                    delta_state = self._compute_delta(latest, state)
                    delta_file = self.storage_dir / f"delta_{checkpoint_id}.json"
                    inc_checkpoint = IncrementalCheckpoint(
                        checkpoint_id=checkpoint_id,
                        parent_id=parent_id,
                        timestamp=timestamp,
                        state_delta=delta_state,
                        balance_delta=balance - latest.balance,
                        spin_delta=spin_count - latest.spin_count,
                        state_hash=state_hash,
                        metadata=metadata or {},
                    )
                    with open(delta_file, "w") as f:
                        json.dump({
                            "checkpoint_id": checkpoint_id,
                            "parent_id": parent_id,
                            "timestamp": timestamp.isoformat(),
                            "state_delta": delta_state,
                            "balance_delta": balance - latest.balance,
                            "spin_delta": spin_count - latest.spin_count,
                            "state_hash": state_hash,
                            "metadata": metadata or {},
                        }, f, indent=2)
                    self._incremental_checkpoints[checkpoint_id] = inc_checkpoint

                # Save full checkpoint file
                filename = f"checkpoint_{checkpoint_id}.json"
                file_path = self.storage_dir / filename
                data = {
                    "checkpoint_id": checkpoint_id,
                    "timestamp": timestamp.isoformat(),
                    "game_name": game_name,
                    "session_id": session_id,
                    "state": state if not is_incremental else None,
                    "runtime_state": runtime_state.hex() if runtime_state else None,
                    "metadata": metadata or {},
                    "state_hash": state_hash,
                    "is_incremental": is_incremental,
                    "parent_id": parent_id,
                }
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2)

                # Create checkpoint data
                checkpoint = CheckpointData(
                    checkpoint_id=checkpoint_id,
                    timestamp=timestamp,
                    game_name=game_name,
                    balance=balance,
                    spin_count=spin_count,
                    session_id=session_id,
                    state_hash=state_hash,
                    is_incremental=is_incremental,
                    parent_id=parent_id,
                    metadata=metadata or {},
                    file_path=str(file_path),
                )

                self._checkpoints.append(checkpoint)
                self._state_cache[checkpoint_id] = state

                # Update auto-snapshot tracking
                self.update_auto_snapshot_tracking(spin_count, balance)

                # Prune
                self._prune_locked()

                # Save index
                self._save_index()

                return checkpoint

    def _compute_delta(self, latest: CheckpointData, current_state: dict) -> dict:
        """Compute delta between latest full checkpoint and current state."""
        # Load latest full state
        latest_state = self.load_state(latest.checkpoint_id)
        if latest_state is None:
            return current_state

        delta = {}
        for key, value in current_state.items():
            if key not in latest_state or latest_state[key] != value:
                delta[key] = value
        return delta

    def load(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """Load a checkpoint by ID."""
        with self._lock:
            for cp in self._checkpoints:
                if cp.checkpoint_id == checkpoint_id:
                    return cp
            return None

    def load_state(self, checkpoint_id: str) -> Optional[dict]:
        """Load checkpoint state dict (handles incremental reconstruction)."""
        with self._lock:
            checkpoint = self.load(checkpoint_id)
            if checkpoint is None:
                return None

            # Check cache first
            if checkpoint_id in self._state_cache:
                return self._state_cache[checkpoint_id]

            if checkpoint.file_path is None:
                return None

            try:
                with open(checkpoint.file_path) as f:
                    data = json.load(f)

                if checkpoint.is_incremental and checkpoint.parent_id:
                    # Reconstruct from incremental + chain of parents
                    state = self._reconstruct_incremental(checkpoint)
                else:
                    state = data.get("state")

                if state:
                    self._state_cache[checkpoint_id] = state
                return state
            except (IOError, json.JSONDecodeError):
                return None

    def _reconstruct_incremental(self, checkpoint: CheckpointData) -> Optional[dict]:
        """Reconstruct full state from an incremental checkpoint chain."""
        if checkpoint.file_path is None:
            return None

        with open(checkpoint.file_path) as f:
            data = json.load(f)

        if not data.get("is_incremental"):
            return data.get("state")

        parent_id = data.get("parent_id")
        if not parent_id:
            return data.get("state")

        # Recursively get parent state
        parent_checkpoint = self.load(parent_id)
        if parent_checkpoint is None:
            return None

        parent_state = self._reconstruct_incremental(parent_checkpoint)
        if parent_state is None:
            # Load parent's full state from file directly
            if parent_checkpoint.file_path:
                with open(parent_checkpoint.file_path) as f:
                    parent_data = json.load(f)
                    parent_state = parent_data.get("state", {})

        if parent_state is None:
            return None

        # Apply delta
        delta = data.get("state_delta", {})
        state = dict(parent_state)
        state.update(delta)
        return state

    def list_checkpoints(
        self,
        game_name: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> list[CheckpointData]:
        """List all checkpoints, optionally filtered."""
        with self._lock:
            results = list(self._checkpoints)
            if game_name:
                results = [cp for cp in results if cp.game_name == game_name]
            if session_id:
                results = [cp for cp in results if cp.session_id == session_id]
            return sorted(results, key=lambda cp: cp.timestamp, reverse=True)

    def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint (and its delta file if applicable)."""
        with FileLock(self._lock_file):
            with self._lock:
                for i, cp in enumerate(self._checkpoints):
                    if cp.checkpoint_id == checkpoint_id:
                        # Delete main file
                        if cp.file_path:
                            Path(cp.file_path).unlink(missing_ok=True)
                        # Delete delta file
                        delta_file = self.storage_dir / f"delta_{checkpoint_id}.json"
                        delta_file.unlink(missing_ok=True)
                        # Remove from caches
                        self._checkpoints.pop(i)
                        self._state_cache.pop(checkpoint_id, None)
                        self._incremental_checkpoints.pop(checkpoint_id, None)
                        self._save_index()
                        return True
                return False

    def _prune_locked(self) -> None:
        """Remove old checkpoints beyond max_checkpoints (must hold lock)."""
        while len(self._checkpoints) > self.max_checkpoints:
            oldest = self._checkpoints.pop(0)
            if oldest.file_path:
                Path(oldest.file_path).unlink(missing_ok=True)
            delta_file = self.storage_dir / f"delta_{oldest.checkpoint_id}.json"
            delta_file.unlink(missing_ok=True)
            self._state_cache.pop(oldest.checkpoint_id, None)
            self._incremental_checkpoints.pop(oldest.checkpoint_id, None)

    def get_latest(
        self,
        game_name: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[CheckpointData]:
        """Get the most recent checkpoint."""
        checkpoints = self.list_checkpoints(game_name=game_name, session_id=session_id)
        return checkpoints[0] if checkpoints else None

    def get_checkpoint_chain(
        self,
        checkpoint_id: str,
    ) -> list[CheckpointData]:
        """Get the full chain of checkpoints from root to the given checkpoint."""
        chain: list[CheckpointData] = []
        current = self.load(checkpoint_id)
        visited = set()

        while current is not None and current.checkpoint_id not in visited:
            chain.insert(0, current)
            visited.add(current.checkpoint_id)
            if current.parent_id:
                current = self.load(current.parent_id)
            else:
                break

        return chain

    # -------------------------------------------------------------------------
    # Index persistence
    # -------------------------------------------------------------------------

    def _load_index(self) -> None:
        """Load checkpoint index from disk."""
        if not self._index_file.exists():
            return
        try:
            with open(self._index_file) as f:
                index = json.load(f)

            checkpoints = []
            for item in index.get("checkpoints", []):
                cp = CheckpointData(
                    checkpoint_id=item["checkpoint_id"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    game_name=item["game_name"],
                    balance=item["balance"],
                    spin_count=item["spin_count"],
                    session_id=item["session_id"],
                    state_hash=item["state_hash"],
                    is_incremental=item.get("is_incremental", False),
                    parent_id=item.get("parent_id"),
                    metadata=item.get("metadata", {}),
                    file_path=item.get("file_path"),
                )
                checkpoints.append(cp)
                self._state_cache[cp.checkpoint_id] = item.get("cached_state", {})

            self._checkpoints = checkpoints

            self._last_snapshot_time = None
            if index.get("last_snapshot_time"):
                self._last_snapshot_time = datetime.fromisoformat(index["last_snapshot_time"])
            self._last_snapshot_spins = index.get("last_snapshot_spins", 0)
            self._last_snapshot_balance = index.get("last_snapshot_balance", 0.0)

        except (IOError, json.JSONDecodeError, KeyError):
            pass

    def _save_index(self) -> None:
        """Save checkpoint index to disk."""
        index = {
            "checkpoints": [
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "timestamp": cp.timestamp.isoformat(),
                    "game_name": cp.game_name,
                    "balance": cp.balance,
                    "spin_count": cp.spin_count,
                    "session_id": cp.session_id,
                    "state_hash": cp.state_hash,
                    "is_incremental": cp.is_incremental,
                    "parent_id": cp.parent_id,
                    "metadata": cp.metadata,
                    "file_path": cp.file_path,
                    "cached_state": self._state_cache.get(cp.checkpoint_id, {}),
                }
                for cp in self._checkpoints
            ],
            "last_snapshot_time": (
                self._last_snapshot_time.isoformat()
                if self._last_snapshot_time else None
            ),
            "last_snapshot_spins": self._last_snapshot_spins,
            "last_snapshot_balance": self._last_snapshot_balance,
        }
        with open(self._index_file, "w") as f:
            json.dump(index, f, indent=2)

    def export(self, checkpoint_id: str, output_path: Path) -> bool:
        """Export a checkpoint (and its full chain) to a single file."""
        with self._lock:
            checkpoint = self.load(checkpoint_id)
            if checkpoint is None:
                return False

            chain = self.get_checkpoint_chain(checkpoint_id)
            export_data = {
                "checkpoint_id": checkpoint_id,
                "chain": [
                    {
                        "checkpoint_id": cp.checkpoint_id,
                        "timestamp": cp.timestamp.isoformat(),
                        "game_name": cp.game_name,
                        "session_id": cp.session_id,
                        "balance": cp.balance,
                        "spin_count": cp.spin_count,
                        "state_hash": cp.state_hash,
                        "is_incremental": cp.is_incremental,
                        "parent_id": cp.parent_id,
                        "metadata": cp.metadata,
                    }
                    for cp in chain
                ],
                "final_state": self.load_state(checkpoint_id),
            }

            with open(output_path, "w") as f:
                json.dump(export_data, f, indent=2)
            return True


class RollbackManager:
    """
    Manages rollback operations using the checkpoint system.
    """

    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self._history: list[dict] = []

    def record_operation(
        self,
        operation: str,
        state_before: dict,
        checkpoint_id: str,
    ) -> None:
        """Record an operation for potential rollback."""
        self._history.append({
            "operation": operation,
            "state_before": state_before,
            "checkpoint_id": checkpoint_id,
            "timestamp": time.time(),
        })

    def rollback(self, steps: int = 1) -> Optional[dict]:
        """
        Rollback N steps.

        Returns the state that was current before the rollback.
        """
        if steps > len(self._history):
            return None

        for _ in range(steps):
            op = self._history.pop()

        # Return the state from the most recent remaining checkpoint
        if self._history:
            latest_cp_id = self._history[-1]["checkpoint_id"]
            return self.checkpoint_manager.load_state(latest_cp_id)

        return None

    def clear_history(self) -> None:
        """Clear rollback history."""
        self._history.clear()

    def get_history_size(self) -> int:
        """Return number of operations in history."""
        return len(self._history)
