"""
Tests for CheckpointManager.
"""

import pytest
import tempfile
from pathlib import Path
from crawlforge.checkpoint import CheckpointManager, CheckpointData


def test_checkpoint_manager_save():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CheckpointManager(Path(tmpdir))
        cp = manager.save(
            game_name="TestGame",
            session_id="sess-001",
            state={"balance": 5000, "spin_count": 10},
        )
        assert cp.game_name == "TestGame"
        assert cp.balance == 5000
        assert cp.spin_count == 10
        assert cp.session_id == "sess-001"


def test_checkpoint_manager_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CheckpointManager(Path(tmpdir))
        cp = manager.save(
            game_name="TestGame",
            session_id="sess-001",
            state={"balance": 5000, "spin_count": 10},
        )
        loaded = manager.load(cp.checkpoint_id)
        assert loaded is not None
        assert loaded.checkpoint_id == cp.checkpoint_id


def test_checkpoint_manager_load_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CheckpointManager(Path(tmpdir))
        manager.save(
            game_name="TestGame",
            session_id="sess-001",
            state={"balance": 5000, "spin_count": 10},
        )
        checkpoints = manager.list_checkpoints()
        state = manager.load_state(checkpoints[0].checkpoint_id)
        assert state is not None
        assert state["balance"] == 5000


def test_checkpoint_manager_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CheckpointManager(Path(tmpdir))
        manager.save("GameA", "s1", {"balance": 100})
        manager.save("GameA", "s2", {"balance": 200})
        manager.save("GameB", "s3", {"balance": 300})

        all_cps = manager.list_checkpoints()
        assert len(all_cps) == 3

        game_a = manager.list_checkpoints(game_name="GameA")
        assert len(game_a) == 2


def test_checkpoint_manager_delete():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CheckpointManager(Path(tmpdir))
        cp = manager.save("GameA", "s1", {"balance": 100})
        assert manager.delete(cp.checkpoint_id) is True
        assert manager.load(cp.checkpoint_id) is None


def test_checkpoint_manager_get_latest():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CheckpointManager(Path(tmpdir))
        cp1 = manager.save("GameA", "s1", {"balance": 100})
        cp2 = manager.save("GameA", "s2", {"balance": 200})

        latest = manager.get_latest("GameA")
        assert latest is not None
        assert latest.balance == 200
