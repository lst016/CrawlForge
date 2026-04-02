# ARCHITECTURE-v3.md — CrawlForge v3 Full Architecture

> **Version:** 3.0  
> **Date:** 2026-04-02  
> **Target:** Slot Game Crawlers + Competitor Activity Intelligence

---

## 1. System Overview

CrawlForge v3 is a **self-evolving, multi-runtime crawler framework** for automated slot game interaction, competitor activity monitoring, and game-data collection. It combines the checkpoint/recovery strength of Hive, the ReAct agentic loop of Autono, the genetic evolution of PantheonOS, and the visual robustness of bombcrypto-bot.

### Core Capabilities

| Capability | Implementation |
|---|---|
| AI Game Recognition | Vision + ReAct loop (MODULE-03, 04) |
| Competitor Activity Detection | Web scraping + AI extraction (MODULE-09) |
| Slot Game Automation | Template matching + uiautomator2 (MODULE-07, 02) |
| Algorithm Data Collection | Reel-stop sampling + statistical analysis (MODULE-09) |
| Self-Healing | Checkpoint + recovery + WebSocket observability (MODULE-05) |
| Self-Evolution | Genetic crossover + fitness evaluation (MODULE-06) |

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      CrawlForge v3                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐  │
│  │  Scheduler  │──▶│  Runtime    │──▶│  Slot Game      │  │
│  │  (MODULE-10)│   │  Abstraction│   │  Adapter        │  │
│  └──────┬──────┘   │  (MODULE-02)│   │  (MODULE-08)    │  │
│         │          └──────┬──────┘   └────────┬────────┘  │
│         │                 │                    │           │
│  ┌──────▼────────────────▼────────────────────▼───────┐  │
│  │              AI Pipeline (MODULE-03)               │  │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐  │  │
│  │  │ Analyze  │→│ Generate │→│Sandbox │→│  Test  │  │  │
│  │  └──────────┘ └──────────┘ └────────┘ └────────┘  │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │           ReAct Loop (MODULE-04)                   │  │
│  │  ┌────────┐ ┌───────┐ ┌────────┐ ┌──────────────┐ │  │
│  │  │ Observe│→│ Think │→│  Act   │→│  Reflect     │ │  │
│  │  └────────┘ └───────┘ └────────┘ └──────────────┘ │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │         Evolution Engine (MODULE-06)               │  │
│  │  Genetic: Select → Crossover → Mutate → Evaluate   │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │        Checkpoint System (MODULE-05)               │  │
│  │  Save ──▶ WebSocket ──▶ Recover ──▶ Self-Heal      │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │                                  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │        Template Matching (MODULE-07)                │  │
│  │  OpenCV + Threshold Config + Visual Fallback         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Foundation (MODULE-01)                        │  │
│  │  Dataclasses + Exceptions + Base Interfaces           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Data Collector (MODULE-09)                   │  │
│  │  Reel Stops + RTP + Activity + Algorithm Analysis    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Module Dependency Graph

```
MODULE-01 (Foundation)
    └── All other modules depend on it

MODULE-02 (Runtime Abstraction)
    ├── depends on MODULE-01
    └── used by MODULE-08, MODULE-10

MODULE-03 (AI Pipeline)
    ├── depends on MODULE-01, MODULE-02
    └── used by MODULE-04, MODULE-06

MODULE-04 (ReAct Loop)
    ├── depends on MODULE-01, MODULE-03
    └── used by MODULE-08, MODULE-06

MODULE-05 (Checkpoint)
    ├── depends on MODULE-01
    └── used by MODULE-08, MODULE-10

MODULE-06 (Evolution)
    ├── depends on MODULE-01, MODULE-03, MODULE-04
    └── used by MODULE-10 (scheduled evolution)

MODULE-07 (Template Matching)
    ├── depends on MODULE-01
    └── used by MODULE-02, MODULE-08

MODULE-08 (Slot Game Adapter)
    ├── depends on MODULE-01, MODULE-02, MODULE-04, MODULE-05, MODULE-07
    └── used by MODULE-09, MODULE-10

MODULE-09 (Data Collector)
    ├── depends on MODULE-01, MODULE-08
    └── used by MODULE-06, MODULE-10

MODULE-10 (Scheduler)
    ├── depends on MODULE-01, MODULE-02, MODULE-05, MODULE-08, MODULE-09
    └── top-level orchestrator
```

---

## 4. Runtime Abstraction (MODULE-02)

### Supported Runtimes

| Runtime | Use Case | Priority |
|---|---|---|
| **ADB + uiautomator2** | Android emulators/devices | Primary |
| **Playwright** | Web-based slot games | Secondary |
| **OpenCV** | Visual fallback for all runtimes | Fallback |

### Runtime Selection Logic

```python
def select_runtime(game_type: GameType) -> Runtime:
    if game_type.is_android_app:
        return Runtime.ADB_UIAUTOMATOR2
    elif game_type.is_web_game:
        return Runtime.PLAYWRIGHT
    else:
        return Runtime.OPENCV_VISUAL
```

---

## 5. Data Flow

### Slot Game Automation Flow

```
1. Scheduler (MODULE-10)
   └── Picks game from queue, selects runtime

2. Slot Game Adapter (MODULE-08)
   ├── Template Matching (MODULE-07) → finds spin button, balance
   ├── State Detection → spin/freespin/bonus states
   └── Reel/stop capture

3. ReAct Loop (MODULE-04)
   ├── OBSERVE: screenshot → AI vision analysis
   ├── THINK: decide action (spin / collect bonus / etc)
   ├── ACT: execute via Runtime Abstraction (MODULE-02)
   └── REFLECT: validate outcome, update state

4. Data Collector (MODULE-09)
   ├── Records reel stops, balance changes
   ├── Computes RTP, volatility, hit frequency
   └── Extracts competitor activity info

5. Checkpoint (MODULE-05)
   └── Saves state after every spin cycle

6. Evolution (MODULE-06)
   └── Evaluates session fitness, evolves strategies
```

---

## 6. Cross-Cutting Concerns

### 6.1 WebSocket Observability (from Hive)
- All modules emit events via `CrawlForgeEvents` bus
- WebSocket server streams events to dashboard
- Structured logging with trace IDs

### 6.2 Self-Healing (from Hive)
- On runtime failure → automatic retry with exponential backoff
- On template mismatch → trigger MODULE-07 re-calibration
- On crash → checkpoint recovery via MODULE-05

### 6.3 @ability Decorator (from Autono)
- All tool functions decorated with `@ability`
- MCP protocol exposes abilities to external agents
- Ability registry with version tracking

### 6.4 Genetic Evolution (from PantheonOS)
- Population: strategy genomes (spin timing, bet sizing, game selection)
- Fitness: session ROI + data collection completeness
- Selection: tournament selection
- Crossover: uniform crossover
- Mutation: Gaussian perturbation

---

## 7. File Structure

```
CrawlForge/
├── src/
│   └── crawlforge/
│       ├── __init__.py
│       ├── foundation/           # MODULE-01
│       │   ├── models.py        # dataclasses
│       │   ├── exceptions.py
│       │   └── interfaces.py
│       ├── runtime/             # MODULE-02
│       │   ├── adb_runtime.py
│       │   ├── playwright_runtime.py
│       │   └── runtime_manager.py
│       ├── ai_pipeline/         # MODULE-03
│       │   ├── analyzer.py
│       │   ├── generator.py
│       │   ├── sandbox.py
│       │   └── tester.py
│       ├── react_loop/          # MODULE-04
│       │   ├── loop.py
│       │   ├── abilities.py     # @ability decorator
│       │   └── mcp_protocol.py
│       ├── checkpoint/          # MODULE-05
│       │   ├── saver.py
│       │   ├── recovery.py
│       │   └── websocket_events.py
│       ├── evolution/           # MODULE-06
│       │   ├── population.py
│       │   ├── crossover.py
│       │   └── fitness.py
│       ├── template_matching/    # MODULE-07
│       │   ├── matcher.py
│       │   ├── threshold_config.py
│       │   └── calibrator.py
│       ├── slot_game/           # MODULE-08
│       │   ├── adapter.py
│       │   ├── state_machine.py
│       │   ├── templates/        # provider-specific templates
│       │   └── activity_extractor.py
│       ├── data_collector/      # MODULE-09
│       │   ├── reel_tracker.py
│       │   ├── rtp_calculator.py
│       │   └── activity_analyzer.py
│       └── scheduler/            # MODULE-10
│           ├── dispatcher.py
│           ├── resource_pool.py
│           └── multi_game_queue.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── configs/
│   ├── games.yaml               # game definitions
│   ├── evolution.yaml           # evolution hyperparams
│   └── runtime.yaml             # runtime configs
└── docs/
    ├── ARCHITECTURE-v3.md
    ├── ITERATION-PLAN.md
    └── modules/
        ├── MODULE-01-foundation.md
        ├── MODULE-02-runtime.md
        ├── MODULE-03-ai-pipeline.md
        ├── MODULE-04-react-loop.md
        ├── MODULE-05-checkpoint.md
        ├── MODULE-06-evolution.md
        ├── MODULE-07-template-matching.md
        ├── MODULE-08-slot-game-adapter.md
        ├── MODULE-09-data-collector.md
        └── MODULE-10-scheduler.md
```

---

## 8. Configuration Schema

### games.yaml
```yaml
games:
  - id: "pragmatic_play_gates_of_olympus"
    provider: "pragmatic_play"
    type: "slot"
    runtime: "adb_uiautomator2"
    templates:
      spin_button: "templates/pgo_spin.png"
      balance: "templates/pgo_balance.png"
    reel_config:
      rows: 6
      cols: 5
      paylines: 20
    activity_selectors:
      bonus_banner: "[data-testid='bonus-banner']"
      promo_popup: ".promo-modal"
```

---

## 9. Deployment Notes

- **Android:** ADB must be on PATH; uiautomator2 server on port 9008
- **Playwright:** Chromium with persistent context recommended for web games
- **OpenCV:** Requires Python 3.10+; opencv-python >= 4.8
- **WebSocket:** Runs on port 8765 by default; configurable
- **Evolution:** GPU recommended for large populations; CPU fallback available

---

## 10. Version History

| Version | Key Change |
|---|---|
| v1 | Basic crawler with ADB + uiautomator2 |
| v2 | Added ReAct loop + AI pipeline |
| v3 (this) | Full modular architecture + evolution + checkpoint |
