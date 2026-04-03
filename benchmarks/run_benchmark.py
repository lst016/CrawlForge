#!/usr/bin/env python3
"""
CrawlForge Performance Benchmarks.

Benchmarks core components:
- CheckpointManager: snapshot/restore performance
- PriorityQueue: enqueue/dequeue performance
- DataExporter: JSON/CSV/Parquet export performance
- AdapterRegistry: lookup performance

Run:
    python benchmarks/run_benchmark.py
"""

import gc
import json
import random
import string
import tempfile
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawlforge import (
    CheckpointManager,
    DataCollector,
    DataExporter,
    GameState,
)
from crawlforge.adapter import AdapterRegistry
from crawlforge.adapter.slot_adapter import SlotGameAdapter
from crawlforge.scheduler import PriorityQueue


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------

def format_time(seconds: float) -> str:
    """Format seconds into human-readable string."""
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.2f} µs"
    elif seconds < 1:
        return f"{seconds * 1_000:.2f} ms"
    else:
        return f"{seconds:.3f} s"


def format_ops_per_sec(n: int, elapsed: float) -> str:
    """Format operations per second."""
    if elapsed <= 0:
        return "inf ops/s"
    ops = n / elapsed
    if ops >= 1_000_000:
        return f"{ops / 1_000_000:.2f} Mops/s"
    elif ops >= 1_000:
        return f"{ops / 1_000:.2f} Kops/s"
    return f"{ops:.2f} ops/s"


def benchmark(name: str, fn, iterations: int, **kwargs) -> dict:
    """Run a benchmark and return results."""
    gc.collect()
    tracemalloc.start()

    start = time.perf_counter()
    result = fn(iterations, **kwargs)
    elapsed = time.perf_counter() - start

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    ops_per_sec = iterations / elapsed if elapsed > 0 else float("inf")

    print(f"  {name:<40} {format_time(elapsed):>12}  {ops_per_sec:>15.2f} ops/s")
    return {
        "name": name,
        "iterations": iterations,
        "elapsed": elapsed,
        "ops_per_sec": ops_per_sec,
        "peak_memory_mb": peak / (1024 * 1024),
    }


# ---------------------------------------------------------------------------
# Checkpoint benchmarks
# ---------------------------------------------------------------------------

def make_state(i: int) -> dict:
    """Create a deterministic game state."""
    return {
        "balance": 10000 + i * 100,
        "spin_count": i,
        "game_phase": "GAME_READY",
        "total_wins": i * 50,
        "session_id": f"session-{i:04d}",
        "timestamp": datetime.now().isoformat(),
        "raw": {"reel_positions": [i % 5, (i + 1) % 5, (i + 2) % 5]},
    }


def bench_checkpoint_save(iterations: int, cp_dir: Path) -> dict:
    """Benchmark checkpoint saves."""
    manager = CheckpointManager(cp_dir, max_checkpoints=1000)
    for i in range(iterations):
        manager.save(
            game_name="BenchSlot",
            session_id=f"bench-{i}",
            state=make_state(i),
            metadata={"bench": True},
        )
    return manager


def bench_checkpoint_load(iterations: int, manager: CheckpointManager, ids: list) -> None:
    """Benchmark checkpoint loads."""
    for i in range(iterations):
        idx = i % len(ids)
        manager.load_state(ids[idx])


def bench_checkpoint_restore(iterations: int, manager: CheckpointManager, ids: list) -> None:
    """Benchmark checkpoint state restoration."""
    for i in range(iterations):
        idx = i % len(ids)
        manager.load(ids[idx])


def run_checkpoint_benchmarks() -> list[dict]:
    print("\n" + "=" * 70)
    print("CheckpointManager Benchmarks")
    print("=" * 70)
    print(f"  {'Operation':<40} {'Time':>12}  {'Throughput':>15}")
    print("-" * 70)

    results = []
    with tempfile.TemporaryDirectory() as td:
        cp_dir = Path(td)

        # Benchmark save
        res = benchmark(
            "CheckpointManager.save (100 ops)",
            lambda n, **_: bench_checkpoint_save(n, cp_dir),
            iterations=100,
        )
        results.append(res)

        # Get checkpoint IDs for load/restore tests
        manager = CheckpointManager(cp_dir)
        bench_checkpoint_save(100, cp_dir)
        checkpoints = manager.list_checkpoints()
        ids = [cp.checkpoint_id for cp in checkpoints]

        # Benchmark load (metadata)
        res = benchmark(
            "CheckpointManager.load (1000 ops)",
            lambda n, **_: bench_checkpoint_load(n, manager, ids),
            iterations=1000,
        )
        results.append(res)

        # Benchmark state restore
        res = benchmark(
            "CheckpointManager.load_state (1000 ops)",
            lambda n, **_: bench_checkpoint_restore(n, manager, ids),
            iterations=1000,
        )
        results.append(res)

    return results


# ---------------------------------------------------------------------------
# PriorityQueue benchmarks
# ---------------------------------------------------------------------------

def bench_queue_push(iterations: int) -> PriorityQueue:
    """Benchmark PriorityQueue push."""
    pq = PriorityQueue()
    for i in range(iterations):
        pq.push(f"task-{i}", priority=random.randint(1, 10))
    return pq


def bench_queue_pop_push(iterations: int) -> int:
    """Benchmark interleaved pop/push."""
    pq = PriorityQueue()
    count = 0
    for i in range(iterations):
        pq.push(f"task-{i}", priority=random.randint(1, 10))
        if i % 10 == 0 and not pq.is_empty():
            pq.pop()
            count += 1
    return count


def run_queue_benchmarks() -> list[dict]:
    print("\n" + "=" * 70)
    print("PriorityQueue Benchmarks")
    print("=" * 70)
    print(f"  {'Operation':<40} {'Time':>12}  {'Throughput':>15}")
    print("-" * 70)

    results = []

    # Push only
    res = benchmark(
        "PriorityQueue.push (10000 ops)",
        bench_queue_push,
        iterations=10000,
    )
    results.append(res)

    # Push + occasional pop
    res = benchmark(
        "PriorityQueue.push+pop (10000 ops)",
        bench_queue_pop_push,
        iterations=10000,
    )
    results.append(res)

    return results


# ---------------------------------------------------------------------------
# DataExporter benchmarks
# ---------------------------------------------------------------------------

def bench_export_json(iterations: int, records: list, export_dir: Path) -> Path:
    """Benchmark JSON export."""
    collector = DataCollector(export_dir / "collector")
    exporter = DataExporter(export_dir / "exports")
    return exporter.export_sessions(collector, format="json")


def bench_export_csv(iterations: int, records: list, export_dir: Path) -> Path:
    """Benchmark CSV export."""
    collector = DataCollector(export_dir / "collector")
    exporter = DataExporter(export_dir / "exports")
    return exporter.export_sessions(collector, format="csv")


def bench_export_parquet(iterations: int, records: list, export_dir: Path) -> Path:
    """Benchmark Parquet export."""
    collector = DataCollector(export_dir / "collector")
    exporter = DataExporter(export_dir / "exports")
    return exporter.export_sessions(collector, format="parquet")


def run_exporter_benchmarks() -> list[dict]:
    print("\n" + "=" * 70)
    print("DataExporter Benchmarks (1000 records)")
    print("=" * 70)
    print(f"  {'Operation':<40} {'Time':>12}  {'Throughput':>15}")
    print("-" * 70)

    results = []

    # Create 1000 spin records
    with tempfile.TemporaryDirectory() as td:
        export_dir = Path(td)
        collector_dir = export_dir / "collector"
        collector_dir.mkdir()

        collector = DataCollector(collector_dir)
        collector.start_session("BenchSlot")

        for i in range(1000):
            win = random.choices([0, 50, 100, 200, 500], weights=[60, 20, 10, 7, 3])[0]
            collector.record_spin(
                balance_before=10000 - 100 * i,
                balance_after=10000 - 100 * (i + 1) + win,
                bet_amount=100,
                win_amount=win,
                is_free_spin=False,
                metadata={"spin": i},
            )
        collector.end_session()

        # JSON export
        res = benchmark(
            "DataExporter (JSON, 1000 rows)",
            lambda n, **kw: bench_export_json(n, [], export_dir),
            iterations=1,
        )
        results.append(res)

        # CSV export
        res = benchmark(
            "DataExporter (CSV, 1000 rows)",
            lambda n, **kw: bench_export_csv(n, [], export_dir),
            iterations=1,
        )
        results.append(res)

        # Parquet export
        res = benchmark(
            "DataExporter (Parquet, 1000 rows)",
            lambda n, **kw: bench_export_parquet(n, [], export_dir),
            iterations=1,
        )
        results.append(res)

    return results


# ---------------------------------------------------------------------------
# AdapterRegistry benchmarks
# ---------------------------------------------------------------------------

def bench_registry_lookup(iterations: int) -> None:
    """Benchmark AdapterRegistry lookup."""
    registry = AdapterRegistry()
    registry.register(SlotGameAdapter, game_name="BenchSlot")

    # Warm up
    for name in registry.list_game_names():
        registry.get(name)

    # Benchmark
    names = registry.list_game_names()
    for _ in range(iterations):
        for name in names:
            registry.get(name)


def bench_registry_create(iterations: int, runtime) -> None:
    """Benchmark adapter creation via factory."""
    registry = AdapterRegistry()
    registry.register(SlotGameAdapter, game_name="BenchSlot2")

    for _ in range(iterations):
        registry.create("BenchSlot2", runtime=runtime)


def run_registry_benchmarks() -> list[dict]:
    print("\n" + "=" * 70)
    print("AdapterRegistry Benchmarks")
    print("=" * 70)
    print(f"  {'Operation':<40} {'Time':>12}  {'Throughput':>15}")
    print("-" * 70)

    results = []

    # Create a mock runtime
    from unittest.mock import MagicMock
    mock_runtime = MagicMock()

    res = benchmark(
        "AdapterRegistry.get (1000 lookups)",
        bench_registry_lookup,
        iterations=1000,
    )
    results.append(res)

    res = benchmark(
        "AdapterRegistry.create (100 ops)",
        lambda n, **kw: bench_registry_create(n, mock_runtime),
        iterations=100,
    )
    results.append(res)

    return results


# ---------------------------------------------------------------------------
# Memory benchmarks
# ---------------------------------------------------------------------------

def bench_memory_checkpoint(iterations: int, cp_dir: Path) -> None:
    """Memory benchmark for CheckpointManager."""
    manager = CheckpointManager(cp_dir, max_checkpoints=100)
    for i in range(iterations):
        manager.save(
            game_name="MemSlot",
            session_id=f"mem-{i}",
            state=make_state(i),
        )


def run_memory_benchmarks() -> list[dict]:
    print("\n" + "=" * 70)
    print("Memory Benchmarks")
    print("=" * 70)
    print(f"  {'Operation':<40} {'Peak Memory':>15}")
    print("-" * 70)

    results = []

    with tempfile.TemporaryDirectory() as td:
        gc.collect()
        tracemalloc.start()
        bench_memory_checkpoint(50, Path(td))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        print(f"  {'CheckpointManager (50 saves)':<40} {peak_mb:>12.2f} MB")
        results.append({"name": "CheckpointManager (50 saves)", "peak_mb": peak_mb})

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def print_summary(all_results: list[dict]) -> None:
    """Print a summary table."""
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    # Group by category
    categories = {}
    for r in all_results:
        cat = r.get("category", "Other")
        categories.setdefault(cat, []).append(r)

    for cat, items in categories.items():
        print(f"\n  {cat}")
        for item in items:
            if "elapsed" in item:
                print(f"    {item['name']:<38} {item['ops_per_sec']:>12.2f} ops/s")
            elif "peak_mb" in item:
                print(f"    {item['name']:<38} {item['peak_mb']:>12.2f} MB")


def main() -> None:
    print("=" * 70)
    print("CrawlForge Performance Benchmarks")
    print("=" * 70)
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Date:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    all_results: list[dict] = []

    # Run all benchmarks
    for results in [
        run_checkpoint_benchmarks(),
        run_queue_benchmarks(),
        run_exporter_benchmarks(),
        run_registry_benchmarks(),
        run_memory_benchmarks(),
    ]:
        for r in results:
            r["category"] = "General"
        all_results.extend(results)

    print_summary(all_results)

    # Export results as JSON
    output_path = Path.home() / ".crawlforge" / "benchmark_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        # Convert non-serializable values
        serializable = []
        for r in all_results:
            sr = {k: float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v
                  for k, v in r.items()}
            serializable.append(sr)
        json.dump(serializable, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
