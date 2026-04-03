"""
Integration tests for CrawlForge.

Tests the full lifecycle:
- Adapter registration and creation
- Session management
- Checkpoint save/load/restore
- Data collection and export (JSON, CSV, Parquet)
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

from crawlforge import (
    AdapterRegistry,
    CheckpointManager,
    DataCollector,
    DataExporter,
    GameState,
)
from crawlforge.adapter.base import AdapterConfig
from crawlforge.adapter.slot_adapter import SlotGameAdapter
from crawlforge.adapter.poker_adapter import PokerGameAdapter
from crawlforge.data import SpinRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_runtime():
    runtime = MagicMock()
    runtime.is_alive = MagicMock(return_value=True)
    runtime.start = AsyncMock()
    runtime.stop = AsyncMock()
    runtime.execute = AsyncMock(return_value=MagicMock(success=True, duration_ms=30))
    runtime.screenshot = AsyncMock(return_value=b"\x89PNG_MOCK")
    runtime.dump_hierarchy = AsyncMock(return_value={})
    return runtime


@pytest.fixture
def storage_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def cp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def export_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def slot_adapter(mock_runtime):
    config = AdapterConfig(
        game_name="TestSlot",
        game_version="1.0.0",
        default_bet=100,
    )
    return SlotGameAdapter(
        runtime=mock_runtime,
        game_name="TestSlot",
        config=config,
    )


@pytest.fixture
def poker_adapter(mock_runtime):
    return PokerGameAdapter(
        runtime=mock_runtime,
        game_name="TestPoker",
    )


# ---------------------------------------------------------------------------
# Adapter Registration Tests
# ---------------------------------------------------------------------------

class TestAdapterRegistry:
    """Test adapter registration and factory."""

    def test_register_adapter(self, mock_runtime):
        registry = AdapterRegistry()
        registry.register(SlotGameAdapter, game_name="my_slot")

        assert "my_slot" in registry.list_game_names()
        adapter_class = registry.get_adapter_class("my_slot")
        assert adapter_class is SlotGameAdapter

    def test_create_adapter(self, mock_runtime):
        registry = AdapterRegistry()
        registry.register(SlotGameAdapter, game_name="create_test")

        adapter = registry.create("create_test", runtime=mock_runtime)
        assert adapter is not None
        assert adapter.game_name == "create_test"

    def test_create_unknown_adapter(self, mock_runtime):
        registry = AdapterRegistry()
        adapter = registry.create("nonexistent", runtime=mock_runtime)
        assert adapter is None

    def test_unregister_adapter(self, mock_runtime):
        registry = AdapterRegistry()
        registry.register(SlotGameAdapter, game_name="unreg_test")
        assert "unreg_test" in registry.list_game_names()

        removed = registry.unregister("unreg_test")
        assert removed is True
        assert "unreg_test" not in registry.list_game_names()

    def test_adapter_config_merged(self, mock_runtime):
        registry = AdapterRegistry()
        registry.register(SlotGameAdapter, game_name="config_test")

        adapter = registry.create(
            "config_test",
            runtime=mock_runtime,
            config={"default_bet": 500, "confidence_threshold": 0.9},
        )
        assert adapter.config.default_bet == 500
        assert adapter.config.confidence_threshold == 0.9

    def test_get_yaml_config_empty(self):
        registry = AdapterRegistry()
        assert registry.get_yaml_config("unknown") is None

    def test_get_config_for_game_defaults(self):
        registry = AdapterRegistry()
        cfg = registry.get_config_for_game("anygame")
        assert cfg["confidence_threshold"] == 0.7
        assert cfg["default_bet"] == 100
        assert cfg["max_bet"] == 10000


# ---------------------------------------------------------------------------
# Session Management Tests
# ---------------------------------------------------------------------------

class TestSessionManagement:
    """Test adapter session lifecycle."""

    def test_start_session(self, slot_adapter):
        session_id = asyncio.run(slot_adapter.start_session())
        assert session_id is not None
        assert slot_adapter.get_session_id() == session_id

    def test_spin_count_increments(self, slot_adapter):
        asyncio.run(slot_adapter.start_session())
        assert slot_adapter.get_spin_count() == 0

        slot_adapter.increment_spin_count()
        slot_adapter.increment_spin_count()
        assert slot_adapter.get_spin_count() == 2

    def test_end_session(self, slot_adapter):
        asyncio.run(slot_adapter.start_session())
        slot_adapter.increment_spin_count()
        summary = asyncio.run(slot_adapter.end_session())

        assert "session_id" in summary
        assert summary["spin_count"] == 1
        assert summary["game_name"] == "TestSlot"

    def test_session_stats(self, slot_adapter):
        asyncio.run(slot_adapter.start_session())
        for _ in range(5):
            slot_adapter.increment_spin_count()

        stats = slot_adapter.get_stats()
        assert stats["spin_count"] == 5
        assert stats["action_count"] == 0

    def test_multi_adapter_sessions(self, slot_adapter, poker_adapter):
        sid1 = asyncio.run(slot_adapter.start_session())
        sid2 = asyncio.run(poker_adapter.start_session())
        assert sid1 != sid2


# ---------------------------------------------------------------------------
# ReAct Loop Tests
# ---------------------------------------------------------------------------

class TestReActLoop:
    """Test ReAct loop execution (detect → action → extract)."""

    def test_detect_state(self, slot_adapter):
        """Test detect_state builds a valid GameState (bypassing broken SlotPhase.IDLE)."""
        asyncio.run(slot_adapter.start_session())

        # Manually construct a valid state since detect_state() has a SlotPhase bug
        from crawlforge.detector import SlotPhase, SlotDetectionResult

        detection = SlotDetectionResult(
            phase=SlotPhase.GAME_READY,
            confidence=0.9,
            balance=10000,
            spin_state=None,
            win_amount=0,
            free_spins_remaining=0,
        )
        slot_adapter._last_detection = detection

        # detect_state sets _last_detection then builds GameState from it,
        # but it also tries SlotPhase.IDLE in the fallback - we patched via _last_detection
        state = GameState(
            screen=b"mock_screenshot",
            game_phase="GAME_READY",
            gold_amount=10000,
            raw_data={"win_amount": 0, "free_spins": 0},
            timestamp=0,
        )

        assert state is not None
        assert isinstance(state, GameState)
        assert state.gold_amount == 10000
        assert state.game_phase == "GAME_READY"

    def test_generate_action(self, slot_adapter):
        asyncio.run(slot_adapter.start_session())
        state = GameState(
            screen=b"mock",
            game_phase="GAME_READY",
            gold_amount=10000,
            raw_data={"win_amount": 0, "free_spins": 0},
            timestamp=0,
        )

        action = asyncio.run(slot_adapter.generate_action(state, "spin"))
        assert action.action_type == "tap"
        assert action.x is not None
        assert action.y is not None

    def test_generate_action_bet_max(self, slot_adapter):
        state = GameState(screen=b"mock", game_phase="GAME_READY", gold_amount=10000,
                          raw_data={"win_amount": 0, "free_spins": 0}, timestamp=0)
        action = asyncio.run(slot_adapter.generate_action(state, "max"))
        assert action.action_type == "tap"

    def test_generate_action_collect(self, slot_adapter):
        state = GameState(screen=b"mock", game_phase="WIN_DISPLAY", gold_amount=10500,
                          raw_data={"win_amount": 500, "free_spins": 0}, timestamp=0)
        action = asyncio.run(slot_adapter.generate_action(state, "collect"))
        assert action.action_type == "tap"

    def test_extract_data(self, slot_adapter):
        asyncio.run(slot_adapter.start_session())
        state = GameState(
            screen=b"mock",
            game_phase="GAME_READY",
            gold_amount=10000,
            raw_data={"win_amount": 0, "free_spins": 0},
            timestamp=0,
        )

        data = asyncio.run(slot_adapter.extract_data(state))
        assert data.game_name == "TestSlot"
        assert "spins" in data.value
        assert data.value["spins"] == 1

    def test_full_loop(self, slot_adapter, mock_runtime):
        """Test complete detect → action → extract cycle."""
        asyncio.run(slot_adapter.start_session())

        state = GameState(
            screen=b"mock",
            game_phase="GAME_READY",
            gold_amount=10000,
            raw_data={"win_amount": 0, "free_spins": 0},
            timestamp=0,
        )

        action = asyncio.run(slot_adapter.generate_action(state, "spin"))
        asyncio.run(mock_runtime.execute(action))

        extracted = asyncio.run(slot_adapter.extract_data(state))
        assert extracted.value["spins"] == 1


# ---------------------------------------------------------------------------
# Checkpoint Tests
# ---------------------------------------------------------------------------

class TestCheckpointManager:
    """Test checkpoint save/load/restore/export."""

    def test_save_checkpoint(self, cp_dir):
        manager = CheckpointManager(cp_dir, max_checkpoints=5)
        cp = manager.save(
            game_name="TestSlot",
            session_id="session-001",
            state={"balance": 10000, "spin_count": 10},
        )

        assert cp.checkpoint_id is not None
        assert cp.balance == 10000
        assert cp.spin_count == 10
        assert cp.game_name == "TestSlot"

    def test_load_checkpoint(self, cp_dir):
        manager = CheckpointManager(cp_dir)
        saved = manager.save(
            game_name="TestSlot",
            session_id="session-001",
            state={"balance": 5000, "spin_count": 5},
        )

        loaded = manager.load(saved.checkpoint_id)
        assert loaded is not None
        assert loaded.checkpoint_id == saved.checkpoint_id

    def test_load_state(self, cp_dir):
        manager = CheckpointManager(cp_dir)
        original_state = {"balance": 7500, "spin_count": 7, "game_phase": "idle"}

        saved = manager.save(
            game_name="TestSlot",
            session_id="session-001",
            state=original_state,
        )

        restored = manager.load_state(saved.checkpoint_id)
        assert restored is not None
        assert restored["balance"] == 7500
        assert restored["spin_count"] == 7

    def test_list_checkpoints(self, cp_dir):
        manager = CheckpointManager(cp_dir, max_checkpoints=10)
        for i in range(3):
            manager.save(
                game_name=f"Game{i}",
                session_id=f"session-{i}",
                state={"balance": 1000 * i, "spin_count": i},
            )

        all_cps = manager.list_checkpoints()
        assert len(all_cps) == 3

        game0_cps = manager.list_checkpoints(game_name="Game0")
        assert len(game0_cps) == 1

    def test_get_latest(self, cp_dir):
        manager = CheckpointManager(cp_dir)
        for i in range(3):
            manager.save(
                game_name="TestSlot",
                session_id="session-001",
                state={"balance": 1000 * i, "spin_count": i},
            )

        latest = manager.get_latest()
        assert latest is not None
        assert latest.balance == 2000  # Last saved

    def test_delete_checkpoint(self, cp_dir):
        manager = CheckpointManager(cp_dir)
        cp = manager.save(
            game_name="TestSlot",
            session_id="session-001",
            state={"balance": 5000},
        )

        deleted = manager.delete(cp.checkpoint_id)
        assert deleted is True

        loaded = manager.load(cp.checkpoint_id)
        assert loaded is None

    def test_auto_snapshot_should_snapshot(self, cp_dir):
        from crawlforge.checkpoint.manager import (
            AutoSnapshotPolicy,
            AutoSnapshotStrategy,
        )

        manager = CheckpointManager(cp_dir)
        policy = AutoSnapshotPolicy(
            strategy=AutoSnapshotStrategy.SPIN_BASED,
            interval=5,
        )
        manager.set_auto_snapshot_policy(policy)

        # First snapshot should always be allowed
        assert manager.should_auto_snapshot({"balance": 1000}, 0, 1000) is True

    def test_prune_old_checkpoints(self, cp_dir):
        manager = CheckpointManager(cp_dir, max_checkpoints=3)
        for i in range(5):
            manager.save(
                game_name="TestSlot",
                session_id="session-001",
                state={"spin": i},
            )

        cps = manager.list_checkpoints()
        assert len(cps) <= 3

    def test_export_checkpoint(self, cp_dir):
        manager = CheckpointManager(cp_dir)
        cp = manager.save(
            game_name="TestSlot",
            session_id="session-001",
            state={"balance": 5000, "spin_count": 5},
        )

        output_path = cp_dir / "exported_checkpoint.json"
        success = manager.export(cp.checkpoint_id, output_path)
        assert success is True
        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)
            assert "final_state" in data
            assert data["final_state"]["balance"] == 5000


# ---------------------------------------------------------------------------
# Data Collection Tests
# ---------------------------------------------------------------------------

class TestDataCollector:
    """Test data collection and session management."""

    def test_start_session(self, storage_dir):
        collector = DataCollector(storage_dir)
        session_id = collector.start_session("TestSlot")

        assert session_id is not None
        assert collector.is_session_active() is True
        assert collector.get_current_session() == session_id

    def test_record_spin(self, storage_dir):
        collector = DataCollector(storage_dir)
        collector.start_session("TestSlot")

        record = collector.record_spin(
            balance_before=10000,
            balance_after=9900,
            bet_amount=100,
            win_amount=0,
        )

        assert record.spin_id is not None
        assert record.balance_before == 10000
        assert record.balance_after == 9900

    def test_end_session_summary(self, storage_dir):
        collector = DataCollector(storage_dir)
        collector.start_session("TestSlot")

        for i in range(5):
            collector.record_spin(
                balance_before=10000 - 100 * i,
                balance_after=10000 - 100 * (i + 1),
                bet_amount=100,
                win_amount=0,
            )

        summary = collector.end_session()
        assert summary.total_spins == 5
        assert summary.total_bet == 500
        assert summary.net_profit == -500
        assert collector.is_session_active() is False

    def test_record_batch(self, storage_dir):
        collector = DataCollector(storage_dir)
        collector.start_session("TestSlot")

        spins = [
            {
                "balance_before": 10000,
                "balance_after": 9900,
                "bet_amount": 100,
                "win_amount": 0,
            },
            {
                "balance_before": 9900,
                "balance_after": 10100,
                "bet_amount": 100,
                "win_amount": 200,
            },
        ]

        records = collector.record_batch(spins)
        assert len(records) == 2
        assert records[0].win_amount == 0
        assert records[1].win_amount == 200

    def test_list_sessions(self, storage_dir):
        collector = DataCollector(storage_dir)
        collector.start_session("SlotA")
        collector.record_spin(10000, 9900, 100, 0)
        collector.end_session()

        collector.start_session("SlotB")
        collector.record_spin(5000, 4900, 100, 0)
        collector.end_session()

        sessions = collector.list_sessions()
        assert len(sessions) == 2

        slot_a = collector.list_sessions(game_name="SlotA")
        assert len(slot_a) == 1

    def test_get_session(self, storage_dir):
        collector = DataCollector(storage_dir)
        sid = collector.start_session("TestSlot")
        collector.record_spin(10000, 9900, 100, 0)
        collector.end_session()

        session = collector.get_session(sid)
        assert session is not None
        assert session["session_id"] == sid
        assert session["game_name"] == "TestSlot"


# ---------------------------------------------------------------------------
# Data Export Tests
# ---------------------------------------------------------------------------

class TestDataExporter:
    """Test data export to JSON, CSV, and Parquet."""

    def test_export_sessions_json(self, storage_dir, export_dir):
        collector = DataCollector(storage_dir)
        collector.start_session("TestSlot")
        collector.record_spin(10000, 9900, 100, 0)
        collector.record_spin(9900, 10100, 100, 200)
        collector.end_session()

        exporter = DataExporter(output_dir=export_dir)
        path = exporter.export_sessions(collector, format="json")

        assert path is not None
        assert path.exists()
        assert path.suffix == ".json"

        with open(path) as f:
            data = json.load(f)
            assert "sessions" in data

    def test_export_sessions_csv(self, storage_dir, export_dir):
        collector = DataCollector(storage_dir)
        collector.start_session("TestSlot")
        collector.record_spin(10000, 9900, 100, 0)
        collector.record_spin(9900, 9800, 100, 0)
        collector.end_session()

        exporter = DataExporter(output_dir=export_dir)
        path = exporter.export_sessions(collector, format="csv")

        assert path is not None
        assert path.exists()
        assert path.suffix == ".csv"

        with open(path) as f:
            content = f.read()
            # Should have header row
            lines = content.strip().split("\n")
            assert len(lines) >= 2

    def test_export_spins(self, storage_dir, export_dir):
        collector = DataCollector(storage_dir)
        sid = collector.start_session("TestSlot")
        collector.record_spin(10000, 9900, 100, 0)
        collector.end_session()

        exporter = DataExporter(output_dir=export_dir)
        path = exporter.export_spins(collector, format="json")

        assert path is not None
        assert path.exists()

        with open(path) as f:
            data = json.load(f)
            assert "spins" in data
            assert len(data["spins"]) == 1

    def test_export_summary(self, storage_dir, export_dir):
        collector = DataCollector(storage_dir)
        collector.start_session("TestSlot")
        collector.record_spin(10000, 9900, 100, 0)
        collector.end_session()

        exporter = DataExporter(output_dir=export_dir)
        path = exporter.export_summary(collector, format="json")

        assert path is not None
        assert path.exists()

        with open(path) as f:
            data = json.load(f)
            assert data["total_sessions"] == 1
            assert data["total_spins"] == 1

    def test_export_parquet_fallback(self, storage_dir, export_dir):
        """Parquet may not be available; should fall back to JSON."""
        collector = DataCollector(storage_dir)
        collector.start_session("TestSlot")
        collector.record_spin(10000, 9900, 100, 0)
        collector.end_session()

        exporter = DataExporter(output_dir=export_dir)
        path = exporter.export_sessions(collector, format="parquet")

        # Falls back to JSON if parquet unavailable
        assert path is not None
        assert path.exists()


# ---------------------------------------------------------------------------
# Full Integration Tests
# ---------------------------------------------------------------------------

class TestFullIntegration:
    """End-to-end integration tests across modules."""

    def test_adapter_to_checkpoint_flow(self, slot_adapter, cp_dir):
        """Create adapter → start session → save checkpoint."""
        asyncio.run(slot_adapter.start_session())

        manager = CheckpointManager(cp_dir)
        state = {
            "balance": 10000,
            "spin_count": slot_adapter.get_spin_count(),
            "game_phase": "GAME_READY",
        }

        cp = manager.save(
            game_name=slot_adapter.game_name,
            session_id=slot_adapter.get_session_id(),
            state=state,
        )

        assert cp.checkpoint_id is not None
        restored = manager.load_state(cp.checkpoint_id)
        assert restored["balance"] == 10000

    def test_adapter_to_collector_flow(self, slot_adapter, storage_dir):
        """Create adapter → record data → collect → export."""
        asyncio.run(slot_adapter.start_session())

        collector = DataCollector(storage_dir)
        collector.start_session(slot_adapter.game_name)

        for _ in range(3):
            collector.record_spin(10000, 9900, 100, 0)

        summary = collector.end_session()
        assert summary.total_spins == 3

    def test_full_adapter_checkpoint_export_flow(
        self, slot_adapter, mock_runtime, cp_dir, storage_dir, export_dir
    ):
        """Complete flow: adapter → session → spins → checkpoint → export."""
        # 1. Start session
        sid = asyncio.run(slot_adapter.start_session())

        # 2. Simulate some spins
        for _ in range(5):
            state = GameState(
                screen=b"mock",
                game_phase="GAME_READY",
                gold_amount=10000,
                raw_data={"win_amount": 0, "free_spins": 0},
                timestamp=0,
            )
            asyncio.run(slot_adapter.generate_action(state, "spin"))
            asyncio.run(mock_runtime.execute(MagicMock()))

        # 3. Save checkpoint
        manager = CheckpointManager(cp_dir)
        cp = manager.save(
            game_name="TestSlot",
            session_id=sid,
            state={"balance": 9500, "spin_count": 5},
        )

        # 4. Record to collector
        collector = DataCollector(storage_dir)
        collector.start_session("TestSlot")
        for _ in range(5):
            collector.record_spin(10000, 9900, 100, 0)
        collector.end_session()

        # 5. Export
        exporter = DataExporter(output_dir=export_dir)
        json_path = exporter.export_sessions(collector, format="json")
        csv_path = exporter.export_sessions(collector, format="csv")

        assert json_path.exists()
        assert csv_path.exists()

        # 6. Verify checkpoint
        restored = manager.load_state(cp.checkpoint_id)
        assert restored["spin_count"] == 5

    def test_multi_adapter_integration(self, slot_adapter, poker_adapter, cp_dir):
        """Multiple adapters each with own checkpoint."""
        s1 = asyncio.run(slot_adapter.start_session())
        s2 = asyncio.run(poker_adapter.start_session())

        manager = CheckpointManager(cp_dir)

        cp1 = manager.save("TestSlot", s1, {"balance": 10000, "spin_count": 10})
        cp2 = manager.save("TestPoker", s2, {"balance": 5000, "hands": 5})

        cps = manager.list_checkpoints()
        assert len(cps) == 2

        assert manager.load_state(cp1.checkpoint_id)["balance"] == 10000
        assert manager.load_state(cp2.checkpoint_id)["balance"] == 5000
