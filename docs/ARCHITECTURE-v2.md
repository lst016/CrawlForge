# CrawlForge v2 Architecture Proposal

## Status: Draft for Review

---

## 1. Executive Summary

**Current state:** A minimal, manually-designed crawler framework with hardcoded adapter stubs and placeholder AI generation.

**Problem:** The current architecture treats AI-generated code as an afterthought — `AIGenerator` is a stub, `generate_adapter()` raises `NotImplementedError`, and the "self-evolving" claim is hollow. The adapter pattern alone cannot support dynamic, AI-generated code that must evolve in production.

**Recommendation:** Rebalance the architecture around three core principles borrowed from PantheonOS's evolvability, Autono's ReAct loops, and ATX's robust runtime abstraction — then add what these projects lack: a proper **AI Generation Pipeline** and a **Feedback-Driven Evolution System**.

---

## 2. Architecture Critique

### 2.1 What's Over-Engineered

| Area | Problem |
|------|---------|
| `AdapterRegistry` singleton + MD5 key hashing | Registry is a singleton with a toy in-memory dict. MD5-based keys are unnecessary complexity. |
| `RuntimeType` enum coupling | Embedding `RuntimeType` inside `adapter.py` creates a import dependency between the adapter contract and specific runtime implementations. |
| `crawlforge/runtimes/` as separate top-level dir | The project has `runtimes/` at top-level AND `crawlforge/runtimes/` inside the package. Double directory, unclear which is canonical. |
| `_generation_history` in `AIGenerator` | In-memory list with no persistence, no query interface, no eviction. |
| `evolve_adapter()` returning `bool` | A boolean is insufficient signal. No diff, no confidence score, no rollback. |

### 2.2 What's Missing

| Missing Component | Impact |
|-------------------|--------|
| **Dynamic Code Loader** | `generate_adapter()` cannot actually instantiate generated code — it prints code and raises `NotImplementedError`. The entire AI-generation pipeline is vaporware. |
| **AI Generation Pipeline** | No staged pipeline: screenshot → vision analysis → code generation → sandboxed compilation → test → deploy. |
| **Feedback/Evaluation Loop** | No way to observe failures and feed them back into the generator. The `evolve()` method has no data to work with. |
| **Sandbox/Quarantine Layer** | AI-generated code is executed with the same privileges as the runtime. No sandbox, no bytecode verification, no execution guardrails. |
| **Execution Recorder** | No trace of what actions were taken, in what order, with what screenshots before/after. |
| **Multi-Game Coordination** | Zero support for orchestrating across multiple games simultaneously (e.g., farming 5 games in parallel). |
| **Error Classification** | All errors are treated as strings. No taxonomy: transient vs permanent, UI-change vs infrastructure, expected vs unexpected. |
| **Recovery Strategies** | No retry budgets, no fallback runtimes, no graceful degradation. |
| **Adapter Versioning** | No concept of adapter versions, hot-swap, or rollback. |
| **Configuration/Profile System** | No per-adapter config, no environment variables, no secrets management. |
| **Logging/Tracing Infrastructure** | `print()` debugging, no structured logs, no distributed tracing. |

### 2.3 What's Fine (Keep)

- **`GameState` / `Action` / `GameData` dataclasses** — Clean, minimal, right level of abstraction.
- **`Runtime` ABC** — Sound interface design. Each runtime (ADB, Playwright) implements it correctly.
- **Async-first design** — Good choice for I/O-bound automation.

---

## 3. Reference Architecture Analysis

### 3.1 ATX (⭐1601) — What to Steal

ATX (openatx/atx) is the gold standard for mobile automation. Key lessons:

```
ATX Strengths:
├── minitouch — Low-level, precise touch injection
├── uiautomator2 — Robust UI hierarchy access
├── ADB wrapper — Battle-tested device management
└── Pattern matching — Template screenshots for reliability

CrawlForge should:
1. Steal ATX's "template + image recognition" fallback strategy
   (when AI UI detection fails, fall back to template matching)
2. Steal ATX's connection retry/backoff logic
3. Steal ATX's device pool management
```

### 3.2 Autono (⭐209) — What to Steal

Autono implements ReAct (Reasoning + Acting) loops for autonomous agents:

```
Autono Pattern:
observe → reason → act → observe → ...

CrawlForge should:
1. Make GameAdapter.generate_action() a ReAct loop:
   - Think: Analyze state (reasoning trace)
   - Act: Execute action
   - Observe: Capture result screenshot
   - Evaluate: Did it work? If not, retry or escalate
2. Use structured output (JSON) for all AI reasoning traces
   so they can be stored and replayed
```

### 3.3 PantheonOS (⭐353) — What to Steal

PantheonOS is designed as an **evolvable distributed agent framework**:

```
PantheonOS Patterns:
├── Modular agents with hot-swap capability
├── Feedback loops at multiple time scales (tick/cycle/epoch)
├── Evolutionary selection (test variants, keep winners)
└── Pluggable observation/execution backends

CrawlForge should:
1. Adopt the "tick/cycle/epoch" time scale model:
   - Tick: Single action execution
   - Cycle: Detect → Act → Evaluate → Retry (within a session)
   - Epoch: Full evolve/adapt cycle across sessions
2. Implement "agent hot-swap" — swap adapter implementation
   without restarting the runtime
3. Add a "selection" step to evolution: generate N variants,
   run smoke test, keep best
```

### 3.4 OpenHarness (⭐48) — What to Steal

OpenHarness is OpenClaw's own harness framework. Key lessons:

```
OpenHarness Patterns:
├── Tight integration between harness + AI model
├── First-class state management and context passing
├── Explicit capability negotiation between agent and target
└── Built-in anti-detection measures

CrawlForge should:
1. Add explicit "capability negotiation" — adapter declares
   what it can detect/execute; runtime verifies support
2. Integrate anti-detection from day one (not bolted on later)
3. Use OpenHarness's "session" concept as the unit of work
```

---

## 4. Proposed Architecture v2

### 4.1 Directory Structure

```
CrawlForge/
├── pyproject.toml
├── README.md
├── src/
│   └── crawlforge/
│       ├── __init__.py
│       ├── api.py                 # Public API (CrawlForge orchestrator)
│       │
│       ├── core/
│       │   ├── adapter.py         # Adapter contracts (GameAdapter ABC)
│       │   ├── game_state.py       # GameState, Action, GameData
│       │   └── exceptions.py      # Typed exception hierarchy
│       │
│       ├── runtime/
│       │   ├── base.py            # Runtime ABC
│       │   ├── adb_runtime.py     # Android via ADB
│       │   ├── playwright_runtime.py  # Browser via Playwright
│       │   ├── win32_runtime.py   # PC games (future)
│       │   └── http_runtime.py    # REST API games (future)
│       │
│       ├── registry/
│       │   ├── adapter_registry.py  # Adapter storage + discovery
│       │   ├── versioned_adapter.py  # Versioning + hot-swap
│       │   └── adapter_store.py    # File/DB-backed persistence
│       │
│       ├── generator/              # AI CODE GENERATION PIPELINE
│       │   ├── pipeline.py        # Stage-by-stage pipeline
│       │   ├── stages/
│       │   │   ├── analyzer.py    # Stage 1: Screenshot → UI semantics
│       │   │   ├── coder.py       # Stage 2: Semantics → Python code
│       │   │   ├── compiler.py    # Stage 3: Code → sandboxed module
│       │   │   └── tester.py      # Stage 4: Smoke test generated code
│       │   ├── sandbox.py         # Sandboxed code execution
│       │   ├── loader.py          # Dynamic module loading
│       │   └── prompts/
│       │       ├── analyzer_prompt.md
│       │       ├── coder_prompt.md
│       │       └── evolver_prompt.md
│       │
│       ├── evolution/              # SELF-EVOLUTION FEEDBACK LOOP
│       │   ├── feedback_collector.py  # Gather execution traces
│       │   ├── error_classifier.py    # Categorize failures
│       │   ├── variant_selector.py   # Selection among N variants
│       │   ├── rollback_manager.py    # Hot-swap + rollback
│       │   └── metrics.py         # Performance/accuracy metrics
│       │
│       ├── execution/              # ACTION EXECUTION + REACT LOOP
│       │   ├── executor.py        # Single action executor
│       │   ├── react_loop.py       # ReAct loop (reason + act + observe)
│       │   ├── retry_policy.py    # Retry budgets + backoff
│       │   ├── recovery.py         # Recovery strategies
│       │   └── trace.py           # Execution recorder (trace log)
│       │
│       ├── coordinator/            # MULTI-GAME COORDINATION
│       │   ├── session.py         # Per-game session
│       │   ├── session_pool.py    # Pool of sessions (parallel games)
│       │   ├── scheduler.py       # Cross-session scheduling
│       │   └── resource_gate.py   # Throttle concurrent runtime access
│       │
│       ├── config/
│       │   ├── loader.py          # YAML/JSON config loading
│       │   └── schemas.py         # Pydantic config schemas
│       │
│       └── utils/
│           ├── screenshot.py      # Screenshot utilities
│           ├── image_match.py     # Template matching fallback
│           └── logging.py         # Structured logging setup
│
├── adapters/                       # Community/adapter registry (pre-built)
│   └── README.md
│
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

**Key structural changes:**
- `src/crawlforge/` is the canonical source (src-layout for better packaging)
- `generator/` is elevated to a first-class package, not a single stub file
- `evolution/` is a new first-class package (currently completely absent)
- `execution/` separates the ReAct loop from the runtime
- `coordinator/` handles multi-game orchestration (currently absent)

---

### 4.2 AI Generation Pipeline (New)

The current `AIGenerator` is a monolithic stub. The proposed pipeline has **4 distinct stages**:

```
Stage 1: ANALYZE
───────────────
Input:  Screenshot (bytes) + Game context (name, type)
Output: UI Semantic Map (JSON)
  - Identified UI elements (button regions, text fields, indicators)
  - Game phase classification
  - Known-invariants (UI that rarely changes)
  - Anomalies detected

Stage 2: GENERATE
─────────────────
Input:  UI Semantic Map + Game type template
Output: Python source code (string)
  - GameAdapter subclass
  - detect_state(), generate_action(), extract_data()
  - Embedded UI element selectors

Stage 3: COMPILE + SANDBOX
──────────────────────────
Input:  Python source code
Output: Loaded, verified Python module (or error list)
  - Syntax check
  - Import validation (blocked list for os, subprocess, etc.)
  - Bytecode compilation
  - Smoke test: can the class be instantiated?

Stage 4: TEST
─────────────
Input:  Loaded adapter module + sandbox runtime
Output: Test report (pass/fail per method)
  - Run detect_state() against known screenshot
  - Run generate_action() with mock state
  - Verify extract_data() returns expected schema
  - On failure → return error details to generator for fix
```

**Failure at any stage returns structured error to previous stage for retry.**

### 4.3 Self-Evolution Feedback Loop (New)

```
┌─────────────────────────────────────────────────────────────────┐
│                      EVOLUTION EPOCH CYCLE                       │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ COLLECT  │───▶│ CLASSIFY │───▶│  FIX     │───▶│ SELECT   │  │
│  │ Feedback │    │ Errors   │    │ Variants │    │ Best     │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │                                               │        │
│       │         ┌─────────────────────────┐            │        │
│       └────────▶│  Rollback Manager       │◀───────────┘        │
│                 │  (keep last N versions) │                     │
│                 └─────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

**Time Scales:**
- **Tick**: Single action → immediate retry (1-2 attempts)
- **Cycle**: Full goal attempt → classify failure → retry with adaptation
- **Epoch**: After N cycles → full adapter regeneration

### 4.4 Multi-Game Coordination (New)

```python
# Example: Farm 5 games in parallel, each with independent session
pool = SessionPool(max_concurrent=3)  # Throttle to 3 runtimes

sessions = [
    pool.acquire("原神",     runtime=adb),
    pool.acquire("崩铁",     runtime=adb),
    pool.acquire("阴阳师",   runtime=adb),
]

async with asyncio.TaskGroup() as tg:
    for session in sessions:
        tg.create_task(session.run_goal("领取日常奖励"))
```

- **Session**: One adapter + one runtime + one trace log
- **SessionPool**: Manages concurrent runtime access, throttling, health checks
- **Scheduler**: Priority-based scheduling when resources are contended
- **ResourceGate**: Ensures only 1 action per device at a time (prevents input conflicts)

---

### 4.5 Error Handling & Recovery (Expanded)

**New Exception Hierarchy:**

```
CrawlForgeError (base)
├── AdapterError
│   ├── AdapterCodeError      # Generated code failed to load
│   ├── AdapterExecutionError # detect_state / generate_action crashed
│   └── AdapterVersionError   # Incompatible version
├── RuntimeError
│   ├── RuntimeConnectionError  # Device/browser unreachable
│   ├── RuntimeExecutionError   # Action execution failed
│   └── RuntimeTimeoutError
├── EvolutionError
│   ├── FeedbackCollectionError
│   ├── VariantSelectionError
│   └── RollbackError
└── CoordinatorError
    ├── SessionPoolExhaustedError
    └── ResourceContentionError
```

**Recovery Strategies:**

| Error Type | Recovery Strategy |
|------------|-------------------|
| `RuntimeConnectionError` | Exponential backoff reconnect (max 5 attempts) |
| `AdapterExecutionError` (transient) | Retry same action 1-2x, then escalate to ReAct retry |
| `AdapterExecutionError` (permanent) | Trigger `evolve()` for this adapter, rollback if new version fails |
| `RuntimeTimeoutError` | Fallback to alternative runtime if available |
| `AdapterCodeError` | Return to generation pipeline with error details |

---

## 5. Key Component Specifications

### 5.1 Dynamic Code Loader (Critical Path)

The current design cannot instantiate AI-generated code. This must be fixed:

```python
# Proposed: sandboxed loader in generator/loader.py
import ast
import sys
from typing import Optional

ALLOWED_IMPORTS = {
    "asyncio", "typing", "dataclasses", "enum",
    "pathlib", "json", "time", "random",
    # Adapter-specific
    "crawlforge.core", "crawlforge.runtime",
}
BLOCKED_BUILTINS = {"open", "eval", "exec", "__import__", "compile"}

class SandboxedLoader:
    def load_module(self, source_code: str, module_name: str) -> Optional[types.ModuleType]:
        # 1. Parse AST
        tree = ast.parse(source_code)
        
        # 2. Validate: no blocked imports or builtins
        self._check_imports(tree)
        self._check_builtins(tree)
        
        # 3. Compile to bytecode
        bytecode = compile(tree, f"<{module_name}>", "exec")
        
        # 4. Create sandboxed namespace
        namespace = {"__name__": module_name, "__builtins__": self._safe_builtins()}
        
        # 5. Execute in isolated namespace
        exec(bytecode, namespace)
        
        return types.ModuleType(module_name)
```

### 5.2 ReAct Loop (from Autono)

```python
class ReActLoop:
    def __init__(self, adapter: GameAdapter, runtime: Runtime, max_cycles: int = 10):
        self.adapter = adapter
        self.runtime = runtime
        self.max_cycles = max_cycles
        self.trace: list[ActionTrace] = []

    async def run(self, goal: str) -> GameData:
        for cycle in range(self.max_cycles):
            # OBSERVE
            screenshot = await self.runtime.screenshot()
            state = await self.adapter.detect_state(screenshot)

            # REASON
            action = await self.adapter.generate_action(state, goal)

            # ACT
            await self.runtime.execute(action)
            self.trace.append(ActionTrace(cycle, state, action))

            # EVALUATE (next iteration or explicit check)
            # If goal reached → extract and return
        raise MaxCyclesExceededError(goal)
```

### 5.3 Feedback Collector

```python
@dataclass
class ActionTrace:
    cycle: int
    state_before: GameState
    action: Action
    state_after: Optional[GameState]
    error: Optional[str]
    duration_ms: float

class FeedbackCollector:
    def record(self, trace: ActionTrace):
        # Persist trace + screenshot pair
        self.storage.append(trace)

    def get_recent_failures(self, adapter_id: str, limit: int = 20) -> list[ActionTrace]:
        return [t for t in self.storage if t.error and t.adapter_id == adapter_id][-limit:]
```

---

## 6. Implementation Priorities

### Phase 1 (Foundation — 2-3 weeks)
1. **Sandboxed code loader** — enables actual AI-generated adapter instantiation
2. **AI Generation Pipeline** — 4-stage pipeline with proper error propagation
3. **Structured Exception Hierarchy** — replaces all stringly-typed errors
4. **Execution Trace** — every action logged with before/after screenshots

### Phase 2 (Intelligence — 2-3 weeks)
5. **ReAct Loop** — explicit reasoning trace per action
6. **Error Classifier** — categorizes failures for smarter recovery
7. **Feedback Collector** — persists traces across sessions
8. **Retry Policy Engine** — per-adapter, per-error-type retry configs

### Phase 3 (Evolution — 2-3 weeks)
9. **Evolutionary Feedback Loop** — generate variants, smoke test, select best
10. **Rollback Manager** — keeps last 3 versions, hot-swaps on failure
11. **Variant Selector** — generates N candidates, evaluates, promotes winner
12. **Metrics Dashboard** — track adapter accuracy over time

### Phase 4 (Coordination — 1-2 weeks)
13. **Session Pool** — parallel multi-game sessions
14. **Resource Gate** — prevents concurrent access to same device
15. **Cross-Session Scheduler** — prioritizes and schedules work across sessions

---

## 7. What NOT to Build (Yet)

| Rejected Idea | Reason |
|---------------|--------|
| Distributed agent network | Over-engineered for single-machine game automation |
| Language-agnostic adapter IR | Python-only adapters is fine; the complexity isn't worth it |
| Formal verification of generated code | Too ambitious; sandbox + smoke test is sufficient |
| Plugin marketplace | Future concern; not relevant to core architecture |
| Multi-user access control | Single-user tool by design |

---

## 8. Summary of Changes

| Component | Current | Proposed |
|-----------|---------|----------|
| `AIGenerator` | Single stub file, `NotImplementedError` | Full 4-stage pipeline with sandbox |
| `evolve()` | Placeholder returning `bool` | Full epoch cycle with variant selection |
| Error handling | Stringly-typed, no taxonomy | Typed exception hierarchy + recovery policies |
| Multi-game | None | `SessionPool` + `ResourceGate` |
| Adapter loading | `print(code)` then crash | Sandboxed `ast` compilation + `exec` in isolated namespace |
| Code storage | In-memory `_generation_history` | Persistent `AdapterStore` with versioning |
| Execution trace | None | `ActionTrace` with before/after screenshots |
| Config | Hardcoded in `__init__` | Pydantic schemas + YAML loading |
| Runtimes directory | Duplicated top-level and inside package | Single canonical location under `src/crawlforge/runtime/` |

---

## 9. Open Questions

1. **Code execution security**: How far should sandboxing go? A malicious adapter could still DoS the process. Consider running each adapter in a subprocess or thread with resource limits.

2. **AI model choice**: The current design assumes a single `model` parameter. In practice, different stages may need different models (e.g., vision for analyzer, code for coder, reasoning for evolver). How should the pipeline select models?

3. **Evolution trigger**: When should a new evolution epoch start? After N failures? After a game update? Manually? The policy needs definition.

4. **Adapter version storage**: Where are old versions stored? File system? SQLite? The current registry is just in-memory JSON export.

5. **Real-time vs batch**: Is CrawlForge meant for real-time game farming or batch data collection? This affects the ReAct loop design (eager vs deferred evaluation).

---

*End of Architecture Proposal v2*
*Author: Senior AI Systems Architect (Subagent)*
*Date: 2026-04-02*
