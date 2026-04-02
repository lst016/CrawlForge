"""
Multi-Game Scheduler - orchestrates multiple game sessions in parallel.

Provides:
- Session pool management
- Resource-based scheduling (CPU, memory, device limits)
- Round-robin and priority scheduling
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from enum import Enum


class ScheduleStrategy(Enum):
    """Scheduling strategies."""
    ROUND_ROBIN = "round_robin"
    PRIORITY = "priority"
    LEAST_LOADED = "least_loaded"
    TIME_SLICE = "time_slice"


@dataclass
class GameSession:
    """A game session."""
    session_id: str
    game_name: str
    adapter: Any  # GameAdapter
    runtime: Any  # Runtime
    status: str = "pending"  # pending, running, paused, completed, error
    priority: int = 1  # 1-10, higher = more priority
    max_spins: int = 0  # 0 = unlimited
    spins_done: int = 0
    started_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status == "running"

    @property
    def progress(self) -> float:
        if self.max_spins <= 0:
            return 0.0
        return min(1.0, self.spins_done / self.max_spins)


@dataclass
class ResourceGate:
    """Controls resource allocation per session."""
    max_concurrent: int = 1  # Max concurrent sessions
    max_cpu_percent: float = 80.0
    max_memory_mb: float = 1024.0
    device_slots: int = 1  # ADB device slots


@dataclass
class ScheduleResult:
    """Result of a scheduling decision."""
    session_id: str
    decision: str  # "run", "wait", "pause", "stop"
    reason: str
    wait_seconds: float = 0.0


class SessionPool:
    """
    Manages a pool of game sessions.

    Usage:
        pool = SessionPool(resource_gate=ResourceGate(max_concurrent=2))
        pool.add_session(adapter_a, runtime_a, game_name="GameA")
        pool.add_session(adapter_b, runtime_b, game_name="GameB")
        await pool.run_all()
    """

    def __init__(
        self,
        resource_gate: Optional[ResourceGate] = None,
        strategy: ScheduleStrategy = ScheduleStrategy.ROUND_ROBIN,
    ):
        self.resource_gate = resource_gate or ResourceGate()
        self.strategy = strategy
        self._sessions: dict[str, GameSession] = {}
        self._active_count: int = 0
        self._running = False
        self._lock = asyncio.Lock()

    def add_session(
        self,
        game_name: str,
        adapter: Any,
        runtime: Any,
        priority: int = 1,
        max_spins: int = 0,
        metadata: Optional[dict] = None,
    ) -> str:
        """Add a session to the pool."""
        session_id = str(uuid.uuid4())[:12]
        session = GameSession(
            session_id=session_id,
            game_name=game_name,
            adapter=adapter,
            runtime=runtime,
            priority=priority,
            max_spins=max_spins,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        return session_id

    def remove_session(self, session_id: str) -> bool:
        """Remove a session."""
        return self._sessions.pop(session_id, None) is not None

    def get_session(self, session_id: str) -> Optional[GameSession]:
        return self._sessions.get(session_id)

    def list_sessions(self, status: Optional[str] = None) -> list[GameSession]:
        sessions = list(self._sessions.values())
        if status:
            sessions = [s for s in sessions if s.status == status]
        return sessions

    async def run_all(self, goal: str = "spin", interval_seconds: float = 30.0) -> dict:
        """
        Run all sessions according to scheduling strategy.

        Args:
            goal: The goal for each session (e.g., "spin 100 times")
            interval_seconds: How often to switch between sessions

        Returns:
            Summary of execution
        """
        self._running = True
        start_time = time.monotonic()
        results = {}

        while self._running and self._sessions:
            # Select next session to run
            session = self._select_session()
            if session is None:
                await asyncio.sleep(1.0)
                continue

            # Run one cycle
            try:
                await self._run_session_cycle(session, goal)
                results[session.session_id] = {"status": "ok", "spins": session.spins_done}
            except Exception as e:
                session.status = "error"
                session.error = str(e)
                results[session.session_id] = {"status": "error", "error": str(e)}

            # Check if all sessions are done
            active = [s for s in self._sessions.values() if s.status == "running"]
            if not active:
                break

            await asyncio.sleep(interval_seconds)

        elapsed = time.monotonic() - start_time
        return {
            "sessions": results,
            "total_duration": elapsed,
            "sessions_run": len(results),
        }

    def _select_session(self) -> Optional[GameSession]:
        """Select the next session based on strategy."""
        candidates = [s for s in self._sessions.values() if s.status in ("pending", "running")]

        if not candidates:
            return None

        if self.strategy == ScheduleStrategy.PRIORITY:
            return max(candidates, key=lambda s: s.priority)
        elif self.strategy == ScheduleStrategy.ROUND_ROBIN:
            running = [s for s in candidates if s.status == "running"]
            pending = [s for s in candidates if s.status == "pending"]
            if pending:
                return pending[0]
            if running:
                # Round-robin through running sessions
                last_active = min(running, key=lambda s: s.last_active or datetime.min)
                return last_active
        elif self.strategy == ScheduleStrategy.LEAST_LOADED:
            return min(candidates, key=lambda s: s.spins_done)

        return candidates[0]

    async def _run_session_cycle(self, session: GameSession, goal: str) -> None:
        """Run one cycle for a session."""
        if session.status != "running":
            if self._active_count >= self.resource_gate.max_concurrent:
                return  # Resource limit reached
            session.status = "running"
            session.started_at = datetime.now()
            self._active_count += 1

        session.last_active = datetime.now()

        # Check spin limit
        if session.max_spins > 0 and session.spins_done >= session.max_spins:
            session.status = "completed"
            self._active_count -= 1
            return

        # Execute one spin
        try:
            screenshot = await session.runtime.screenshot()
            action = await session.adapter.generate_action(None, goal)
            result = await session.runtime.execute(action)

            if result.success:
                session.spins_done += 1
            else:
                # Log but continue
                pass
        except Exception as e:
            session.status = "error"
            session.error = str(e)
            self._active_count -= 1
            raise

    def pause(self, session_id: str) -> bool:
        """Pause a session."""
        session = self._sessions.get(session_id)
        if session and session.status == "running":
            session.status = "paused"
            self._active_count -= 1
            return True
        return False

    def resume(self, session_id: str) -> bool:
        """Resume a paused session."""
        session = self._sessions.get(session_id)
        if session and session.status == "paused":
            session.status = "pending"
            return True
        return False

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False

    def get_stats(self) -> dict:
        """Get pool statistics."""
        sessions = list(self._sessions.values())
        return {
            "total": len(sessions),
            "running": sum(1 for s in sessions if s.status == "running"),
            "paused": sum(1 for s in sessions if s.status == "paused"),
            "completed": sum(1 for s in sessions if s.status == "completed"),
            "error": sum(1 for s in sessions if s.status == "error"),
            "total_spins": sum(s.spins_done for s in sessions),
            "strategy": self.strategy.value,
        }
