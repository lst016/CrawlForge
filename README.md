# CrawlForge

> AI-driven multi-game crawler framework for automating slot, poker, and arcade games.

**CrawlForge** is a modular Python framework for automating game interactions using AI-driven detection, ReAct-based action loops, and self-evolving adapters.

---

## Features

- **Modular Adapters** — `SlotGameAdapter`, `PokerGameAdapter`, `ArcadeGameAdapter`
- **Multi-Runtime** — ADB (Android), Playwright (web/H5), UI Automation
- **AI Pipeline** — ReAct loop (Reasoning + Acting) with AI-powered state detection
- **Checkpoint System** — Snapshot/restore/rollback with incremental deltas and FileLock concurrency
- **Data Collection** — Spin-by-spin recording, batch collection, RTP analysis, algorithm insights
- **Scheduler** — Priority queue, cron scheduling, retry with exponential backoff
- **Self-Evolving** — Genetic engine + feedback-driven adapter repair
- **CLI** — Full command-line interface for all operations

---

## Installation

```bash
# From source
cd ~/Desktop/agent/projects/CrawlForge
pip install -e .

# Or install dependencies only
pip install -e . --no-deps
pip install playwright httpx pydantic opencv-python uiautomator2
```

---

## Quick Start

```python
from crawlforge import (
    SlotGameAdapter, CheckpointManager, DataCollector, DataExporter,
)
from crawlforge.runtimes import ADBRuntime

# 1. Setup runtime
runtime = ADBRuntime()          # Android device via ADB
await runtime.start()

# 2. Create adapter
adapter = SlotGameAdapter(runtime, game_name="MySlot")

# 3. Start session
session_id = await adapter.start_session()

# 4. ReAct loop
for _ in range(100):
    screenshot = await runtime.screenshot()
    state = await adapter.detect_state(screenshot)
    action = await adapter.generate_action(state, goal="spin")
    await runtime.execute(action)
    data = await adapter.extract_data(state)

# 5. Checkpoint
cp_manager = CheckpointManager("/tmp/cf_checkpoints")
cp_manager.save("MySlot", session_id, {"balance": 10000, "spin_count": 100})

# 6. Export
collector = DataCollector("/tmp/cf_data")
exporter = DataExporter("/tmp/cf_exports")
exporter.export_sessions(collector, format="csv")
```

---

## Architecture

```
crawlforge/
├── core/                    # Core models and interfaces
│   ├── models.py            # GameState, Action, GameData, ActionResult
│   ├── interfaces.py        # Runtime, GameAdapter abstract interfaces
│   └── exceptions.py        # Custom exception hierarchy
│
├── adapter/                 # Game adapter system
│   ├── base.py              # GameAdapter ABC, AdapterConfig, AdapterMetadata
│   ├── registry.py           # AdapterRegistry (singleton, factory pattern)
│   ├── slot_adapter.py      # SlotGameAdapter (slot machine games)
│   ├── poker_adapter.py     # PokerGameAdapter (video poker)
│   └── arcade_adapter.py    # ArcadeGameAdapter (arcade games)
│
├── data/                    # Data collection & export
│   ├── collector.py          # DataCollector, BatchCollector, AlgorithmAnalyzer
│   └── exporter.py           # DataExporter (JSON/CSV/Parquet), SchemaValidator
│
├── checkpoint/              # Checkpoint & rollback system
│   └── manager.py           # CheckpointManager, IncrementalCheckpoint, RollbackManager, FileLock
│
├── detector/                # Game state detection
│   ├── slot_detector.py     # SlotGameDetector (phase, spin, balance detection)
│   └── phases.py            # SlotPhase, SpinState, BalanceState enums
│
├── runtimes/                # Platform runtimes
│   ├── adb_runtime.py       # ADBRuntime (Android ADB + uiautomator2)
│   └── playwright_runtime.py # PlaywrightRuntime (Chromium/Firefox/WebKit)
│
├── scheduler/               # Scheduling & retry
│   ├── queue.py             # PriorityQueue, TaskRunner
│   ├── cron.py              # CronParser, CronScheduler
│   └── retry.py             # RetryPolicy, RetryManager, @retry decorator
│
├── evolution/               # Self-healing & genetic optimization
│   ├── engine.py             # GeneticEngine, EvolutionCandidate
│   └── fixer.py             # AdapterFixer, SelfHealingAdapter
│
├── ai_pipeline/             # AI routing & generation
│   ├── pipeline.py          # AIPipeline, AIRouter
│   └── models.py            # PipelineConfig, PipelineContext
│
└── cli.py                   # CLI entry point
```

---

## Adapters

| Adapter | Game Type | Key Capabilities |
|---------|-----------|-----------------|
| `SlotGameAdapter` | Slot machines | auto_spin, bet_min/max/up/down, collect, free_spin, gamble, skip_bonus |
| `PokerGameAdapter` | Video poker | bet, deal, hold/discard, collect |
| `ArcadeGameAdapter` | Arcade | generic actions, score tracking |

Create adapters via the registry factory:

```python
from crawlforge.adapter import get_registry, create_adapter

registry = get_registry()
registry.register(SlotGameAdapter, game_name="my_slot")

adapter = create_adapter("my_slot", runtime=my_runtime)
```

---

## CLI Usage

```bash
# List all registered adapters
crawlforge list

# Run a game crawler (dry-run mode)
crawlforge run slot_machine --spins 100 --goal auto

# List checkpoints
crawlforge checkpoint ls
crawlforge checkpoint ls --game TestSlot --session abc123

# Diff two checkpoints
crawlforge checkpoint diff --id1 abc123 --id2 def456

# Restore from checkpoint
crawlforge checkpoint restore --checkpoint-id abc123

# Export data
crawlforge export slot_machine --format csv --output-dir ./exports

# Add scheduled task (validates cron expression)
crawlforge schedule slot_machine "*/5 * * * *"
```

---

## Running Examples

```bash
# Slot machine demo
python examples/slot_machine_demo.py

# Full framework demo
python examples/full_demo.py
```

Both demos use **mocked runtimes** — no real device or browser needed.

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Integration tests only
pytest tests/test_integration.py -v

# With coverage
pytest tests/ --cov=crawlforge --cov-report=term-missing
```

---

## Module Status

| Module | Status | Tests |
|--------|--------|-------|
| `checkpoint` | ✅ Implemented | `test_checkpoint_manager.py` |
| `adapter` | ✅ Implemented | `test_integration.py` |
| `data` | ✅ Implemented | `test_data_collector.py` |
| `scheduler` | ✅ Implemented | `test_scheduler.py` |
| `evolution` | ✅ Implemented | `test_evolution.py` |
| `runtimes` | ✅ Implemented | — |
| `detector` | ✅ Implemented | `test_slot_detector.py` |
| `cli` | ✅ Implemented | — |
| `examples` | ✅ Implemented | — |
| `benchmarks` | ✅ Implemented | — |
| `mypy` | ✅ Configured | — |

---

## Version

`0.3.0` — AI-Driven Multi-Game Crawler Framework

**Author:** CrawlForge Team
