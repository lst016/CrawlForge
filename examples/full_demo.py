#!/usr/bin/env python3
"""
Full Demo - Complete CrawlForge workflow demonstration.

This demo shows the full adapter lifecycle:
1. Adapter registration
2. Session start
3. ReAct loop execution
4. Checkpoint save/restore
5. Data export (JSON + CSV)
6. Algorithm analysis

Run directly:
    python examples/full_demo.py
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import sys
demo_root = Path(__file__).parent.parent
sys.path.insert(0, str(demo_root))

from crawlforge import (
    AdapterRegistry,
    CheckpointManager,
    DataCollector,
    DataExporter,
    GameState,
    Action,
    GameData,
)
from crawlforge.adapter.base import AdapterConfig
from crawlforge.adapter.slot_adapter import SlotGameAdapter
from crawlforge.adapter.poker_adapter import PokerGameAdapter
from crawlforge.adapter.arcade_adapter import ArcadeGameAdapter
from crawlforge.data import AlgorithmAnalyzer


def main():
    print("=" * 65)
    print("CrawlForge - Full Framework Demo")
    print("=" * 65)

    # -------------------------------------------------------------------------
    # Step 1: Adapter Registration
    # -------------------------------------------------------------------------
    print("\n[Step 1] Adapter Registry")

    registry = AdapterRegistry()

    # Manually register adapters (normally auto-registered via get_registry)
    registry.register(
        SlotGameAdapter,
        game_name="slot_machine",
    )
    registry.register(
        PokerGameAdapter,
        game_name="video_poker",
    )
    registry.register(
        ArcadeGameAdapter,
        game_name="arcade_classic",
    )

    print(f"  Registered adapters: {registry.list_game_names()}")

    # -------------------------------------------------------------------------
    # Step 2: Create Runtime (mocked)
    # -------------------------------------------------------------------------
    print("\n[Step 2] Runtime Setup")

    mock_runtime = MagicMock()
    mock_runtime.is_alive = MagicMock(return_value=True)
    mock_runtime.start = AsyncMock()
    mock_runtime.stop = AsyncMock()
    mock_runtime.execute = AsyncMock(return_value=MagicMock(success=True, duration_ms=30))
    mock_runtime.screenshot = AsyncMock(return_value=b"\x89PNG_MOCK")
    print(f"  Runtime created: MockRuntime (alive={mock_runtime.is_alive()})")

    # -------------------------------------------------------------------------
    # Step 3: Create Adapters via Registry Factory
    # -------------------------------------------------------------------------
    print("\n[Step 3] Adapter Creation via Factory")

    slot_adapter = registry.create(
        "slot_machine",
        runtime=mock_runtime,
        config={"default_bet": 200, "confidence_threshold": 0.8},
    )

    poker_adapter = registry.create(
        "video_poker",
        runtime=mock_runtime,
        config={"default_bet": 50},
    )

    print(f"  slot_machine adapter: {slot_adapter.__class__.__name__}")
    print(f"  video_poker adapter:  {poker_adapter.__class__.__name__}")

    # -------------------------------------------------------------------------
    # Step 4: Session Management
    # -------------------------------------------------------------------------
    print("\n[Step 4] Session Management")

    session_id = asyncio.run(slot_adapter.start_session())
    print(f"  Started session: {session_id}")
    print(f"  Game: {slot_adapter.game_name}")

    # -------------------------------------------------------------------------
    # Step 5: Simulate ReAct Loop
    # -------------------------------------------------------------------------
    print("\n[Step 5] ReAct Loop (5 spins)")

    import random
    balance = 50000
    bet = 200

    for i in range(1, 6):
        state = GameState(
            screen=b"MOCK",
            game_phase="GAME_READY",
            gold_amount=balance,
            raw_data={"win_amount": 0, "free_spins": 0},
            timestamp=0,
        )

        action = asyncio.run(slot_adapter.generate_action(state, "spin"))
        win = random.choices([0, 100, 200, 400, 1000], weights=[70, 15, 8, 5, 2])[0]
        balance = balance - bet + win

        extracted = asyncio.run(slot_adapter.extract_data(state))
        print(f"  Spin {i}: bet={bet}, win={win}, balance={balance}, spins={extracted.value['spins']}")

    print(f"  Net profit: {balance - 50000:+d}")

    # -------------------------------------------------------------------------
    # Step 6: Checkpoint Save/Restore
    # -------------------------------------------------------------------------
    print("\n[Step 6] Checkpoint Management")

    cp_dir = Path("/tmp/crawlforge_demo_full")
    cp_dir.mkdir(parents=True, exist_ok=True)

    manager = CheckpointManager(cp_dir, max_checkpoints=10)

    # Save multiple checkpoints
    for i in range(3):
        state = {
            "balance": balance - i * 100,
            "spin_count": 5 + i,
            "game_phase": "GAME_READY",
            "total_wins": i * 100,
        }
        cp = manager.save(
            game_name="slot_machine",
            session_id=session_id,
            state=state,
            metadata={"checkpoint_num": i + 1},
        )
        print(f"  Saved checkpoint: {cp.checkpoint_id}")

    # List
    checkpoints = manager.list_checkpoints()
    print(f"  Total checkpoints: {len(checkpoints)}")

    # Restore latest
    latest = manager.get_latest()
    if latest:
        restored_state = manager.load_state(latest.checkpoint_id)
        print(f"  Restored: balance={restored_state['balance']}, spins={restored_state['spin_count']}")

    # -------------------------------------------------------------------------
    # Step 7: Data Collection & Export
    # -------------------------------------------------------------------------
    print("\n[Step 7] Data Collection & Export")

    storage_dir = Path("/tmp/crawlforge_demo_data")
    storage_dir.mkdir(parents=True, exist_ok=True)

    collector = DataCollector(storage_dir)
    collector.start_session("slot_machine", metadata={"demo": "full_demo"})

    # Record 20 spins
    for i in range(1, 21):
        win = random.choices([0, 50, 100, 200, 500], weights=[60, 20, 10, 7, 3])[0]
        collector.record_spin(
            balance_before=50000 - 200 * (i - 1),
            balance_after=50000 - 200 * i + win,
            bet_amount=200,
            win_amount=win,
            is_free_spin=False,
            metadata={"spin": i},
        )

    summary = collector.end_session()
    print(f"  Session: {summary.total_spins} spins, net={summary.net_profit:+d}, ROI={summary.roi:.2f}%")

    # Export JSON and CSV
    export_dir = Path("/tmp/crawlforge_demo_exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    exporter = DataExporter(output_dir=export_dir)

    json_path = exporter.export_sessions(collector, format="json")
    csv_path = exporter.export_sessions(collector, format="csv")
    print(f"  JSON: {json_path} ({json_path.stat().st_size} bytes)")
    print(f"  CSV:  {csv_path} ({csv_path.stat().st_size} bytes)")

    # -------------------------------------------------------------------------
    # Step 8: Algorithm Analysis
    # -------------------------------------------------------------------------
    print("\n[Step 8] Algorithm Analysis")

    analyzer = AlgorithmAnalyzer(collector)
    sessions = collector.list_sessions()
    if sessions:
        sid = sessions[0]["session_id"]
        insights = analyzer.analyze_session(sid)
        for insight in insights:
            print(f"  [{insight.insight_type.upper()}] {insight.description}")
            if insight.recommendations:
                for rec in insight.recommendations:
                    print(f"    → {rec}")

    # -------------------------------------------------------------------------
    # Step 9: Adapter Capabilities
    # -------------------------------------------------------------------------
    print("\n[Step 9] Adapter Capabilities")
    caps = slot_adapter.get_capabilities()
    print(f"  slot_machine: {', '.join(caps)}")
    caps = poker_adapter.get_capabilities()
    print(f"  video_poker:  {', '.join(caps)}")

    # -------------------------------------------------------------------------
    # Step 10: Cleanup
    # -------------------------------------------------------------------------
    print("\n[Step 10] Cleanup & Stats")

    end_summary = asyncio.run(slot_adapter.end_session())
    print(f"  Session ended: {end_summary['session_id']}")
    print(f"  Total spins:  {end_summary['spin_count']}")
    print(f"  Duration:      {end_summary['duration_seconds']:.1f}s")

    print("\n" + "=" * 65)
    print("Full demo complete!")
    print("=" * 65)


if __name__ == "__main__":
    main()
