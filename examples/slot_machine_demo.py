#!/usr/bin/env python3
"""
Slot Machine Demo - Complete walkthrough of CrawlForge slot automation.

Demonstrates:
- Creating a SlotGameAdapter
- Running a ReAct loop (simulated)
- Collecting spin data
- Saving checkpoints
- Exporting data

Run directly:
    python examples/slot_machine_demo.py
"""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# ---------------------------------------------------------------------------
# Mock the heavy dependencies so this demo can run standalone
# ---------------------------------------------------------------------------
import sys
demo_root = Path(__file__).parent.parent
sys.path.insert(0, str(demo_root))

# Mock ADB/Playwright to avoid needing real devices
MOCK_RUNTIME = MagicMock()
MOCK_RUNTIME.is_alive = MagicMock(return_value=True)
MOCK_RUNTIME.start = AsyncMock()
MOCK_RUNTIME.stop = AsyncMock()
MOCK_RUNTIME.execute = AsyncMock(return_value=MagicMock(success=True, duration_ms=50))
MOCK_RUNTIME.dump_hierarchy = AsyncMock(return_value={})
MOCK_RUNTIME.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n" + b"MOCK_SCREENSHOT_DATA")


def main():
    print("=" * 60)
    print("CrawlForge - Slot Machine Demo")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # Step 1: Setup - Import and create adapter
    # -------------------------------------------------------------------------
    print("\n[Step 1] Creating SlotGameAdapter...")

    from crawlforge.adapter.slot_adapter import SlotGameAdapter
    from crawlforge.adapter.base import AdapterConfig

    config = AdapterConfig(
        game_name="DemoSlot",
        game_version="1.0.0",
        confidence_threshold=0.75,
        default_bet=100,
        auto_collect=True,
    )

    adapter = SlotGameAdapter(
        runtime=MOCK_RUNTIME,
        game_name="DemoSlot",
        config=config,
    )
    print(f"  Adapter created: {adapter.game_name}")
    print(f"  Config: bet={config.default_bet}, threshold={config.confidence_threshold}")
    print(f"  Capabilities: {', '.join(adapter.get_capabilities())}")

    # -------------------------------------------------------------------------
    # Step 2: Session management
    # -------------------------------------------------------------------------
    print("\n[Step 2] Starting session...")

    session_id = asyncio.run(adapter.start_session())
    print(f"  Session started: {session_id}")

    # -------------------------------------------------------------------------
    # Step 3: Simulate ReAct loop - Detect, Act, Extract
    # -------------------------------------------------------------------------
    print("\n[Step 3] Running ReAct loop (10 simulated spins)...")

    import random
    from crawlforge.core import GameState, GameData, Action
    from crawlforge.detector import SlotPhase, SlotDetectionResult

    balance = 10000
    bet = 100

    for i in range(1, 11):
        # Simulate screenshot
        mock_screenshot = f"MOCK_SCREENSHOT_SPIN_{i}".encode()

        # Build game state manually
        state = GameState(
            screen=mock_screenshot,
            game_phase="GAME_READY",
            gold_amount=balance,
            raw_data={
                "spin_state": "idle",
                "win_amount": 0,
                "free_spins": 0,
                "reel_positions": [],
            },
            timestamp=time.time(),
        )
        print(f"  Spin {i:2d}: phase={state.game_phase}, balance={state.gold_amount}")

        # Generate action
        action = asyncio.run(adapter.generate_action(state, "spin"))
        print(f"           action={action.action_type} @ ({action.x},{action.y})")

        # Simulate execution
        asyncio.run(MOCK_RUNTIME.execute(action))

        # Simulate balance change
        win = random.choices([0, 50, 100, 200, 500, 1000], weights=[60, 20, 10, 5, 4, 1])[0]
        balance = balance - bet + win
        state.gold_amount = balance

        # Extract data
        data = asyncio.run(adapter.extract_data(state))
        print(f"           win={win}, balance={balance}, spins={data.value.get('spins', i)}")

    # -------------------------------------------------------------------------
    # Step 4: Collect data with DataCollector
    # -------------------------------------------------------------------------
    print("\n[Step 4] Recording spins with DataCollector...")

    from crawlforge.data import DataCollector, DataExporter

    storage_dir = Path("/tmp/crawlforge_demo_slot")
    storage_dir.mkdir(parents=True, exist_ok=True)

    collector = DataCollector(storage_dir)
    collector.start_session("DemoSlot", metadata={"source": "demo"})

    for i in range(1, 11):
        prev_balance = 10000 - 100 * (i - 1)
        wins = sum(random.choices([0, 50, 100, 200, 500, 1000], weights=[60, 20, 10, 5, 4, 1])[0] for _ in range(i - 1))
        balance_before = prev_balance + wins
        win = random.choices([0, 50, 100, 200, 500, 1000], weights=[60, 20, 10, 5, 4, 1])[0]
        collector.record_spin(
            balance_before=balance_before,
            balance_after=balance_before - bet + win,
            bet_amount=bet,
            win_amount=win,
            is_free_spin=False,
            metadata={"spin_number": i},
        )

    summary = collector.end_session()
    print(f"  Session ended: {summary.total_spins} spins, net={summary.net_profit:+d}, ROI={summary.roi:.2f}%")

    # -------------------------------------------------------------------------
    # Step 5: Checkpoint
    # -------------------------------------------------------------------------
    print("\n[Step 5] Saving checkpoint...")

    from crawlforge.checkpoint import CheckpointManager

    cp_dir = Path("/tmp/crawlforge_demo_checkpoints")
    cp_manager = CheckpointManager(cp_dir, max_checkpoints=20)

    state = {
        "balance": balance,
        "spin_count": 10,
        "game_phase": "idle",
        "total_wins": 500,
    }

    checkpoint = cp_manager.save(
        game_name="DemoSlot",
        session_id=session_id,
        state=state,
        metadata={"source": "demo"},
    )
    print(f"  Checkpoint saved: {checkpoint.checkpoint_id}")
    print(f"  Balance: {checkpoint.balance}, Spins: {checkpoint.spin_count}")

    # List checkpoints
    cps = cp_manager.list_checkpoints()
    print(f"  Total checkpoints: {len(cps)}")

    # -------------------------------------------------------------------------
    # Step 6: Export data
    # -------------------------------------------------------------------------
    print("\n[Step 6] Exporting data...")

    from datetime import datetime

    export_dir = Path("/tmp/crawlforge_demo_exports")
    export_dir.mkdir(parents=True, exist_ok=True)

    exporter = DataExporter(output_dir=export_dir)

    for fmt in ["json", "csv"]:
        path = exporter.export_sessions(collector, format=fmt)
        if path:
            size = path.stat().st_size
            print(f"  Exported ({fmt}): {path} ({size} bytes)")

    # -------------------------------------------------------------------------
    # Step 7: Stats
    # -------------------------------------------------------------------------
    print("\n[Step 7] Adapter statistics:")
    stats = adapter.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
