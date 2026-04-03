"""
CrawlForge CLI - Command-line interface for CrawlForge.

Usage:
    crawlforge run <game>           # Run game crawler
    crawlforge list                 # List all registered adapters
    crawlforge checkpoint <op>      # Checkpoint operations
    crawlforge export <game>        # Export game data
    crawlforge schedule <game> <cron>  # Add scheduled task

Examples:
    crawlforge list
    crawlforge run slot_machine --spins 100
    crawlforge checkpoint ls
    crawlforge checkpoint diff abc123
    crawlforge export slot_machine --format csv
    crawlforge schedule slot_machine "*/5 * * * *"
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import crawlforge
from crawlforge import (
    AdapterRegistry,
    CheckpointManager,
    DataCollector,
    DataExporter,
    SlotGameAdapter,
    PokerGameAdapter,
    ArcadeGameAdapter,
    GameState,
    Action,
    GameData,
    RuntimeType,
)
from crawlforge.adapter import get_registry, create_adapter
from crawlforge.data import DataCollector as DC, DataExporter as DE
from crawlforge.scheduler import CronParser, CronScheduler


def cmd_list(args) -> int:
    """List all registered adapters."""
    registry = get_registry()
    adapters = registry.list_adapters()

    if not adapters:
        print("No adapters registered.")
        return 0

    print(f"\n{'='*60}")
    print(f"Registered Adapters ({len(adapters)})")
    print(f"{'='*60}")
    for name, entry in adapters:
        meta = entry.metadata
        print(f"\n  [{name}]")
        print(f"    Type:      {meta.game_type}")
        print(f"    Version:   {meta.version}")
        print(f"    Phases:    {', '.join(meta.supported_phases) if meta.supported_phases else 'N/A'}")
        print(f"    Author:    {meta.author}")
        print(f"    Module:    {entry.module_path}")
        if meta.description:
            desc = meta.description[:80] + ("..." if len(meta.description) > 80 else "")
            print(f"    Desc:      {desc}")
    print(f"\n{'='*60}\n")
    return 0


def cmd_checkpoint(args) -> int:
    """Manage checkpoints."""
    storage_dir = Path(args.storage_dir or "/tmp/crawlforge_checkpoints")
    manager = CheckpointManager(storage_dir)

    op = args.op

    if op == "ls":
        checkpoints = manager.list_checkpoints(
            game_name=args.game or None,
            session_id=args.session or None,
        )
        if not checkpoints:
            print("No checkpoints found.")
            return 0

        print(f"\n{'ID':<14} {'Time':<22} {'Game':<20} {'Balance':<12} {'Spins':<8} {'Session':<14}")
        print("-" * 90)
        for cp in checkpoints:
            ts = cp.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{cp.checkpoint_id:<14} {ts:<22} {cp.game_name:<20} {cp.balance:<12.2f} {cp.spin_count:<8} {cp.session_id:<14}")
        print(f"\nTotal: {len(checkpoints)} checkpoint(s)")
        return 0

    elif op == "diff":
        if not args.id1 or not args.id2:
            print("Error: diff requires two checkpoint IDs: --id1 <id> --id2 <id>")
            return 1
        state1 = manager.load_state(args.id1)
        state2 = manager.load_state(args.id2)
        if state1 is None or state2 is None:
            print("Error: one or both checkpoints not found.")
            return 1

        diff = {}
        all_keys = set(state1.keys()) | set(state2.keys())
        for k in sorted(all_keys):
            v1 = state1.get(k)
            v2 = state2.get(k)
            if v1 != v2:
                diff[k] = {"before": v1, "after": v2}

        print(f"\nDiff: {args.id1} → {args.id2}")
        print("-" * 40)
        if not diff:
            print("  (no differences)")
        else:
            for k, vals in diff.items():
                print(f"  {k}:")
                print(f"    - {vals['before']}")
                print(f"    + {vals['after']}")
        return 0

    elif op == "restore":
        if not args.checkpoint_id:
            print("Error: restore requires --checkpoint-id <id>")
            return 1
        state = manager.load_state(args.checkpoint_id)
        if state is None:
            print(f"Error: checkpoint {args.checkpoint_id} not found.")
            return 1
        print(f"\nRestored state for checkpoint {args.checkpoint_id}:")
        print(json.dumps(state, indent=2, default=str))
        return 0

    elif op == "export":
        if not args.checkpoint_id:
            print("Error: export requires --checkpoint-id <id>")
            return 1
        output = Path(args.output or f"checkpoint_{args.checkpoint_id}.json")
        if manager.export(args.checkpoint_id, output):
            print(f"Exported checkpoint to {output}")
        else:
            print(f"Error: failed to export checkpoint {args.checkpoint_id}")
            return 1
        return 0

    else:
        print(f"Unknown checkpoint operation: {op}")
        print("Supported: ls, diff, restore, export")
        return 1


def cmd_export(args) -> int:
    """Export game data."""
    storage_dir = Path(args.storage_dir or "/tmp/crawlforge_data")
    collector = DC(storage_dir)
    exporter = DE(output_dir=Path(args.output_dir or "/tmp/crawlforge_exports"))

    game_name = args.game or None
    format = args.format or "json"
    session_ids = args.sessions.split(",") if args.sessions else None

    sessions = collector.list_sessions(game_name=game_name)
    if not sessions:
        print(f"No sessions found for game '{game_name or 'all'}'.")
        return 0

    filtered = [s for s in sessions if not session_ids or s.get("session_id") in session_ids]

    if args.export_type == "sessions":
        path = exporter.export_sessions(collector, format=format, session_ids=session_ids)
    elif args.export_type == "spins":
        path = exporter.export_spins(collector, format=format, session_ids=session_ids)
    elif args.export_type == "summary":
        path = exporter.export_summary(collector, format=format)
    else:
        path = exporter.export_sessions(collector, format=format, session_ids=session_ids)

    if path:
        print(f"Exported to: {path}")
        return 0
    else:
        print("Export failed or no data to export.")
        return 1


def cmd_run(args) -> int:
    """Run a game adapter."""
    game_name = args.game
    registry = get_registry()

    # Check if adapter exists
    adapter_class = registry.get_adapter_class(game_name)
    if adapter_class is None:
        print(f"Error: adapter '{game_name}' not found.")
        print("  Use 'crawlforge list' to see available adapters.")
        return 1

    # Create a mock runtime for CLI demo (avoiding real ADB/Playwright)
    from crawlforge.runtimes import ADBRuntime

    try:
        runtime = ADBRuntime()
        print(f"[CLI] Starting {game_name} adapter (dry-run mode)...")
        print(f"[CLI] For real execution, provide --runtime adb|playwright")
    except Exception as e:
        print(f"[CLI] Runtime init: {e}")

    print(f"[CLI] Adapter: {game_name}")
    print(f"[CLI] Spins: {args.spins or 'unlimited'}")
    print(f"[CLI] Goal: {args.goal or 'spin'}")

    # Show what would be loaded
    entry = registry.get(game_name)
    if entry:
        print(f"[CLI] Type: {entry.metadata.game_type}")
        print(f"[CLI] Capabilities: {', '.join(entry.metadata.capabilities or [])}")

    print("\n[CLI] NOTE: This is a dry-run CLI. For real game automation,")
    print("         use the Python API with a real ADB/Playwright runtime.")
    print("         Example:")
    print("           from crawlforge.adapter import create_adapter")
    print("           from crawlforge.runtimes import ADBRuntime")
    print("           adapter = create_adapter('slot_machine', runtime)")
    print("           await adapter.start_session('game_001')")
    print("           state = await adapter.detect_state(screenshot_bytes)")
    print("           action = await adapter.generate_action(state, 'spin')")

    return 0


def cmd_schedule(args) -> int:
    """Show/add scheduled tasks."""
    parser = CronParser()
    cron_expr = args.cron_expr

    # Validate cron expression
    valid, err = parser.validate(cron_expr)
    if not valid:
        print(f"Invalid cron expression: {err}")
        return 1

    parsed = parser.parse(cron_expr)
    next_runs = parser.upcoming_runs(parsed, count=5)

    print(f"\nSchedule: {args.game}")
    print(f"  Cron: {cron_expr}")
    print(f"  Next 5 runs:")
    for i, t in enumerate(next_runs, 1):
        print(f"    {i}. {t.strftime('%Y-%m-%d %H:%M:%S')}")

    # Save to schedule file
    schedule_file = Path.home() / ".crawlforge" / "schedules.json"
    schedule_file.parent.mkdir(parents=True, exist_ok=True)

    schedules = {}
    if schedule_file.exists():
        try:
            schedules = json.loads(schedule_file.read_text())
        except Exception:
            schedules = {}

    schedules[args.game] = {
        "cron": cron_expr,
        "added_at": datetime.now().isoformat(),
        "game": args.game,
    }
    schedule_file.write_text(json.dumps(schedules, indent=2))
    print(f"\n  Schedule saved to: {schedule_file}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crawlforge",
        description="CrawlForge - AI-Driven Multi-Game Crawler Framework",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    sub.add_parser("list", help="List all registered adapters")

    # run
    run_parser = sub.add_parser("run", help="Run a game crawler")
    run_parser.add_argument("game", help="Game name (e.g., slot_machine, poker)")
    run_parser.add_argument("--spins", type=int, help="Number of spins to run")
    run_parser.add_argument("--goal", default="spin", help="Goal (spin, auto, collect)")
    run_parser.add_argument("--runtime", choices=["adb", "playwright"], help="Runtime type")
    run_parser.set_defaults(func=cmd_run)

    # checkpoint
    cp_parser = sub.add_parser("checkpoint", help="Checkpoint operations")
    cp_parser.add_argument("op", choices=["ls", "diff", "restore", "export"], help="Operation")
    cp_parser.add_argument("--game", help="Filter by game name")
    cp_parser.add_argument("--session", help="Filter by session ID")
    cp_parser.add_argument("--checkpoint-id", "--id", dest="checkpoint_id", help="Checkpoint ID")
    cp_parser.add_argument("--id1", help="First checkpoint ID (for diff)")
    cp_parser.add_argument("--id2", help="Second checkpoint ID (for diff)")
    cp_parser.add_argument("--output", help="Output file path (for export)")
    cp_parser.add_argument("--storage-dir", help="Checkpoint storage directory")
    cp_parser.set_defaults(func=cmd_checkpoint)

    # export
    exp_parser = sub.add_parser("export", help="Export game data")
    exp_parser.add_argument("game", nargs="?", help="Game name (optional)")
    exp_parser.add_argument("--type", dest="export_type", default="sessions",
                            choices=["sessions", "spins", "summary"], help="Export type")
    exp_parser.add_argument("--format", default="json", choices=["json", "csv", "parquet"],
                            help="Output format")
    exp_parser.add_argument("--sessions", help="Comma-separated session IDs")
    exp_parser.add_argument("--output-dir", help="Output directory")
    exp_parser.add_argument("--storage-dir", help="Data storage directory")
    exp_parser.set_defaults(func=cmd_export)

    # schedule
    sch_parser = sub.add_parser("schedule", help="Add scheduled task")
    sch_parser.add_argument("game", help="Game name")
    sch_parser.add_argument("cron_expr", help="Cron expression (e.g., */5 * * * *)")
    sch_parser.set_defaults(func=cmd_schedule)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list":
        return cmd_list(args)
    elif args.command in ("run", "checkpoint", "export", "schedule"):
        return args.func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
