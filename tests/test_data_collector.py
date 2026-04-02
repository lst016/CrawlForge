"""
Tests for DataCollector.
"""

import pytest
import tempfile
from pathlib import Path
from crawlforge.data import DataCollector, AlgorithmAnalyzer


def test_data_collector_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = DataCollector(Path(tmpdir))
        session_id = collector.start_session("TestSlot", {"version": "1.0"})

        assert session_id is not None
        assert collector._current_session == session_id


def test_data_collector_record_spin():
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = DataCollector(Path(tmpdir))
        collector.start_session("TestSlot")

        record = collector.record_spin(
            balance_before=5000,
            balance_after=5100,
            bet_amount=100,
            win_amount=200,
            is_free_spin=False,
        )

        assert record.win_amount == 200
        assert len(collector._spins) == 1


def test_data_collector_end_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = DataCollector(Path(tmpdir))
        collector.start_session("TestSlot")

        collector.record_spin(5000, 5100, 100, 200)
        collector.record_spin(5100, 5000, 100, 0)
        collector.record_spin(5000, 5200, 100, 300)

        summary = collector.end_session()

        assert summary.total_spins == 3
        assert summary.total_bet == 300
        assert summary.total_wins == 500
        assert summary.net_profit == 200  # 500 - 300


def test_data_collector_list_sessions():
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = DataCollector(Path(tmpdir))

        collector.start_session("GameA")
        collector.end_session()

        collector.start_session("GameB")
        collector.end_session()

        sessions = collector.list_sessions()
        assert len(sessions) == 2


def test_algorithm_analyzer():
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = DataCollector(Path(tmpdir))
        analyzer = AlgorithmAnalyzer(collector)

        collector.start_session("TestSlot")
        collector.record_spin(5000, 5100, 100, 200)
        collector.record_spin(5100, 5000, 100, 0)
        collector.record_spin(5000, 5500, 100, 600)
        summary = collector.end_session()

        insights = analyzer.analyze_session(summary.session_id)
        assert len(insights) >= 1
