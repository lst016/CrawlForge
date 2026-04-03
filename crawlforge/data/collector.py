"""
Data Collector - collects, analyzes, and stores game data.

Provides:
- Session recording (start/end, spin tracking)
- Batch collection (multiple games/sessions at once)
- Schema validation
- Statistical reporting
- Algorithm analysis
"""

import json
import time
import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Union

from .exporter import DataExporter, SchemaValidator


@dataclass
class SpinRecord:
    """Record of a single spin."""
    spin_id: str
    timestamp: datetime
    balance_before: float
    balance_after: float
    bet_amount: float
    win_amount: float
    is_free_spin: bool
    reel_positions: list[int] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "spin_id": self.spin_id,
            "timestamp": self.timestamp.isoformat(),
            "balance_before": self.balance_before,
            "balance_after": self.balance_after,
            "bet_amount": self.bet_amount,
            "win_amount": self.win_amount,
            "is_free_spin": self.is_free_spin,
            "reel_positions": self.reel_positions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SpinRecord":
        return cls(
            spin_id=d["spin_id"],
            timestamp=datetime.fromisoformat(d["timestamp"]) if isinstance(d["timestamp"], str) else d["timestamp"],
            balance_before=d["balance_before"],
            balance_after=d["balance_after"],
            bet_amount=d["bet_amount"],
            win_amount=d["win_amount"],
            is_free_spin=d["is_free_spin"],
            reel_positions=d.get("reel_positions", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class SessionSummary:
    """Summary of a game session."""
    session_id: str
    game_name: str
    start_time: datetime
    end_time: Optional[datetime]
    total_spins: int
    total_bet: float
    total_wins: float
    net_profit: float
    roi: float
    max_balance: float
    min_balance: float
    free_spins_triggered: int
    bonus_rounds_triggered: int
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "game_name": self.game_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_spins": self.total_spins,
            "total_bet": self.total_bet,
            "total_wins": self.total_wins,
            "net_profit": self.net_profit,
            "roi": self.roi,
            "max_balance": self.max_balance,
            "min_balance": self.min_balance,
            "free_spins_triggered": self.free_spins_triggered,
            "bonus_rounds_triggered": self.bonus_rounds_triggered,
            "metadata": self.metadata,
        }


@dataclass
class AlgorithmInsight:
    """Analysis insight about game algorithm."""
    insight_id: str
    timestamp: datetime
    insight_type: str  # "pattern", "anomaly", "optimization"
    description: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class DataCollector:
    """
    Collects and stores game data for analysis.

    Features:
    - Session recording
    - Spin-by-spin tracking
    - Batch collection support
    - Schema validation
    - Built-in exporter integration

    Usage:
        collector = DataCollector("/tmp/game_data")

        # Basic usage
        collector.start_session("slot_game_xyz")
        collector.record_spin(5000, 5100, 100, 0)
        collector.record_spin(5100, 5000, 100, 0)
        summary = collector.end_session()

        # Batch collection
        batch = BatchCollector(collector)
        batch.add_spin(session_id, spin_data)
        batch.flush()

        # Export
        exporter = DataExporter("/tmp/exports")
        exporter.export_sessions(collector, format="csv")
    """

    # Default schema for spin records
    DEFAULT_SPIN_SCHEMA = {
        "spin_id": str,
        "balance_before": float,
        "balance_after": float,
        "bet_amount": float,
        "win_amount": float,
        "is_free_spin": bool,
    }

    def __init__(
        self,
        storage_dir: Union[str, Path],
        validate_schema: bool = True,
        auto_export: bool = False,
        auto_export_dir: Optional[Path] = None,
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.validate_schema = validate_schema
        self.auto_export = auto_export

        self._lock = threading.RLock()
        self._current_session: Optional[str] = None
        self._spins: list[SpinRecord] = []
        self._session_start: Optional[datetime] = None
        self._game_name: str = "unknown"

        # Schema validation
        self._schema_validator = SchemaValidator()
        self._schema_validator.register("spin", self.DEFAULT_SPIN_SCHEMA)

        # Auto-export
        self._exporter = DataExporter(auto_export_dir) if auto_export_dir else None

    def start_session(
        self,
        game_name: str,
        metadata: Optional[dict] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Start a new recording session.

        Args:
            game_name: Name of the game
            metadata: Optional session metadata
            session_id: Optional custom session ID

        Returns:
            session_id
        """
        with self._lock:
            if self._current_session is not None:
                # Auto-end previous session
                self.end_session()

            session_id = session_id or str(uuid.uuid4())[:12]
            self._current_session = session_id
            self._spins = []
            self._session_start = datetime.now()
            self._game_name = game_name

            # Save session metadata
            session_file = self.storage_dir / f"session_{session_id}.json"
            with open(session_file, "w") as f:
                json.dump({
                    "session_id": session_id,
                    "game_name": game_name,
                    "start_time": self._session_start.isoformat(),
                    "metadata": metadata or {},
                    "status": "active",
                }, f, indent=2)

            return session_id

    def record_spin(
        self,
        balance_before: float,
        balance_after: float,
        bet_amount: float,
        win_amount: float,
        is_free_spin: bool = False,
        reel_positions: Optional[list[int]] = None,
        metadata: Optional[dict] = None,
        spin_id: Optional[str] = None,
    ) -> SpinRecord:
        """
        Record a single spin.

        Args:
            balance_before: Balance before the spin
            balance_after: Balance after the spin
            bet_amount: Amount bet
            win_amount: Amount won (0 if no win)
            is_free_spin: Whether this was a free spin
            reel_positions: Optional reel positions for analysis
            metadata: Optional additional metadata
            spin_id: Optional custom spin ID

        Returns:
            SpinRecord that was created
        """
        with self._lock:
            if self._current_session is None:
                raise RuntimeError("No active session. Call start_session() first.")

            spin_id = spin_id or str(uuid.uuid4())[:12]
            record = SpinRecord(
                spin_id=spin_id,
                timestamp=datetime.now(),
                balance_before=balance_before,
                balance_after=balance_after,
                bet_amount=bet_amount,
                win_amount=win_amount,
                is_free_spin=is_free_spin,
                reel_positions=reel_positions or [],
                metadata=metadata or {},
            )

            # Schema validation
            if self.validate_schema:
                result = self._schema_validator.validate("spin", record.to_dict())
                if not result.valid:
                    raise ValueError(f"Spin record validation failed: {result.errors}")
                if result.warnings:
                    record.metadata["_schema_warnings"] = result.warnings

            self._spins.append(record)
            return record

    def record_batch(
        self,
        spins: list[dict],
        session_id: Optional[str] = None,
    ) -> list[SpinRecord]:
        """
        Record a batch of spins at once.

        Args:
            spins: List of spin dicts (same fields as record_spin)
            session_id: Optional session override (uses active session if None)

        Returns:
            List of created SpinRecords
        """
        with self._lock:
            if session_id and session_id != self._current_session:
                # Switch sessions
                if self._current_session:
                    self.end_session()
                self.start_session(self._game_name, session_id=session_id)

            records = []
            for spin_data in spins:
                record = self.record_spin(
                    balance_before=spin_data["balance_before"],
                    balance_after=spin_data["balance_after"],
                    bet_amount=spin_data["bet_amount"],
                    win_amount=spin_data.get("win_amount", 0),
                    is_free_spin=spin_data.get("is_free_spin", False),
                    reel_positions=spin_data.get("reel_positions"),
                    metadata=spin_data.get("metadata"),
                    spin_id=spin_data.get("spin_id"),
                )
                records.append(record)

            return records

    def end_session(self, metadata: Optional[dict] = None) -> SessionSummary:
        """
        End the current session and return summary.

        Args:
            metadata: Optional metadata to merge into session record

        Returns:
            SessionSummary
        """
        with self._lock:
            if self._current_session is None:
                raise RuntimeError("No active session.")

            end_time = datetime.now()

            total_bet = sum(s.bet_amount for s in self._spins)
            total_wins = sum(s.win_amount for s in self._spins)
            net_profit = total_wins - total_bet
            roi = (net_profit / total_bet * 100) if total_bet > 0 else 0.0

            balances = (
                [s.balance_before for s in self._spins] +
                ([self._spins[-1].balance_after] if self._spins else [])
            )
            max_balance = max(balances) if balances else 0.0
            min_balance = min(balances) if balances else 0.0

            summary = SessionSummary(
                session_id=self._current_session,
                game_name=self._game_name,
                start_time=self._session_start or datetime.now(),
                end_time=end_time,
                total_spins=len(self._spins),
                total_bet=total_bet,
                total_wins=total_wins,
                net_profit=net_profit,
                roi=roi,
                max_balance=max_balance,
                min_balance=min_balance,
                free_spins_triggered=sum(1 for s in self._spins if s.is_free_spin),
                bonus_rounds_triggered=0,
            )

            self._save_session_data(summary, metadata)

            # Auto-export if enabled
            if self.auto_export and self._exporter:
                try:
                    self._exporter.export_spins(self, session_ids=[self._current_session])
                    self._exporter.export_sessions(self, session_ids=[self._current_session])
                except Exception:
                    pass  # Don't fail on export errors

            self._current_session = None
            self._spins = []
            return summary

    def _save_session_data(
        self,
        summary: SessionSummary,
        extra_metadata: Optional[dict] = None,
    ) -> None:
        """Save session data to disk."""
        session_id = summary.session_id

        # Save spins
        spins_file = self.storage_dir / f"spins_{session_id}.json"
        with open(spins_file, "w") as f:
            json.dump([s.to_dict() for s in self._spins], f, indent=2)

        # Update session summary
        session_file = self.storage_dir / f"session_{session_id}.json"
        if session_file.exists():
            with open(session_file) as f:
                data = json.load(f)

            data["end_time"] = summary.end_time.isoformat() if summary.end_time else None
            data["status"] = "completed"
            data["summary"] = {
                "total_spins": summary.total_spins,
                "total_bet": summary.total_bet,
                "total_wins": summary.total_wins,
                "net_profit": summary.net_profit,
                "roi": summary.roi,
                "max_balance": summary.max_balance,
                "min_balance": summary.min_balance,
            }
            if extra_metadata:
                data["metadata"].update(extra_metadata)
            with open(session_file, "w") as f:
                json.dump(data, f, indent=2)

    def get_session(self, session_id: str) -> Optional[dict]:
        """Load a session by ID."""
        session_file = self.storage_dir / f"session_{session_id}.json"
        if not session_file.exists():
            return None
        with open(session_file) as f:
            return json.load(f)

    def get_spins(self, session_id: str) -> list[SpinRecord]:
        """Load all spins for a session."""
        spins_file = self.storage_dir / f"spins_{session_id}.json"
        if not spins_file.exists():
            return []
        with open(spins_file) as f:
            data = json.load(f)
            return [SpinRecord.from_dict(s) for s in data]

    def list_sessions(self, game_name: Optional[str] = None) -> list[dict]:
        """List all sessions, optionally filtered by game name."""
        sessions = []
        for f in self.storage_dir.glob("session_*.json"):
            with open(f) as fp:
                sessions.append(json.load(fp))

        if game_name:
            sessions = [s for s in sessions if s.get("game_name") == game_name]

        return sorted(sessions, key=lambda s: s.get("start_time", ""), reverse=True)

    def get_current_session(self) -> Optional[str]:
        """Return the active session ID."""
        return self._current_session

    def is_session_active(self) -> bool:
        """Return True if there's an active session."""
        return self._current_session is not None

    def get_session_stats(self, session_id: str) -> Optional[dict]:
        """Get quick stats for a session without loading all spins."""
        session = self.get_session(session_id)
        if not session:
            return None
        summary = session.get("summary", {})
        return {
            "session_id": session_id,
            "game_name": session.get("game_name"),
            "status": session.get("status"),
            "total_spins": summary.get("total_spins", 0),
            "net_profit": summary.get("net_profit", 0),
            "roi": summary.get("roi", 0),
        }


class BatchCollector:
    """
    Efficiently collect data from multiple sessions in batch.

    Usage:
        collector = DataCollector("/tmp/data")
        batch = BatchCollector(collector)

        # Queue spins (not written to disk yet)
        batch.add_spin("session1", spin_data_1)
        batch.add_spin("session2", spin_data_2)
        batch.add_spin("session1", spin_data_3)

        # Flush to disk
        batch.flush()
    """

    def __init__(
        self,
        collector: DataCollector,
        flush_interval: int = 100,  # Auto-flush every N spins
        flush_seconds: float = 30.0,  # Auto-flush every N seconds
    ):
        self.collector = collector
        self.flush_interval = flush_interval
        self._buffer: list[tuple[str, dict]] = []  # (session_id, spin_data)
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()
        self._last_flush = datetime.now()
        self._timer_thread: Optional[threading.Thread] = None
        self._running = False

    def add_spin(self, session_id: str, spin_data: dict) -> None:
        """Add a spin to the batch buffer."""
        with self._lock:
            self._buffer.append((session_id, spin_data))
            self._counts[session_id] = self._counts.get(session_id, 0) + 1

            if len(self._buffer) >= self.flush_interval:
                self.flush()

    def flush(self) -> dict[str, int]:
        """
        Flush the buffer to disk.

        Returns:
            Dict mapping session_id to number of spins flushed
        """
        with self._lock:
            if not self._buffer:
                return {}

            # Group by session
            by_session: dict[str, list[dict]] = {}
            for session_id, spin_data in self._buffer:
                by_session.setdefault(session_id, []).append(spin_data)

            flushed: dict[str, int] = {}
            for session_id, spins in by_session.items():
                # Ensure session is started
                if not self.collector.is_session_active():
                    self.collector.start_session("batch", session_id=session_id)
                elif self.collector.get_current_session() != session_id:
                    self.collector.end_session()
                    self.collector.start_session("batch", session_id=session_id)

                self.collector.record_batch(spins, session_id=session_id)
                flushed[session_id] = len(spins)

            self._buffer.clear()
            self._last_flush = datetime.now()
            return flushed

    def start_auto_flush(self) -> None:
        """Start background auto-flush thread."""
        self._running = True
        self._timer_thread = threading.Thread(target=self._auto_flush_loop, daemon=True)
        self._timer_thread.start()

    def stop_auto_flush(self) -> None:
        """Stop background auto-flush thread."""
        self._running = False
        if self._timer_thread:
            self._timer_thread.join(timeout=5)
        self.flush()  # Final flush

    def _auto_flush_loop(self) -> None:
        while self._running:
            time.sleep(1.0)
            elapsed = (datetime.now() - self._last_flush).total_seconds()
            if elapsed >= self.flush_seconds:
                self.flush()

    def pending_count(self) -> int:
        """Return number of spins in buffer."""
        return len(self._buffer)


class AlgorithmAnalyzer:
    """
    Analyzes game algorithm from collected spin data.
    """

    def __init__(self, collector: DataCollector):
        self.collector = collector

    def analyze_session(self, session_id: str) -> list[AlgorithmInsight]:
        """Analyze a session and generate insights."""
        insights = []

        session = self.collector.get_session(session_id)
        if not session:
            return insights

        spins = self.collector.get_spins(session_id)
        if not spins:
            return insights

        # Analyze win patterns
        win_amounts = [s.win_amount for s in spins if s.win_amount > 0]
        if win_amounts:
            avg_win = sum(win_amounts) / len(win_amounts)
            max_win = max(win_amounts)
            insights.append(AlgorithmInsight(
                insight_id=str(uuid.uuid4())[:12],
                timestamp=datetime.now(),
                insight_type="pattern",
                description=f"Average win amount: {avg_win:.2f}",
                confidence=0.8,
                evidence=[f"Based on {len(win_amounts)} winning spins"],
            ))

        # RTP analysis
        total_bet = sum(s.bet_amount for s in spins)
        total_wins = sum(s.win_amount for s in spins)
        if total_bet > 0:
            rtp = (total_wins / total_bet) * 100
            insights.append(AlgorithmInsight(
                insight_id=str(uuid.uuid4())[:12],
                timestamp=datetime.now(),
                insight_type="optimization",
                description=f"Session RTP: {rtp:.2f}%",
                confidence=0.9,
                evidence=[f"Total bet: {total_bet:.2f}", f"Total wins: {total_wins:.2f}"],
                recommendations=[f"Expected RTP is typically 85-98%"] if rtp < 85 or rtp > 98 else [],
            ))

        # Anomaly detection
        if win_amounts:
            avg = sum(win_amounts) / len(win_amounts)
            high_wins = [w for w in win_amounts if w > avg * 5]
            if high_wins:
                insights.append(AlgorithmInsight(
                    insight_id=str(uuid.uuid4())[:12],
                    timestamp=datetime.now(),
                    insight_type="anomaly",
                    description=f"Found {len(high_wins)} unusually high wins (>5x average)",
                    confidence=0.7,
                    evidence=[f"Max win: {max(win_amounts):.2f}", f"Avg win: {avg:.2f}"],
                    recommendations=["Investigate if these are within expected RTP range"],
                ))

        # Free spin trigger analysis
        free_spins = [s for s in spins if s.is_free_spin]
        if len(spins) > 10:
            trigger_rate = len(free_spins) / len(spins)
            insights.append(AlgorithmInsight(
                insight_id=str(uuid.uuid4())[:12],
                timestamp=datetime.now(),
                insight_type="pattern",
                description=f"Free spin trigger rate: {trigger_rate:.2%}",
                confidence=0.6,
                evidence=[f"{len(free_spins)} free spins in {len(spins)} total spins"],
            ))

        # Volatility analysis
        if len(spins) > 20:
            net_deltas = [s.balance_after - s.balance_before for s in spins]
            variance = sum(d * d for d in net_deltas) / len(net_deltas)
            std_dev = variance ** 0.5
            volatility = "high" if std_dev > 500 else "medium" if std_dev > 200 else "low"
            insights.append(AlgorithmInsight(
                insight_id=str(uuid.uuid4())[:12],
                timestamp=datetime.now(),
                insight_type="pattern",
                description=f"Session volatility: {volatility} (std dev: {std_dev:.1f})",
                confidence=0.7,
                evidence=[f"Based on {len(spins)} spins"],
            ))

        return insights

    def analyze_all_sessions(self, game_name: Optional[str] = None) -> dict[str, list[AlgorithmInsight]]:
        """Analyze all sessions for a game."""
        sessions = self.collector.list_sessions(game_name=game_name)
        results = {}
        for session in sessions:
            sid = session.get("session_id")
            if sid:
                results[sid] = self.analyze_session(sid)
        return results
