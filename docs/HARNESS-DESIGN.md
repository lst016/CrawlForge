# HARNESS-DESIGN.md — AI Agent Harness Framework for CrawlForge

**Version:** 1.0  
**Date:** 2026-04-02  
**Status:** Draft — Framework Design Specification  

---

## Table of Contents

1. [What Is an AI Harness?](#1-what-is-an-ai-harness)
2. [Design Principles for Game Automation Harnesses](#2-design-principles-for-game-automation-harnesses)
3. [Reference Architecture](#3-reference-architecture)
4. [Data Flow Diagrams](#4-data-flow-diagrams)
5. [State Machines](#5-state-machines)
6. [API Design](#6-api-design)
7. [Code Generation Pipeline](#7-code-generation-pipeline)
8. [Self-Evolution Loop](#8-self-evolution-loop)
9. [Multi-Game Concurrency](#9-multi-game-concurrency)
10. [Minimal Viable Harness (MVH)](#10-minimal-viable-harness-mvh)
11. [Reference Project Analysis](#11-reference-project-analysis)
12. [Implementation Roadmap](#12-implementation-roadmap)

---

## 1. What Is an AI Harness?

### 1.1 Core Definition

An **AI Harness** is the execution framework that surrounds one or more AI agents, providing:

| Responsibility | Description |
|---|---|
| **Orchestration** | Drives agent lifecycle (spawn, monitor, retire) |
| **Context Management** | Supplies structured context to agents (game state, memory, tools) |
| **Action Execution** | Takes agent outputs and translates them into real system actions |
| **Feedback Collection** | Collects execution results and feeds them back for learning |
| **Self-Evolution** | Modifies its own prompts, tools, or agent behavior based on feedback |

Think of it as the **operating system for AI agents** — it provides I/O, scheduling, and adaptation, while agents themselves are the "programs."

```
┌─────────────────────────────────────────────────┐
│                   HARNESS                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Agent #1  │  │Agent #2  │  │Agent #N  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │             │              │
│  ┌────▼─────────────▼─────────────▼────┐        │
│  │      EXECUTION ENGINE               │        │
│  │  (Action Translation + Sandbox)     │        │
│  └────────────────┬────────────────────┘        │
│                   │                             │
│  ┌────────────────▼────────────────────┐        │
│  │      FEEDBACK + EVOLUTION LOOP      │        │
│  └─────────────────────────────────────┘        │
└─────────────────────────────────────────────────┘
         │                           ▲
         ▼                           │
    ┌─────────┐               ┌─────────────┐
    │  GAME   │               │   LEARNED   │
    │  STATE  │               │   MEMORY    │
    └─────────┘               └─────────────┘
```

### 1.2 Harness vs. Agent — The Distinction

| Aspect | Agent | Harness |
|---|---|---|
| **Focus** | "What should I do?" (reasoning) | "How do I run agents correctly?" (execution) |
| **Outputs** | Thoughts, plans, tool calls | Action sequences, context bundles |
| **Adaptation** | Learns task knowledge | Learns execution strategy |
| **Boundary** | Cognitive / decision-making | Operational / environmental |

**Key insight:** The harness does not reason. It *executes, observes, and adapts*. The agent reasons. The harness translates reasoning into action and action into learning.

---

## 2. Design Principles for Game Automation Harnesses

### 2.1 Hard Requirements

```
P0 — Must Have
├── Deterministic replay — same input → same behavior
├── Sandboxed execution — game crashes don't kill harness
├── Observable state — every game tick must be inspectable
├── Human override — safety brake at all times
└── Graceful degradation — partial information still usable

P1 — Should Have
├── Parallel game instances — handle 5+ simultaneous games
├── Self-healing scripts — detect failure, regenerate code
├── Cross-game learning — generalize patterns across games
└── Versioned strategy snapshots — rollback bad evolution

P2 — Nice to Have
├── Natural language strategy editing
├── Visual script builder
├── ML-based performance prediction
└── Distributed execution across machines
```

### 2.2 The Game Automation Specifics

Game automation introduces unique harness requirements beyond general agent frameworks:

1. **Visual/Observation Layer** — Games are primarily visual; harness needs screenshot/frame ingestion
2. **Latency Sensitivity** — Action timing matters (RTS, fighting games)
3. **State Complexity** — Game state may be opaque (no API); requires OCR/Vision inference
4. **Anti-cheat Boundaries** — Must respect game ToS; harness stays in "input simulation" layer
5. **Multi-modal Inputs** — Keyboard, mouse, gamepad, in-game menus
6. **Long-running Sessions** — Hours/days of continuous operation

---

## 3. Reference Architecture

### 3.1 Global Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║                        CRAWLFORGE HARNESS                             ║
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐     ║
║  │                    ORCHESTRATION LAYER                       │     ║
║  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │     ║
║  │  │ Session  │  │  Game    │  │ Strategy │  │ Evolution│    │     ║
║  │  │ Manager  │  │ Registry │  │ Loader   │  │ Manager  │    │     ║
║  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │     ║
║  └───────┼─────────────┼─────────────┼─────────────┼───────────┘     ║
║          │             │             │             │                   ║
║  ┌───────▼─────────────▼─────────────▼─────────────▼───────────┐     ║
║  │                     CONTEXT BRIDGE                           │     ║
║  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────────────┐     │     ║
║  │  │ Game   │  │Memory  │  │  Tool  │  │ Strategy       │     │     ║
║  │  │ State  │◄─┤ Layer  │◄─┤ Bundle │◄─┤ Context        │     │     ║
║  │  │ Ingest │  │        │  │        │  │ Assembler       │     │     ║
║  │  └────┬───┘  └────────┘  └────────┘  └────────────────┘     │     ║
║  └───────┼─────────────────────────────────────────────────────┘     ║
║          │                                                           ║
║  ┌───────▼─────────────────────────────────────────────────────┐     ║
║  │                      AGENT RUNTIME                            │     ║
║  │  ┌─────────────────────────────────────────────────────┐     │     ║
║  │  │              AI CODE GENERATOR                       │     │     ║
║  │  │  (Prompt Eng + Retrieval + Synthesis)               │     │     ║
║  │  └──────────────────────┬──────────────────────────────┘     │     ║
║  │                         │                                     │     ║
║  │  ┌──────────────────────▼──────────────────────────────┐     │     ║
║  │  │              CODE EXECUTOR                          │     │     ║
║  │  │  (Sandbox + Verification + Rollback)                │     │     ║
║  │  └──────────────────────┬──────────────────────────────┘     │     ║
║  └─────────────────────────┼───────────────────────────────────┘     ║
║                            │                                          ║
║  ┌─────────────────────────▼───────────────────────────────────┐     ║
║  │                   GAME INTERFACE LAYER                       │     ║
║  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │     ║
║  │  │ Screenshot│  │ Input    │  │ Audio    │  │ Memory   │    │     ║
║  │  │ Capture  │  │ Driver   │  │ Capture  │  │ Reader   │    │     ║
║  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │     ║
║  └───────────────────────────────────────────────────────────────┘     ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 3.2 Component Inventory

| Component | Responsibility | Language |
|---|---|---|
| `SessionManager` | Track game sessions, spawn/kill agents | Python |
| `GameRegistry` | Per-game adapters, state extractors | Python |
| `StrategyLoader` | Versioned strategy profiles, hot-swap | Python |
| `EvolutionManager` | Fitness evaluation, mutation, selection | Python |
| `ContextBridge` | Assemble context for each agent tick | Python |
| `MemoryLayer` | Short-term + long-term memory (mem0/Qdrant) | Python |
| `ToolBundle` | Available actions per game type | Python + JSON |
| `AIGenerator` | Prompt construction + LLM calls | Python |
| `CodeExecutor` | Sandboxed script execution | Python (isolated) |
| `GameInterface` | Platform-specific input/screenshot | C++/Python |
| `FeedbackCollector` | Metrics, logs, replay buffers | Python |

---

## 4. Data Flow Diagrams

### 4.1 Primary Tick Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                      SINGLE TICK FLOW                            │
└─────────────────────────────────────────────────────────────────┘

  GAME STATE               HARNESS                  AGENT
  (screenshot             (this tick)               (LLM call)
   + memory)

    │                        │                        │
    ▼                        │                        │
┌────────┐                   │                        │
│Capture │◄──────────────────┘                        │
│Frame   │                                            │
└───┬────┘                                            │
    │                                                 │
    │ game_frame                                      │
    ▼                                                 │
┌────────┐    context_bundle                          │
│State   │◄────────────────────┐                      │
│Extract │                     │                      │
└───┬────┘                     │                      │
    │                          │                      │
    │ game_state               │                      │
    │ (structured JSON)        │                      │
    ▼                          │                      │
┌─────────────┐               │                      │
│Memory       │               │                      │
│Query        │◄──────────────┤                      │
│(relevant    │               │                      │
│past events) │               │                      │
└──────┬──────┘               │                      │
       │                      │                      │
       │ memory_context       │                      │
       ▼                      │                      │
┌────────────────────┐         │                      │
│Context Assembler  │◄────────┘                      │
│(state+memory+tools)│                                │
└──────┬────────────┘                                 │
       │                                               │
       │ full_context_bundle                           │
       ▼                                               │
┌─────────────────┐                                    │
│  Agent Runtime  │───────────────────────────────────►│
│  (LLM Prompt)   │  Prompt: context_bundle            │
└─────┬───────────┘                                    │
      │                                                │
      │ LLM Response (action plan + code)             │
      ▼                                                │
┌─────────────────┐                                    │
│ Code Executor   │                                    │
│ (verify+sandbox)│                                    │
└─────┬───────────┘                                    │
      │                                                │
      │ verified_action                                │
      ▼                                                │
┌─────────────────┐                                    │
│  Input Driver   │───(send to game)─────────────────►│
│                 │                                    │
└─────────────────┘                                    │
      │                                                │
      │ execution_result                               │
      ▼                                                │
┌─────────────────┐                                    │
│  Feedback      │                                    │
│  Collector     │                                    │
└─────┬───────────┘                                    │
      │                                                │
      │ tick_result                                    │
      ▼                                                │
┌─────────────────┐                                    │
│ Evolution      │                                    │
│ Manager        │                                    │
└─────────────────┘
```

### 4.2 Code Generation Pipeline (Detail)

```
┌──────────────────────────────────────────────────────────────────┐
│              AI CODE GENERATION PIPELINE                          │
└──────────────────────────────────────────────────────────────────┘

 user_goal / game_state
        │
        ▼
┌──────────────────┐
│ GOAL PARSER     │  ← Extract: objective, constraints, success criteria
│ (structured)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ RETRIEVAL BLOCK  │  ← Query vector DB for similar past strategies
│                  │    + relevant tool definitions
└────────┬─────────┘
         │ retrieved_context (top-k strategies + tools)
         │
         ▼
┌──────────────────┐
│ PROMPT BUILDER   │  ← Stitch: goal + retrieved + constraints + format
│                  │    Output format enforced: JSON {action, params, reason}
└────────┬─────────┘
         │ final_prompt
         │
         ▼
┌──────────────────┐
│ LLM CALL         │  ← Call: local MLX model OR cloud API (configurable)
│ (AIGenerator)   │
└────────┬─────────┘
         │ raw_response
         │
         ▼
┌──────────────────┐
│ OUTPUT PARSER    │  ← Parse JSON, validate schema, extract code block
│                  │  ← Fallback: regex extraction if JSON fails
└────────┬─────────┘
         │ parsed_action {action, params, code_snippet, reason}
         │
         ├───► IF mode = "direct" ──► EXECUTE IMMEDIATELY
         │
         ▼
┌──────────────────┐
│ CODE VERIFIER    │  ← Static analysis: imports, types, safety keywords
│                  │  ← Sandbox check: filesystem, network, dangerous imports
└────────┬─────────┘
         │ verified_code (or error_with_fix_request)
         │
         ▼
┌──────────────────┐
│ SANDBOX EXEC     │  ← Run in subprocess with timeout (5s default)
│                  │  ← Capture stdout/stderr, return value
└────────┬─────────┘
         │ execution_result {success, output, error, duration_ms}
         │
         ▼
┌──────────────────┐
│ FEEDBACK LOOP    │  ← Score result, store in replay buffer, trigger
│                  │    evolution if连续 failure
└──────────────────┘
```

### 4.3 Self-Evolution Loop

```
┌──────────────────────────────────────────────────────────────────┐
│                   SELF-EVOLUTION LOOP                             │
└──────────────────────────────────────────────────────────────────┘

  EXTERNAL TRIGGERS                    INTERNAL TRIGGERS
  ────────────────                     ─────────────────
  • N consecutive failures             • Fitness plateau (>10 ticks)
  • Human flag strategy                • New tool available
  • Game patch detected                • Cross-game pattern found
  • Time-based refresh                 • Memory confidence drop

         │                                    │
         └──────────────┬─────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │ EVOLUTION MANAGER │
              │ (top-level FSM)  │
              └────────┬─────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
  ┌────────────┐ ┌────────────┐ ┌─────────────┐
  │  DIAGNOSE  │ │   PLAN     │ │  VALIDATE   │
  │            │ │            │ │             │
  │ Why failed?│ │What change?│ │Does it work?│
  └─────┬──────┘ └─────┬──────┘ └──────┬──────┘
        │              │               │
        │ diagnosis    │ mutation_plan│ validated_strateg
        ▼              ▼               ▼
  ┌─────────────────────────────────────────┐
  │          MUTATION ENGINE                │
  │                                          │
  │  • Prompt mutation (system instruction)  │
  │  • Tool discovery (new action added)    │
  │  • Strategy crossover (2 games → 1)     │
  │  • Parameter tuning (thresholds, delays)│
  │  • Context window reallocation           │
  └────────────────────┬────────────────────┘
                       │
                       │ mutated_strategy
                       ▼
              ┌──────────────────┐
              │  GENETIC POOL    │
              │  (population of  │
              │   strategy vN)   │
              └────────┬─────────┘
                       │
              ┌────────▼─────────┐
              │  FITNESS EVAL    │
              │  (test on N ticks│
              │   of game replay)│
              └────────┬─────────┘
                       │ fitness_score
                       ▼
              ┌──────────────────┐
              │  SELECTION       │
              │  (tournament or  │
              │   elitism)       │
              └────────┬─────────┘
                       │ best_strategy
                       ▼
              ┌──────────────────┐
              │ DEPLOY + MONITOR │
              │ (hot-swap into   │
              │  live harness)   │
              └──────────────────┘
```

---

## 5. State Machines

### 5.1 Harness Lifecycle State Machine

```
                              ┌─────────────────┐
                              │     BOOT        │
                              │  (init config)  │
                              └────────┬────────┘
                                       │ config_ok
                              ┌────────▼────────┐
                         NO   │    IDLE         │   shutdown
          ┌───────────────────►│  (waiting)      │◄─────────┐
          │                    └────────┬────────┘          │
          │                             │ start_session    │
          │                             │                   │
          │                    ┌────────▼────────┐          │
          │                    │  INITIALIZING   │          │
          │                    │ (load game,     │          │
          │                    │  spawn agent)   │          │
          │                    └────────┬────────┘          │
          │                             │ agent_ready       │
          │                    ┌────────▼────────┐          │
          │                    │    RUNNING      │          │
          │                    │  (tick loop)    │──────────┤
          │                    └────────┬────────┘          │
          │                             │                   │
          │         ┌───────────────────┼────────────────┐  │
          │         │                   │                │  │
          │         ▼                   ▼                ▼  │
          │  ┌────────────┐     ┌────────────┐   ┌───────────┐ │
          │  │ DEGRADED   │     │  PAUSED    │   │  CRASHED  │ │
          │  │ (recover   │     │(human      │   │ (restart  │ │
          │  │  partial)  │     │ override)  │   │  agent)   │ │
          │  └────────────┘     └─────┬──────┘   └─────┬─────┘ │
          │                             │                │       │
          │                             │ resume         │       │
          │                             │                │ retry_ok
          │                             ▼                │       │
          │                      ┌────────────┐          │       │
          │                      │  RUNNING   │◄─────────┘       │
          │                      └────────────┘    max_retries    │
          │                                                 not_ok │
          │                                                 │
          └──────────────────────────────────────────────────────►IDLE
```

### 5.2 Strategy Evolution FSM

```
┌─────────────────┐  trigger   ┌─────────────────┐
│    STABLE       │───────────►│   DIAGNOSE      │
│                 │            │                 │
│ (normal ops,    │◄───────────│  (analyze       │
│  no changes)    │  no issue   │   failure       │
└─────────────────┘            └────────┬────────┘
                                       │ issue_found
                              ┌────────▼────────┐
                              │    EVOLVE       │
                              │                 │
                              │ (genetic ops    │
                              │  on strategy)   │
                              └────────┬────────┘
                                       │ candidate_ready
                              ┌────────▼────────┐
                              │   VALIDATE      │
                              │                 │
                              │ (test on replay │
                              │  or shadow run) │
                              └────────┬────────┘
                                       │ fitness > threshold
                              ┌────────▼────────┐
                              │    DEPLOY       │
                              │                 │
                              │ (atomic swap    │
                              │  strategy vN+1) │
                              └────────┬────────┘
                                       │ deployed
                              ┌────────▼────────┐
                              │    STABLE       │
                              │ (back to normal)│
                              └─────────────────┘
```

### 5.3 Agent Tick State Machine

```
┌─────────┐  tick_start   ┌─────────────┐  context_ok   ┌──────────┐
│ TICKING │──────────────►│  CONTEXT    │──────────────►│  REASON  │
└─────────┘               │  ASSEMBLING │               │          │
                          └─────────────┘               └────┬─────┘
                                │ error                       │
                                │                             │ response_ready
                                ▼                             ▼
                          ┌──────────┐              ┌─────────────────┐
                          │ RETRY   │              │    EXECUTE      │
                          │ CONTEXT │              │                 │
                          └────┬─────┘              └────────┬────────┘
                               │ retry_ok                      │
                               │ max_retries                   │ execution_done
                               ▼ no                            ▼
                         ┌──────────┐              ┌─────────────────┐
                         │ ABORT    │              │    FEEDBACK     │
                         │ TICK     │              │                 │
                         └────┬─────┘              └────────┬────────┘
                              │                               │
                              │ skip_action                   │ score_computed
                              ▼                               ▼
                        ┌──────────┐                   ┌──────────┐
                        │ IDLE     │◄─────────────────│ NEXT     │
                        │ (wait    │    tick_complete │ TICK     │
                        │  next)   │                   └──────────┘
                        └──────────┘
```

---

## 6. API Design

### 6.1 Core Harness API (Python SDK)

```python
# ─── Session Management ───────────────────────────────────────────────────

class Harness:
    """Main entry point for the CrawlForge harness."""
    
    def start_session(self, game: str, config: GameConfig) -> Session:
        """Start a new game session. Returns a Session handle."""
    
    def pause_session(self, session_id: str) -> None:
        """Freeze the tick loop. Human can take over."""
    
    def resume_session(self, session_id: str) -> None:
        """Resume from paused state."""
    
    def stop_session(self, session_id: str) -> SessionResult:
        """Gracefully stop. Returns summary + metrics."""
    
    def inject_action(self, session_id: str, action: Action) -> None:
        """Human override: inject an action directly into the queue."""


# ─── Strategy Management ──────────────────────────────────────────────────

class StrategyManager:
    """Versioned strategy profiles."""
    
    def load(self, game: str, version: str | None = None) -> Strategy:
        """Load strategy by version, or latest if None."""
    
    def save(self, strategy: Strategy) -> str:
        """Save strategy, returns version ID."""
    
    def hot_swap(self, session_id: str, strategy: Strategy) -> None:
        """Atomically replace active strategy mid-session."""
    
    def history(self, game: str) -> list[VersionInfo]:
        """List all versions for a game."""


# ─── Evolution ────────────────────────────────────────────────────────────

class EvolutionManager:
    """Genetic strategy evolution."""
    
    def diagnose(self, session_id: str) -> Diagnosis:
        """Analyze recent failures, return root cause."""
    
    def mutate(
        self, 
        strategy: Strategy, 
        mode: MutationMode = MutationMode.PROMPT_ONLY
    ) -> Strategy:
        """Apply mutation. Modes: PROMPT_ONLY, TOOL_ADD, CROSSOVER."""
    
    def validate(
        self, 
        candidate: Strategy, 
        game: str, 
        ticks: int = 100
    ) -> FitnessResult:
        """Run candidate in shadow mode, return fitness score."""
    
    def deploy(self, session_id: str, candidate: Strategy) -> None:
        """Atomic deploy validated candidate."""


# ─── Game Interface ───────────────────────────────────────────────────────

class GameInterface:
    """Per-game adapter layer."""
    
    def capture_frame(self) -> GameFrame:
        """Screenshot + optional memory read."""
    
    def send_input(self, action: Action) -> InputResult:
        """Execute action, return success + any error."""
    
    def get_state(self) -> GameState:
        """Structured game state (JSON)."""
    
    def get_available_actions(self) -> list[ActionSpec]:
        """List actions valid in current game context."""


# ─── Data Classes ─────────────────────────────────────────────────────────

@dataclass
class Action:
    type: str                          # "keyboard", "mouse", "menu"
    params: dict                       # {"key": "f2", "hold_ms": 100}
    reason: str                        # human-readable rationale
    confidence: float                   # 0.0–1.0
    strategy_version: str

@dataclass
class GameState:
    frame: GameFrame
    tick: int
    session_id: str
    extracted: dict                    # game-specific extracted state
    raw: dict                          # raw observations

@dataclass
class Strategy:
    id: str
    game: str
    version: str
    system_prompt: str                 # the evolved prompt
    tools: list[ToolDef]               # available tools
    constraints: list[str]             # hard constraints
    fitness_history: list[float]       # past fitness scores

@dataclass
class FitnessResult:
    score: float                       # 0.0–1.0
    ticks_tested: int
    failure_modes: list[str]
    improvement_over_parent: float
```

### 6.2 REST API (Harness Control Plane)

```
Harness Control Plane — Port 18889
===================================

Sessions
────────
POST   /api/v1/sessions              Create session
GET    /api/v1/sessions/{id}         Get session status
DELETE /api/v1/sessions/{id}         Stop session

Strategies
──────────
GET    /api/v1/strategies/{game}              List versions
POST   /api/v1/strategies/{game}              Create/update strategy
GET    /api/v1/strategies/{game}/{version}     Get specific version
POST   /api/v1/evolve/{game}                  Trigger evolution
GET    /api/v1/evolve/{game}/status           Evolution job status

Sessions/{id}/actions
─────────────────────
POST   /api/v1/sessions/{id}/inject   Inject human action
POST   /api/v1/sessions/{id}/pause
POST   /api/v1/sessions/{id}/resume

Metrics
───────
GET    /api/v1/metrics/{session_id}  Live metrics
GET    /api/v1/metrics/{session_id}/telemetry  Detailed telemetry
WS     /ws/sessions/{id}/feed        Live tick-by-tick feed
```

### 6.3 Agent-Orchestrator Protocol (Internal IPC)

```python
# ZeroMQ or Unix socket communication between harness components

# Messages are JSON envelopes

# Harness → Agent: context bundle each tick
{
    "type": "TICK",
    "session_id": "abc123",
    "tick": 42,
    "context": {
        "game_state": { ... },
        "memory": [ ... ],
        "tools": [ ... ],
        "constraints": [ ... ]
    }
}

# Agent → Harness: action decision
{
    "type": "ACTION",
    "tick": 42,
    "action": {"type": "keyboard", "params": {...}, "reason": "..."},
    "confidence": 0.87
}

# Harness → Agent: feedback after execution
{
    "type": "FEEDBACK", 
    "tick": 42,
    "result": "success" | "failure" | "error",
    "game_state_after": { ... },
    "fitness_delta": 0.05
}

# Harness → Agent: evolution signal
{
    "type": "STRATEGY_UPDATED",
    "old_version": "v12",
    "new_version": "v13",
    "change_summary": "Improved prompt for combat sequences"
}
```

---

## 7. Code Generation Pipeline

### 7.1 The Three Approaches (Build vs. Buy)

| Approach | How It Works | Pros | Cons |
|---|---|---|---|
| **Prompt Engineering** | Rich system prompt + context | Fast iteration, no training cost | Context window limits, token cost at scale |
| **Fine-tuning** | Train on curated game-play data | Better task-specific reasoning | Expensive, slow iteration, catastrophic forgetting |
| **Retrieval (RAG)** | Retrieve relevant past strategies | Bounded context, reusable knowledge | Retrieval quality determines everything |

**Recommended: Hybrid Retrieval + Prompt Engineering (RAG-P)**
- Fine-tune a small adapter for game-action syntax only
- Use RAG for strategic knowledge (past strategies, game patterns)
- Use prompt engineering for dynamic context (current game state)

### 7.2 Prompt Engineering Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  SYSTEM PROMPT (evolved over time)                          │
│  ─────────────────────────────────────                      │
│  You are an expert game automation agent.                   │
│  You control [GAME_NAME] via structured actions.            │
│  Rules: [CONSTRAINTS from Strategy]                         │
│  Current objective: [OBJECTIVE from ContextBundle]          │
│  Available tools: [TOOL_DEFS from Strategy]                │
│  Response format: JSON {action, params, reason, confidence} │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ + current game state
                              │ + retrieved similar past strategies
                              │ + recent feedback (what worked/failed)
                              ▼
              ┌───────────────────────────────┐
              │     FULL PROMPT (assembled)     │
              │                                │
              │  [System Prompt]                │
              │  [Game State Snapshot]          │
              │  [Retrieved Strategies (top-3)] │
              │  [Recent Feedback History]     │
              │  [Tool Definitions]             │
              │  [Output Format Spec]          │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │           LLM                 │
              │   (local MLX or cloud)        │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │     JSON Action Response      │
              │  {                            │
              │    "action": "keyboard",      │
              │    "params": {"key": "e"},    │
              │    "reason": "...",            │
              │    "confidence": 0.91         │
              │  }                            │
              └───────────────────────────────┘
```

### 7.3 Retrieval System

```python
class StrategyRetriever:
    """RAG-style retrieval for strategy context."""
    
    def __init__(self, vector_store: QdrantClient):
        self.vector_store = vector_store
        self.embedding_model = "bge-m3"  # local embedding
    
    def retrieve(
        self, 
        game_state: GameState, 
        goal: str,
        top_k: int = 3
    ) -> list[RetrievedStrategy]:
        """Retrieve most relevant past strategies."""
        
        # Build query from current situation
        query = f"""
        Game: {game_state.game}
        Objective: {goal}
        Recent events: {game_state.recent_ticks_summary}
        """
        
        results = self.vector_store.search(
            collection_name=f"strategies_{game_state.game}",
            query_vector=self.embed(query),
            limit=top_k
        )
        
        return [r.payload for r in results]
    
    def index_strategy(self, strategy: Strategy) -> None:
        """Add new strategy to retrieval index."""
        self.vector_store.add(
            collection_name=f"strategies_{strategy.game}",
            vectors={"strategy": self.embed(strategy.system_prompt)},
            payloads={"strategy": asdict(strategy)}
        )
```

### 7.4 Handling the "Last Mile" Problem

The **last mile** = translating an LLM's text output into a verified, executed, game action.

```
LLM Output (text)
      │
      ▼
┌──────────────────┐
│ JSON PARSER      │ ──► Structured Action
│ (pydantic/zod)   │     or Error
└────────┬─────────┘
         │ parse_error
         ▼
   ┌──────────────────┐
   │ REGEX FALLBACK   │ ──► Try to extract from raw text
   │ (action patterns)│     (handles malformed JSON)
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │  CODE VERIFIER   │
   │  ─────────────── │
   │  1. Syntax check │
   │  2. Import audit │
   │  3. Safety scan  │
   │     (no os, no   │
   │      subprocess)  │
   │  4. Type check   │
   └────────┬─────────┘
            │ invalid
            ▼
      ┌──────────────┐
      │  ERROR QUEUE  │ ──► Log + request retry from agent
      └──────────────┘
            │
            │ valid
            ▼
   ┌──────────────────┐
   │  SANDBOX EXEC    │
   │  ─────────────── │
   │  Subprocess      │
   │  Timeout: 5s     │
   │  Memory: 128MB   │
   │  Network: BLOCK  │
   │  Filesystem: /tmp│
   └────────┬─────────┘
            │
            │ exec_result
            ▼
   ┌──────────────────┐
   │  FEEDBACK        │
   │  ─────────────── │
   │  Record:         │
   │  • success/fail  │
   │  • execution_ms  │
   │  • output/error  │
   │  • game_state    │
   │    after         │
   └──────────────────┘
```

**Verification Steps Before Execution:**
1. **Schema validation** — pydantic model check on parsed JSON
2. **Safety keyword scan** — reject if contains `rm`, `subprocess`, `eval`, `exec`, `import os`
3. **Action whitelist** — only actions in `available_actions` list allowed
4. **Parameter bounds** — validate params against action spec (e.g., key in valid_keyset)
5. **Sandbox dry run** — test import resolution without side effects
6. **Timeout** — hard kill after N seconds

---

## 8. Self-Evolution Loop

### 8.1 Evolution Trigger Conditions

```python
EVOLUTION_TRIGGERS = {
    # Immediate triggers
    "consecutive_failures": 5,          # N failures in a row
    "fitness_drop": 0.3,                 # Fitness fell by >30% vs baseline
    "game_patch_detected": True,        # Game version mismatch
    
    # Gradual triggers
    "fitness_plateau": {                 # No improvement for N ticks
        "ticks": 200,
        "threshold": 0.01               # delta < 1%
    },
    "drift_detected": {                  # Strategy drifted too far from seed
        "max_edit_distance": 0.7,       # 70% prompt mutation
        "reset_recommended": True
    },
    
    # Scheduled triggers
    "periodic_refresh": 60 * 60 * 24,   # Force evolution every 24 hours
}

class EvolutionManager:
    def should_evolve(self, session_id: str) -> TriggerType | None:
        metrics = self.get_metrics(session_id)
        
        if metrics.consecutive_failures >= 5:
            return TriggerType.CONSECUTIVE_FAILURES
        if metrics.fitness_plateau_ticks > 200:
            return TriggerType.FITNESS_PLATEAU
        if self.game_version_mismatch(session_id):
            return TriggerType.GAME_PATCH
        return None
```

### 8.2 Mutation Operators

| Operator | Description | Risk |
|---|---|---|
| **Prompt Mutation** | Edit system prompt (synonym替换, structure reorder) | Low |
| **Tool Add/Remove** | Add new tool to bundle, or disable noisy tools | Medium |
| **Constraint Relaxation** | Loosen a constraint that may be too restrictive | Medium |
| **Cross-Over** | Blend strategy from Game A into Game B | High |
| **Parameter Tuning** | Adjust numeric constants (thresholds, delays) | Low |
| **Strategy Reset** | Roll back to known-good baseline | Low |

### 8.3 Fitness Function

```python
@dataclass
class FitnessScore:
    success_rate: float        # % of ticks with successful action execution
    goal_progress: float      # Distance toward objective (0.0–1.0)
    efficiency: float         # Speed of completion vs. baseline
    stability: float          # Variance in performance (lower = better)
    safety_score: float       # Human override frequency (higher = better)
    
    def overall(self, weights: dict = None) -> float:
        w = weights or {
            "success_rate": 0.3,
            "goal_progress": 0.4,
            "efficiency": 0.1,
            "stability": 0.1,
            "safety_score": 0.1
        }
        return sum(getattr(self, k) * v for k, v in w.items())
```

### 8.4 Genetic Selection

```python
class GeneticSelector:
    """Tournament selection with elitism."""
    
    def select(
        self, 
        population: list[Strategy], 
        fitness_scores: dict[str, float],
        tournament_size: int = 3,
        elite_count: int = 1
    ) -> list[Strategy]:
        
        # Elitism: keep top N performers unchanged
        sorted_pop = sorted(
            population, 
            key=lambda s: fitness_scores.get(s.id, 0), 
            reverse=True
        )
        elite = sorted_pop[:elite_count]
        
        # Tournament selection for rest
        remaining = sorted_pop[elite_count:]
        tournament_winners = []
        
        for _ in range(len(remaining)):
            tournament = random.sample(remaining, tournament_size)
            winner = max(tournament, key=lambda s: fitness_scores.get(s.id, 0))
            tournament_winners.append(winner)
            remaining.remove(winner)
        
        return elite + tournament_winners
```

---

## 9. Multi-Game Concurrency

### 9.1 Architecture for Parallel Games

```
┌─────────────────────────────────────────────────────────────┐
│                  HARNESS PROCESS                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              SESSION MANAGER                          │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │
│  │  │Game #1  │  │Game #2  │  │Game #3  │  │Game #N  │  │  │
│  │  │Agent #1 │  │Agent #2 │  │Agent #3 │  │Agent #N │  │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  │  │
│  └───────┼────────────┼────────────┼────────────┼───────┘  │
│          │            │            │            │           │
│  ┌───────▼────────────▼────────────▼────────────▼───────┐  │
│  │              SHARED SERVICES                         │  │
│  │  • Vector DB (strategy retrieval — shared)           │  │
│  │  • Evolution Manager (global optimization)            │  │
│  │  • LLM Client (connection pooling)                   │  │
│  │  • Memory Layer (cross-game learning)               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Game #1  │    │ Game #2  │    │ Game #3  │
    │ Process  │    │ Process  │    │ Process  │
    │ (sandbox)│    │ (sandbox)│    │ (sandbox)│
    └──────────┘    └──────────┘    └──────────┘
```

### 9.2 Resource Budgeting

```python
class ResourceBudget:
    """Prevent any single game from monopolizing resources."""
    
    MAX_CONCURRENT_GAMES = 5
    LLM_CALLS_PER_MINUTE = 60        # shared LLM budget
    MEMORY_LAYER_QUERIES_PER_SEC = 100
    
    def __init__(self):
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_GAMES)
        self.llm_rate_limiter = TokenBucket(rate=60, capacity=60)
    
    async def acquire(self, session_id: str) -> None:
        await self.semaphore.acquire()
        if not self.llm_rate_limiter.try_acquire():
            self.semaphore.release()
            raise RuntimeError(f"Session {session_id}: LLM rate limit exceeded")
    
    def release(self, session_id: str) -> None:
        self.semaphore.release()
```

### 9.3 Cross-Game Learning

When one game learns a strategy, it can be transferred:

```
Game A (Starcraft) discovers efficient micro-pattern
         │
         ▼
  ┌──────────────────┐
  │  Cross-Game      │
  │  Pattern Extract │
  │  (abstract the   │
  │   underlying     │
  │   principle)     │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │  Generalize to   │
  │  applicable      │
  │  game types      │
  │  (RTS, RPG, etc) │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │  Inject into     │
  │  Strategy Pool   │
  │  for Game B      │
  │  (shadow test    │
  │   first)         │
  └──────────────────┘
```

---

## 10. Minimal Viable Harness (MVH)

### 10.1 What Must Be Present

For a harness to be *viable* (not just minimal), it must have:

```
MINIMAL VIABLE HARNESS = [
    SESSION_MANAGER,
    GAME_INTERFACE (screenshot + input),
    AGENT_RUNTIME (LLM call),
    CODE_EXECUTOR (sandbox),
    FEEDBACK_COLLECTOR (basic metrics),
]
```

**What's NOT required for MVH:**
- Full evolution system
- Multi-game support
- Cross-session memory
- Strategy versioning
- REST API

### 10.2 MVH Architecture

```
┌─────────────────────────────────────────────────────┐
│              MINIMAL VIABLE HARNESS                  │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐                  │
│  │ SessionMgr   │  │GameInterface │                  │
│  │ (1 session)  │  │(screenshot+  │                  │
│  │              │  │ input)      │                  │
│  └──────┬───────┘  └──────┬───────┘                  │
│         │                 │                          │
│         └────────┬────────┘                          │
│                  │                                   │
│         ┌────────▼────────┐                         │
│         │  Context Assembler│                        │
│         │  (state + tools)  │                        │
│         └────────┬─────────┘                        │
│                  │                                   │
│         ┌────────▼─────────┐                        │
│         │   Agent Runtime  │                        │
│         │   (prompt + LLM) │                        │
│         └────────┬─────────┘                        │
│                  │                                   │
│         ┌────────▼─────────┐                        │
│         │  Code Executor   │                        │
│         │  (sandbox exec)  │                        │
│         └────────┬─────────┘                        │
│                  │                                   │
│         ┌────────▼─────────┐                        │
│         │ Feedback Collect │                        │
│         │ (simple log)     │                        │
│         └──────────────────┘                        │
└─────────────────────────────────────────────────────┘
```

### 10.3 MVH Implementation

```python
# minimal_harness.py — ~200 lines, no external deps beyond stdlib + openai

import json
import time
import asyncio
from dataclasses import dataclass, asdict
from typing import Callable

@dataclass
class MinimalContext:
    game_state: dict
    available_actions: list[dict]

@dataclass
class MinimalAction:
    action: str
    params: dict
    reason: str

class MinimalHarness:
    """MVH: ~200 lines. No vector DB, no evolution, no multi-game."""
    
    def __init__(self, game_interface: Callable, llm_client: Callable):
        self.game = game_interface      # fn() -> game_state dict
        self.llm = llm_client            # fn(prompt) -> str
        self.tick_count = 0
        self.history: list[dict] = []
    
    async def tick(self, objective: str) -> MinimalAction:
        # 1. Capture game state
        state = self.game()
        
        # 2. Build prompt
        prompt = self._build_prompt(state, objective)
        
        # 3. Call LLM
        response = self.llm(prompt)
        
        # 4. Parse
        action = self._parse_response(response)
        
        # 5. Execute (in sandbox)
        result = self._execute(action)
        
        # 6. Record feedback
        self.history.append({
            "tick": self.tick_count,
            "action": action,
            "result": result,
            "state_before": state
        })
        
        self.tick_count += 1
        return action
    
    def _build_prompt(self, state: dict, objective: str) -> str:
        return f"""Game state: {json.dumps(state)}
Objective: {objective}
Respond with JSON: {{"action": "...", "params": {{}}, "reason": "..."}}"""
    
    def _parse_response(self, response: str) -> MinimalAction:
        try:
            obj = json.loads(response)
            return MinimalAction(**obj)
        except json.JSONDecodeError:
            # Fallback: regex extraction
            import re
            m = re.search(r'\{.*\}', response, re.DOTALL)
            if m:
                return MinimalAction(**json.loads(m.group(0)))
            return MinimalAction("noop", {}, "parse_failed")
    
    def _execute(self, action: MinimalAction) -> dict:
        # Sandbox: just validate and log (real impl would call game interface)
        return {"success": True, "action_taken": action.action}
    
    async def run(self, objective: str, max_ticks: int = 1000):
        for _ in range(max_ticks):
            await self.tick(objective)
            await asyncio.sleep(0.1)  # tick rate limit
```

---

## 11. Reference Project Analysis

### 11.1 PantheonOS (Evolable Agents)

**What it is:** A framework for agents that can evolve their own tooling and prompts.

**Key insights for CrawlForge:**
- **Tool self-discovery:** Agents can propose new tools → use for game-specific action discovery
- **Evolved prompts:** System prompts modified by agent feedback → directly applicable to strategy evolution
- **Modular agent architecture:** Separation of agent brain (LLM) from agent body (tools)

**Relevant patterns:**
- Tool registry that grows over time
- Prompt version tracking (git-like history)
- Agent-generated test cases for strategy validation

### 11.2 OpenHarness (OpenClaw's Own)

**What it is:** OpenClaw's own ACP (Agent Communication Protocol) runtime.

**Key insights for CrawlForge:**
- **Session-based model:** Each game = a session with isolated state + shared memory
- **Channel abstraction:** Games are just another "channel" (like Discord/Telegram)
- **Runtime orchestration:** Sessions spawned/managed by a top-level orchestrator
- **Tool bundle pattern:** Tools packaged as versioned bundles, hot-swappable

**Relevant patterns:**
- ACP message protocol for harness↔agent communication
- Session state machine (init → running → paused → stopped)
- Shared skill registry accessible to all sessions

### 11.3 Autono (ReAct Agents)

**What it is:** ReAct (Reason + Act) pattern implementation for autonomous agents.

**Key insights for CrawlForge:**
- **Thought-Action-Observation loop:** Think → Act → Observe → Think...
- **Structured output enforcement:** Force JSON output for parseability
- **Error recovery loops:** Failed actions trigger retry with different approach
- **Minimal prompt, maximal structure:** Use structure to compensate for small context

**Relevant patterns:**
- ReAct loop as the core tick loop
- Error type classification → route to recovery strategy
- Action space formalization (typed action registry)

### 11.4 deepagentsdk (AI SDK Harness)

**What it is:** Production-grade Python SDK for building AI agents with tool use.

**Key insights for CrawlForge:**
- **Streaming responses:** Real-time action display while LLM is still generating
- **Tool call serialization:** Tools as JSON schemas, LLM decides which to call
- **State checkpointing:** Periodic state snapshots for crash recovery
- **Multi-turn memory:** Sliding window of conversation history

**Relevant patterns:**
- Tool definition as JSON Schema (openai function calling format)
- Streaming execution for real-time feedback
- Checkpointing for long-running session resilience

### 11.5 Consolidated Best Practices

```
FROM PantheonOS:     Tool self-discovery, prompt evolution, modular brain/body
FROM OpenHarness:   Session model, channel abstraction, ACP protocol
FROM Autono:        ReAct loop, structured output, error recovery routing  
FROM deepagentsdk:  Tool JSON schema, streaming, checkpointing
```

---

## 12. Implementation Roadmap

### Phase 1: Core Harness (MVP)
- [ ] Session manager (start/stop/pause single game)
- [ ] Game interface (screenshot capture, keyboard/mouse input)
- [ ] Agent runtime (prompt assembly + LLM call)
- [ ] Code executor (sandbox + basic verification)
- [ ] Feedback collector (action log, success rate)

**Deliverable:** Can play a simple game (e.g., Asteroids, Snake) autonomously

### Phase 2: Structured Execution
- [ ] Strategy versioning (save/load strategy snapshots)
- [ ] Tool registry (game-specific action definitions)
- [ ] Context assembler (game state + memory + tools)
- [ ] Basic error recovery (retry on failure)
- [ ] REST control plane API

**Deliverable:** Can hot-swap strategies mid-game; 5+ simultaneous sessions

### Phase 3: Self-Evolution
- [ ] Fitness scoring system
- [ ] Mutation operators (prompt, tool, constraints)
- [ ] Genetic population management
- [ ] Validation framework (shadow run before deploy)
- [ ] Evolution trigger system

**Deliverable:** Strategy evolves autonomously after 100+ ticks of failure

### Phase 4: Production Hardening
- [ ] Cross-game learning transfer
- [ ] Multi-machine distributed execution
- [ ] Natural language strategy editor
- [ ] Full telemetry dashboard
- [ ] Anti-cheat aware input simulation

---

## Appendix A: Glossary

| Term | Definition |
|---|---|
| **Harness** | Framework that drives, executes, and adapts AI agents |
| **Tick** | Single decision cycle: observe → reason → act → feedback |
| **Strategy** | Versioned combination of system prompt + tools + constraints |
| **Fitness** | Numeric score of how well a strategy performs |
| **Last Mile** | Gap between LLM text output and verified game action |
| **Evolution** | Genetic modification of strategies based on fitness |
| **ReAct** | Reasoning + Action loop pattern |
| **RAG** | Retrieval-Augmented Generation |
| **Sandbox** | Isolated execution environment (subprocess, container) |

## Appendix B: File Structure

```
CrawlForge/
├── harness/
│   ├── __init__.py
│   ├── core/
│   │   ├── harness.py           # Main Harness class
│   │   ├── session_manager.py   # Session lifecycle
│   │   ├── state_machine.py     # FSM implementations
│   │   └── config.py            # Configuration
│   ├── agent/
│   │   ├── runtime.py            # Agent runtime (LLM calls)
│   │   ├── code_generator.py     # Code gen pipeline
│   │   ├── code_executor.py      # Sandbox execution
│   │   └── output_parser.py      # Response parsing
│   ├── evolution/
│   │   ├── manager.py            # Evolution FSM
│   │   ├── mutation.py           # Mutation operators
│   │   ├── fitness.py            # Fitness scoring
│   │   └── genetic.py            # Selection/crossover
│   ├── retrieval/
│   │   ├── retriever.py          # RAG retrieval
│   │   ├── embedder.py           # Embedding model
│   │   └── vector_store.py       # Qdrant interface
│   ├── context/
│   │   ├── assembler.py           # Context bundle assembly
│   │   ├── memory.py             # Memory layer
│   │   └── game_state.py         # State extraction
│   ├── game_interface/
│   │   ├── base.py               # GameInterface ABC
│   │   └── adapters/             # Per-game adapters
│   └── api/
│       ├── rest.py               # REST control plane
│       ├── websocket.py          # Live feed
│       └── protocol.py           # ACP protocol
├── docs/
│   ├── HARNESS-DESIGN.md         # This document
│   ├── ARCHITECTURE.md           # System architecture
│   └── GAME-ADAPTERS.md          # Per-game integration guide
└── tests/
    ├── harness/
    │   ├── test_session.py
    │   ├── test_evolution.py
    │   └── test_code_executor.py
    └── fixtures/
        └── mock_game_state.json
```

---

*Document version 1.0 — Framework Design Specification*  
*Next: ARCHITECTURE.md (component-level implementation details)*
