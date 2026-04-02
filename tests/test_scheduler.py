"""
Tests for Multi-Game Scheduler.
"""

import pytest
from crawlforge.scheduler import (
    ScheduleStrategy, ResourceGate, GameSession, SessionPool,
)


def test_game_session_properties():
    session = GameSession(
        session_id="test-1",
        game_name="TestSlot",
        adapter=None,
        runtime=None,
        max_spins=100,
        spins_done=25,
    )
    assert session.is_active is False  # status is "pending"
    assert session.progress == 0.25


def test_game_session_unlimited_spins():
    session = GameSession(
        session_id="test-1",
        game_name="TestSlot",
        adapter=None,
        runtime=None,
        max_spins=0,
        spins_done=50,
    )
    assert session.progress == 0.0  # max=0 means progress=0


def test_resource_gate_defaults():
    gate = ResourceGate()
    assert gate.max_concurrent == 1
    assert gate.max_cpu_percent == 80.0
    assert gate.device_slots == 1


def test_session_pool_add():
    pool = SessionPool()
    session_id = pool.add_session(
        game_name="GameA",
        adapter=None,
        runtime=None,
        priority=5,
    )
    assert session_id is not None
    assert pool.get_session(session_id) is not None
    assert pool.get_session(session_id).priority == 5


def test_session_pool_remove():
    pool = SessionPool()
    session_id = pool.add_session("GameA", None, None)
    assert pool.remove_session(session_id) is True
    assert pool.get_session(session_id) is None


def test_session_pool_list():
    pool = SessionPool()
    pool.add_session("GameA", None, None)
    pool.add_session("GameB", None, None)
    pool.add_session("GameC", None, None)

    all_sessions = pool.list_sessions()
    assert len(all_sessions) == 3

    running = pool.list_sessions(status="running")
    assert len(running) == 0


def test_session_pool_stats():
    pool = SessionPool()
    pool.add_session("GameA", None, None)
    pool.add_session("GameB", None, None)

    stats = pool.get_stats()
    assert stats["total"] == 2
    assert stats["strategy"] == "round_robin"


def test_schedule_strategy_enum():
    assert ScheduleStrategy.ROUND_ROBIN.value == "round_robin"
    assert ScheduleStrategy.PRIORITY.value == "priority"
    assert ScheduleStrategy.LEAST_LOADED.value == "least_loaded"
