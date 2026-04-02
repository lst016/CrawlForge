"""
Checkpoint System - snapshot, recovery, and rollback for CrawlForge.

Provides:
- Checkpoint creation with full state capture
- Recovery from checkpoints
- Rollback to previous checkpoints
"""

import json
import time
import uuid
import hashlib
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Any


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
    metadata: dict = field(default_factory=dict)
    file_path: Optional[str] = None


class CheckpointManager:
    """
    Manages checkpoints for game sessions.

    Checkpoints capture:
    - Game state (balance, spin count, etc.)
    - Runtime state
    - Adapter state
    - Execution history

    Usage:
        manager = CheckpointManager("/tmp/crawlforge_checkpoints")
        await manager.save(adapter, runtime, {"balance": 5000, "spins": 100})
        checkpoint = await manager.load("checkpoint-uuid")
    """

    def __init__(self, storage_dir: Path, max_checkpoints: int = 10):
        self.storage_dir = Path(storage_dir)
        self.max_checkpoints = max_checkpoints
        self._checkpoints: list[CheckpointData] = []
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        game_name: str,
        session_id: str,
        state: dict,
        runtime_state: Optional[bytes] = None,
        metadata: Optional[dict] = None,
    ) -> CheckpointData:
        """
        Save a checkpoint.

        Args:
            game_name: Name of the game
            session_id: Session identifier
            state: Game state dict (balance, spins, etc.)
            runtime_state: Optional pickled runtime state
            metadata: Optional additional metadata

        Returns:
            CheckpointData with checkpoint details
        """
        checkpoint_id = str(uuid.uuid4())[:12]
        timestamp = datetime.now()
        balance = state.get("balance", 0)
        spin_count = state.get("spin_count", 0)

        # Create state hash
        state_bytes = json.dumps(state, sort_keys=True).encode()
        state_hash = hashlib.sha256(state_bytes).hexdigest()[:16]

        # Determine file path
        filename = f"checkpoint_{checkpoint_id}.json"
        file_path = self.storage_dir / filename

        # Create checkpoint data
        checkpoint = CheckpointData(
            checkpoint_id=checkpoint_id,
            timestamp=timestamp,
            game_name=game_name,
            balance=balance,
            spin_count=spin_count,
            session_id=session_id,
            state_hash=state_hash,
            metadata=metadata or {},
            file_path=str(file_path),
        )

        # Save checkpoint file
        data = {
            "checkpoint_id": checkpoint_id,
            "timestamp": timestamp.isoformat(),
            "game_name": game_name,
            "session_id": session_id,
            "state": state,
            "runtime_state": runtime_state.hex() if runtime_state else None,
            "metadata": metadata or {},
            "state_hash": state_hash,
        }
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        # Track in memory
        self._checkpoints.append(checkpoint)

        # Prune old checkpoints
        self._prune()

        return checkpoint

    def load(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """Load a checkpoint by ID."""
        for cp in self._checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                return cp
        return None

    def load_state(self, checkpoint_id: str) -> Optional[dict]:
        """Load checkpoint state dict."""
        checkpoint = self.load(checkpoint_id)
        if checkpoint is None or checkpoint.file_path is None:
            return None
        try:
            with open(checkpoint.file_path) as f:
                data = json.load(f)
            return data.get("state")
        except (IOError, json.JSONDecodeError):
            return None

    def list_checkpoints(self, game_name: Optional[str] = None, session_id: Optional[str] = None) -> list[CheckpointData]:
        """List all checkpoints, optionally filtered."""
        results = self._checkpoints
        if game_name:
            results = [cp for cp in results if cp.game_name == game_name]
        if session_id:
            results = [cp for cp in results if cp.session_id == session_id]
        return sorted(results, key=lambda cp: cp.timestamp, reverse=True)

    def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        for i, cp in enumerate(self._checkpoints):
            if cp.checkpoint_id == checkpoint_id:
                if cp.file_path:
                    Path(cp.file_path).unlink(missing_ok=True)
                self._checkpoints.pop(i)
                return True
        return False

    def _prune(self) -> None:
        """Remove old checkpoints beyond max_checkpoints."""
        while len(self._checkpoints) > self.max_checkpoints:
            oldest = self._checkpoints.pop(0)
            if oldest.file_path:
                Path(oldest.file_path).unlink(missing_ok=True)

    def get_latest(self, game_name: Optional[str] = None) -> Optional[CheckpointData]:
        """Get the most recent checkpoint."""
        checkpoints = self.list_checkpoints(game_name=game_name)
        return checkpoints[0] if checkpoints else None


class RollbackManager:
    """
    Manages rollback operations.

    Tracks a history of operations and can revert to previous states.
    """

    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self._history: list[dict] = []

    def record_operation(self, operation: str, state_before: dict, checkpoint_id: str) -> None:
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
            # The state_before is the state we revert to
            # This is already saved in the checkpoint

        # Return the state from the most recent remaining checkpoint
        if self._history:
            latest_cp_id = self._history[-1]["checkpoint_id"]
            return self.checkpoint_manager.load_state(latest_cp_id)

        return None

    def clear_history(self) -> None:
        """Clear rollback history."""
        self._history.clear()
