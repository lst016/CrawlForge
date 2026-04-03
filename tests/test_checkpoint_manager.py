"""
Tests for CheckpointManager.
"""

import json
import time
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timedelta
import unittest

from crawlforge.checkpoint.manager import (
    CheckpointManager, AutoSnapshotPolicy, AutoSnapshotStrategy,
    FileLock, IncrementalCheckpoint, CheckpointData, RollbackManager,
)


class TestFileLock(unittest.TestCase):
    """Test FileLock concurrency."""

    def test_lock_acquire_release(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock = FileLock(lock_path)
            self.assertTrue(lock.acquire())
            lock.release()
            self.assertTrue(lock_path.exists())

    def test_lock_context_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            with FileLock(lock_path):
                self.assertTrue(lock_path.exists())
            # Lock released after context

    def test_non_blocking_acquire(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock1 = FileLock(lock_path)
            lock2 = FileLock(lock_path)
            self.assertTrue(lock1.acquire())
            # Non-blocking should fail while lock held
            self.assertFalse(lock2.acquire(blocking=False))
            lock1.release()
            self.assertTrue(lock2.acquire())
            lock2.release()


class TestAutoSnapshotPolicy(unittest.TestCase):
    """Test auto-snapshot decision logic."""

    def _make_manager(self, tmpdir, policy=None):
        mgr = CheckpointManager(tmpdir, max_checkpoints=10, auto_snapshot_policy=policy)
        return mgr

    def test_time_based_strategy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = AutoSnapshotPolicy(
                strategy=AutoSnapshotStrategy.TIME_BASED,
                interval=5,
                min_gap_seconds=0,  # Disable min gap for testing
                max_gap_seconds=300,
            )
            mgr = self._make_manager(tmpdir, policy)

            # No prior snapshot - first call always returns True
            self.assertTrue(
                mgr.should_auto_snapshot({"balance": 100}, 0, 100)
            )

            # Force time passage
            mgr._last_snapshot_time = datetime.now() - timedelta(seconds=10)
            self.assertTrue(
                mgr.should_auto_snapshot({"balance": 100}, 0, 100)
            )

            # Within interval
            mgr._last_snapshot_time = datetime.now()
            self.assertFalse(
                mgr.should_auto_snapshot({"balance": 100}, 0, 100)
            )

    def test_spin_based_strategy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = AutoSnapshotPolicy(
                strategy=AutoSnapshotStrategy.SPIN_BASED,
                interval=10,
                min_gap_seconds=0,
                max_gap_seconds=300,
            )
            mgr = self._make_manager(tmpdir, policy)

            # Simulate prior snapshot by setting tracking state
            mgr._last_snapshot_time = datetime.now()  # Pretend we already snapshotted
            mgr._last_snapshot_spins = 0
            mgr._last_snapshot_balance = 100

            # Within threshold (10 delta < 10)
            self.assertFalse(mgr.should_auto_snapshot({"balance": 100}, 5, 100))
            # At threshold (10 delta == 10)
            self.assertTrue(mgr.should_auto_snapshot({"balance": 100}, 10, 100))
            # Exceeds threshold (15 delta > 10)
            self.assertTrue(mgr.should_auto_snapshot({"balance": 100}, 15, 100))

    def test_balance_change_strategy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = AutoSnapshotPolicy(
                strategy=AutoSnapshotStrategy.BALANCE_CHANGE,
                interval=50,
                min_gap_seconds=0,
                max_gap_seconds=300,
            )
            mgr = self._make_manager(tmpdir, policy)

            mgr._last_snapshot_time = datetime.now()
            mgr._last_snapshot_balance = 100
            mgr._last_snapshot_spins = 0

            # Within threshold (40 < 50)
            self.assertFalse(mgr.should_auto_snapshot({"balance": 140}, 0, 140))
            # At threshold (50 == 50)
            self.assertTrue(mgr.should_auto_snapshot({"balance": 150}, 0, 150))

    def test_any_change_strategy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = AutoSnapshotPolicy(
                strategy=AutoSnapshotStrategy.ANY_CHANGE,
                min_gap_seconds=0,
                max_gap_seconds=300,
            )
            mgr = self._make_manager(tmpdir, policy)

            mgr._last_snapshot_time = datetime.now()
            mgr._last_snapshot_spins = 5
            mgr._last_snapshot_balance = 100

            # Spin changed
            self.assertTrue(mgr.should_auto_snapshot({"balance": 100}, 6, 100))
            # Nothing changed
            self.assertFalse(mgr.should_auto_snapshot({"balance": 100}, 5, 100))
            # Balance changed
            self.assertTrue(mgr.should_auto_snapshot({"balance": 105}, 5, 105))


class TestCheckpointManager(unittest.TestCase):
    """Test CheckpointManager core functionality."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir, max_checkpoints=5)

            state = {"balance": 5000, "spin_count": 100, "bet": 100}
            cp = mgr.save("TestGame", "session-1", state)

            self.assertEqual(cp.game_name, "TestGame")
            self.assertEqual(cp.session_id, "session-1")
            self.assertEqual(cp.balance, 5000)
            self.assertEqual(cp.spin_count, 100)
            self.assertFalse(cp.is_incremental)

            loaded = mgr.load(cp.checkpoint_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.checkpoint_id, cp.checkpoint_id)

    def test_load_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir)

            state = {"balance": 5000, "spin_count": 100, "extra": "data"}
            cp = mgr.save("TestGame", "session-1", state)

            loaded_state = mgr.load_state(cp.checkpoint_id)
            self.assertEqual(loaded_state["balance"], 5000)
            self.assertEqual(loaded_state["spin_count"], 100)
            self.assertEqual(loaded_state["extra"], "data")

    def test_incremental_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir, max_checkpoints=5, enable_incremental=True)

            # First save - full checkpoint
            state1 = {"balance": 5000, "spin_count": 0, "unchanged": "value"}
            cp1 = mgr.save("TestGame", "session-1", state1)
            self.assertFalse(cp1.is_incremental)

            # Second save - only balance changed -> incremental
            state2 = {"balance": 4900, "spin_count": 0, "unchanged": "value"}
            cp2 = mgr.save("TestGame", "session-1", state2)
            self.assertTrue(cp2.is_incremental)
            self.assertEqual(cp2.parent_id, cp1.checkpoint_id)

            # Reconstruct state from incremental
            reconstructed = mgr.load_state(cp2.checkpoint_id)
            self.assertEqual(reconstructed["balance"], 4900)
            self.assertEqual(reconstructed["unchanged"], "value")

    def test_list_and_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir, max_checkpoints=20)

            mgr.save("GameA", "s1", {"balance": 100})
            mgr.save("GameA", "s2", {"balance": 200})
            mgr.save("GameB", "s1", {"balance": 300})

            all_a = mgr.list_checkpoints(game_name="GameA")
            self.assertEqual(len(all_a), 2)

            all_s1 = mgr.list_checkpoints(session_id="s1")
            self.assertEqual(len(all_s1), 2)

    def test_pruning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir, max_checkpoints=3)

            for i in range(5):
                mgr.save("Game", "session", {"balance": i * 100})

            # Only latest 3 should remain
            checkpoints = mgr.list_checkpoints()
            self.assertEqual(len(checkpoints), 3)

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir, max_checkpoints=5)

            cp = mgr.save("Game", "session", {"balance": 100})
            self.assertIsNotNone(mgr.load(cp.checkpoint_id))

            self.assertTrue(mgr.delete(cp.checkpoint_id))
            self.assertIsNone(mgr.load(cp.checkpoint_id))
            self.assertFalse(mgr.delete("nonexistent"))

    def test_get_latest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir, max_checkpoints=5)

            cp1 = mgr.save("Game", "session", {"balance": 100})
            time.sleep(0.01)
            cp2 = mgr.save("Game", "session", {"balance": 200})

            latest = mgr.get_latest(game_name="Game")
            self.assertEqual(latest.checkpoint_id, cp2.checkpoint_id)

    def test_get_latest_for_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir, max_checkpoints=5)

            mgr.save("Game", "session-A", {"balance": 100})
            mgr.save("Game", "session-B", {"balance": 200})

            latest_a = mgr.get_latest(session_id="session-A")
            self.assertEqual(latest_a.session_id, "session-A")

            latest_b = mgr.get_latest(session_id="session-B")
            self.assertEqual(latest_b.session_id, "session-B")

    def test_checkpoint_chain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir, max_checkpoints=10, enable_incremental=True)

            cp1 = mgr.save("Game", "session", {"balance": 5000, "spin_count": 0})
            time.sleep(0.01)
            cp2 = mgr.save("Game", "session", {"balance": 4900, "spin_count": 1})
            time.sleep(0.01)
            cp3 = mgr.save("Game", "session", {"balance": 5100, "spin_count": 2})

            chain = mgr.get_checkpoint_chain(cp3.checkpoint_id)
            self.assertEqual(len(chain), 3)
            self.assertEqual(chain[0].checkpoint_id, cp1.checkpoint_id)
            self.assertEqual(chain[-1].checkpoint_id, cp3.checkpoint_id)

    def test_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir)

            cp = mgr.save("Game", "session", {"balance": 5000, "spin_count": 100})

            export_path = Path(tmpdir) / "export.json"
            self.assertTrue(mgr.export(cp.checkpoint_id, export_path))

            with open(export_path) as f:
                data = json.load(f)
            self.assertEqual(data["checkpoint_id"], cp.checkpoint_id)
            self.assertEqual(data["final_state"]["balance"], 5000)

    def test_auto_snapshot_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = AutoSnapshotPolicy(
                strategy=AutoSnapshotStrategy.SPIN_BASED,
                interval=5,
                min_gap_seconds=0,  # Disable min gap so spin-based check fires
            )
            mgr = CheckpointManager(tmpdir, auto_snapshot_policy=policy)

            mgr.save("Game", "session", {"balance": 5000, "spin_count": 0})
            mgr.update_auto_snapshot_tracking(0, 5000)

            # Within threshold
            self.assertFalse(mgr.should_auto_snapshot({"balance": 5000}, 3, 5000))
            # Exceeds threshold
            self.assertTrue(mgr.should_auto_snapshot({"balance": 5000}, 6, 5000))


class TestRollbackManager(unittest.TestCase):
    """Test RollbackManager."""

    def test_rollback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir)
            rollback_mgr = RollbackManager(mgr)

            state1 = {"balance": 5000}
            cp1 = mgr.save("Game", "session", state1)

            rollback_mgr.record_operation("spin", state1, cp1.checkpoint_id)

            state2 = {"balance": 4900}
            cp2 = mgr.save("Game", "session", state2)
            rollback_mgr.record_operation("spin", state2, cp2.checkpoint_id)

            # Rollback one step
            rolled = rollback_mgr.rollback(1)
            self.assertEqual(rolled["balance"], 5000)
            self.assertEqual(rollback_mgr.get_history_size(), 1)

            # Rollback another step
            rolled2 = rollback_mgr.rollback(1)
            self.assertIsNone(rolled2)
            self.assertEqual(rollback_mgr.get_history_size(), 0)

    def test_clear_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir)
            rollback_mgr = RollbackManager(mgr)

            cp = mgr.save("Game", "session", {"balance": 5000})
            rollback_mgr.record_operation("spin", {"balance": 5000}, cp.checkpoint_id)
            rollback_mgr.clear_history()
            self.assertEqual(rollback_mgr.get_history_size(), 0)


class TestConcurrentAccess(unittest.TestCase):
    """Test multi-threaded concurrent access."""

    def test_concurrent_saves(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(tmpdir, max_checkpoints=20)
            errors = []
            saved_ids = []

            def save_thread(game_name, session, balance):
                try:
                    cp = mgr.save(game_name, session, {"balance": balance})
                    saved_ids.append(cp.checkpoint_id)
                except Exception as e:
                    errors.append(str(e))

            threads = []
            for i in range(5):
                t = threading.Thread(
                    target=save_thread,
                    args=(f"Game{i}", f"session-{i}", i * 1000)
                )
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            self.assertEqual(len(errors), 0)
            self.assertEqual(len(saved_ids), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
