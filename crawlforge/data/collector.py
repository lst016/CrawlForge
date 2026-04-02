"""
Data Collector - collects, analyzes, and stores game data.

Provides:
- Algorithm analysis
- Session data storage
- Statistical reporting
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Any


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

    Usage:
        collector = DataCollector("/tmp/game_data")
        collector.start_session("slot_game_xyz")
        collector.record_spin(5000, 5100, 100, 0)
        summary = collector.end_session()
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._current_session: Optional[str] = None
        self._spins: list[SpinRecord] = []
        self._session_start: Optional[datetime] = None

    def start_session(self, game_name: str, metadata: Optional[dict] = None) -> str:
        """Start a new recording session."""
        session_id = str(uuid.uuid4())[:12]
        self._current_session = session_id
        self._spins = []
        self._session_start = datetime.now()

        # Save session metadata
        session_file = self.storage_dir / f"session_{session_id}.json"
        with open(session_file, "w") as f:
            json.dump({
                "session_id": session_id,
                "game_name": game_name,
                "start_time": self._session_start.isoformat(),
                "metadata": metadata or {},
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
    ) -> SpinRecord:
        """Record a single spin."""
        if self._current_session is None:
            raise RuntimeError("No active session. Call start_session() first.")

        spin_id = str(uuid.uuid4())[:12]
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
        self._spins.append(record)
        return record

    def end_session(self) -> SessionSummary:
        """End the current session and return summary."""
        if self._current_session is None:
            raise RuntimeError("No active session.")

        end_time = datetime.now()

        total_bet = sum(s.bet_amount for s in self._spins)
        total_wins = sum(s.win_amount for s in self._spins)
        net_profit = total_wins - total_bet
        roi = (net_profit / total_bet * 100) if total_bet > 0 else 0.0

        balances = [s.balance_before for s in self._spins] + ([self._spins[-1].balance_after] if self._spins else [])
        max_balance = max(balances) if balances else 0.0
        min_balance = min(balances) if balances else 0.0

        summary = SessionSummary(
            session_id=self._current_session,
            game_name="unknown",
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

        # Save session data
        self._save_session_data(summary)

        self._current_session = None
        self._spins = []
        return summary

    def _save_session_data(self, summary: SessionSummary) -> None:
        """Save session data to disk."""
        session_id = summary.session_id

        # Save spins
        spins_file = self.storage_dir / f"spins_{session_id}.json"
        with open(spins_file, "w") as f:
            json.dump([
                {
                    "spin_id": s.spin_id,
                    "timestamp": s.timestamp.isoformat(),
                    "balance_before": s.balance_before,
                    "balance_after": s.balance_after,
                    "bet_amount": s.bet_amount,
                    "win_amount": s.win_amount,
                    "is_free_spin": s.is_free_spin,
                    "reel_positions": s.reel_positions,
                    "metadata": s.metadata,
                }
                for s in self._spins
            ], f, indent=2)

        # Update session summary
        session_file = self.storage_dir / f"session_{session_id}.json"
        if session_file.exists():
            with open(session_file) as f:
                data = json.load(f)
            data["end_time"] = summary.end_time.isoformat()
            data["summary"] = {
                "total_spins": summary.total_spins,
                "total_bet": summary.total_bet,
                "total_wins": summary.total_wins,
                "net_profit": summary.net_profit,
                "roi": summary.roi,
                "max_balance": summary.max_balance,
                "min_balance": summary.min_balance,
            }
            with open(session_file, "w") as f:
                json.dump(data, f, indent=2)

    def get_session(self, session_id: str) -> Optional[dict]:
        """Load a session by ID."""
        session_file = self.storage_dir / f"session_{session_id}.json"
        if not session_file.exists():
            return None
        with open(session_file) as f:
            return json.load(f)

    def list_sessions(self) -> list[dict]:
        """List all sessions."""
        sessions = []
        for f in self.storage_dir.glob("session_*.json"):
            with open(f) as fp:
                sessions.append(json.load(fp))
        return sorted(sessions, key=lambda s: s.get("start_time", ""), reverse=True)


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

        spins_file = self.collector.storage_dir / f"spins_{session_id}.json"
        if not spins_file.exists():
            return insights

        with open(spins_file) as f:
            spins = json.load(f)

        if not spins:
            return insights

        # Analyze win patterns
        win_amounts = [s["win_amount"] for s in spins if s["win_amount"] > 0]
        if win_amounts:
            avg_win = sum(win_amounts) / len(win_amounts)
            insights.append(AlgorithmInsight(
                insight_id=str(uuid.uuid4())[:12],
                timestamp=datetime.now(),
                insight_type="pattern",
                description=f"Average win amount: {avg_win:.2f}",
                confidence=0.8,
                evidence=[f"Based on {len(win_amounts)} winning spins"],
            ))

        # Detect anomaly: unusually high wins
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
        free_spins = [s for s in spins if s.get("is_free_spin")]
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

        return insights
