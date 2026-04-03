"""
Tests for DataCollector.
"""

import csv
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime
import unittest

from crawlforge.data import (
    DataCollector, BatchCollector, AlgorithmAnalyzer,
    SpinRecord, SessionSummary, AlgorithmInsight,
    DataExporter, SchemaValidator,
)


class TestDataCollector(unittest.TestCase):
    """Test DataCollector core functionality."""

    def test_start_end_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)

            sid = collector.start_session("TestGame")
            self.assertIsNotNone(sid)
            self.assertTrue(collector.is_session_active())
            self.assertEqual(collector.get_current_session(), sid)

            summary = collector.end_session()
            self.assertEqual(summary.game_name, "TestGame")
            self.assertEqual(summary.total_spins, 0)
            self.assertFalse(collector.is_session_active())

    def test_record_spin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)

            collector.start_session("TestGame")

            # Record spins
            collector.record_spin(5000, 4900, 100, 0)           # Loss
            collector.record_spin(4900, 5050, 100, 150)        # Win
            collector.record_spin(5050, 4950, 100, 0, is_free_spin=True)  # Free spin loss

            summary = collector.end_session()
            self.assertEqual(summary.total_spins, 3)
            self.assertEqual(summary.total_bet, 300)
            self.assertEqual(summary.total_wins, 150)
            self.assertEqual(summary.net_profit, -150)
            self.assertEqual(summary.free_spins_triggered, 1)

    def test_record_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)

            collector.start_session("TestGame")

            spins = [
                {"balance_before": 5000, "balance_after": 4900, "bet_amount": 100, "win_amount": 0},
                {"balance_before": 4900, "balance_after": 5050, "bet_amount": 100, "win_amount": 150},
            ]
            collector.record_batch(spins)

            summary = collector.end_session()
            self.assertEqual(summary.total_spins, 2)

    def test_reel_positions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)
            collector.start_session("TestGame")

            collector.record_spin(
                5000, 5050, 100, 50,
                reel_positions=[1, 3, 5, 2, 4],
                metadata={"bonus_triggered": False},
            )

            sid = collector.get_current_session()
            collector.end_session()

            spins = collector.get_spins(sid)
            self.assertEqual(len(spins), 1)
            self.assertEqual(spins[0].reel_positions, [1, 3, 5, 2, 4])

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)

            collector.start_session("GameA")
            collector.end_session()
            time.sleep(0.01)

            collector.start_session("GameB")
            collector.end_session()

            sessions = collector.list_sessions()
            self.assertEqual(len(sessions), 2)

            sessions_a = collector.list_sessions(game_name="GameA")
            self.assertEqual(len(sessions_a), 1)
            self.assertEqual(sessions_a[0]["game_name"], "GameA")

    def test_get_session_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)
            collector.start_session("TestGame")
            collector.record_spin(5000, 4900, 100, 0)
            collector.record_spin(4900, 5050, 100, 150)
            sid = collector.get_current_session()
            summary = collector.end_session()
            self.assertEqual(summary.session_id, sid)

            stats = collector.get_session_stats(sid)
            self.assertEqual(stats["total_spins"], 2)

    def test_auto_end_on_start(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)

            sid1 = collector.start_session("Game1")
            collector.record_spin(5000, 4900, 100, 0)
            sid2 = collector.start_session("Game2")  # Should auto-end Game1

            # Session 1 should have been auto-ended
            session1 = collector.get_session(sid1)
            self.assertEqual(session1["status"], "completed")


class TestBatchCollector(unittest.TestCase):
    """Test BatchCollector."""

    def test_add_and_flush(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)
            batch = BatchCollector(collector)

            batch.add_spin("s1", {"balance_before": 5000, "balance_after": 4900, "bet_amount": 100, "win_amount": 0})
            batch.add_spin("s2", {"balance_before": 3000, "balance_after": 2900, "bet_amount": 100, "win_amount": 0})

            self.assertEqual(batch.pending_count(), 2)

            flushed = batch.flush()
            self.assertEqual(flushed.get("s1"), 1)
            self.assertEqual(flushed.get("s2"), 1)
            self.assertEqual(batch.pending_count(), 0)

    def test_auto_flush_by_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)
            batch = BatchCollector(collector, flush_interval=3)

            for i in range(5):
                batch.add_spin("s1", {"balance_before": 5000, "balance_after": 4900, "bet_amount": 100, "win_amount": 0})

            # Should have auto-flushed after 3, leaving 2 in buffer
            # (4th spin triggers flush at exactly 3, leaving 1; 5th adds 1 = 2)
            self.assertEqual(batch.pending_count(), 2)


class TestAlgorithmAnalyzer(unittest.TestCase):
    """Test AlgorithmAnalyzer."""

    def test_analyze_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)
            analyzer = AlgorithmAnalyzer(collector)

            # Session 1: 20 losses + 1 big win
            collector.start_session("TestGame")
            for _ in range(20):
                collector.record_spin(5000, 4900, 100, 0)
            collector.record_spin(4900, 5500, 100, 700)
            summary = collector.end_session()
            sid = summary.session_id

            insights = analyzer.analyze_session(sid)
            self.assertGreater(len(insights), 0)
            types = {i.insight_type for i in insights}
            self.assertIn("pattern", types)


class TestSchemaValidator(unittest.TestCase):
    """Test SchemaValidator."""

    def test_validate_valid(self):
        validator = SchemaValidator()
        validator.register("spin", {
            "balance_before": float,
            "balance_after": float,
            "bet_amount": float,
            "win_amount": float,
        })

        result = validator.validate("spin", {
            "balance_before": 5000.0,
            "balance_after": 4900.0,
            "bet_amount": 100.0,
            "win_amount": 0.0,
        })
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_validate_missing_field(self):
        validator = SchemaValidator()
        validator.register("spin", {
            "balance_before": float,
            "balance_after": float,
        })

        result = validator.validate("spin", {
            "balance_before": 5000.0,
        })
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)


class TestDataExporter(unittest.TestCase):
    """Test DataExporter."""

    def test_export_sessions_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)
            collector.start_session("TestGame")
            collector.record_spin(5000, 4900, 100, 0)
            collector.end_session()

            exporter = DataExporter(Path(tmpdir) / "exports")
            out = exporter.export_sessions(collector, format="json")

            self.assertIsNotNone(out)
            self.assertTrue(out.exists())

            with open(out) as f:
                data = json.load(f)
            self.assertIn("sessions", data)

    def test_export_spins_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)
            collector.start_session("TestGame")
            collector.record_spin(5000, 4900, 100, 0)
            collector.record_spin(4900, 5050, 100, 150)
            collector.end_session()

            exporter = DataExporter(Path(tmpdir) / "exports")
            out = exporter.export_spins(collector, format="csv")

            self.assertIsNotNone(out)
            self.assertTrue(out.exists())

            with open(out) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 2)

    def test_export_compressed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)
            collector.start_session("TestGame")
            collector.record_spin(5000, 4900, 100, 0)
            collector.end_session()

            exporter = DataExporter(Path(tmpdir) / "exports")
            out = exporter.export_sessions(collector, format="json", compress=True)

            self.assertTrue(str(out).endswith(".json.gz"))

    def test_export_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = DataCollector(tmpdir)
            collector.start_session("TestGame")
            collector.record_spin(5000, 4900, 100, 0)
            collector.end_session()

            exporter = DataExporter(Path(tmpdir) / "exports")
            out = exporter.export_summary(collector)

            self.assertIsNotNone(out)
            with open(out) as f:
                data = json.load(f)
            self.assertEqual(data["total_sessions"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
