# ITERATION-PLAN.md — 4-Hour Autonomous Iteration Plan

> **Duration:** 4 hours (240 minutes)  
> **Sprint Length:** 3 sprints × 80 minutes each  
> **Goal:** Complete MODULE-01 through MODULE-03 implementation  
> **Start:** T+0:00 | **End:** T+4:00

---

## Sprint Overview

| Sprint | Time | Modules | Goal |
|--------|------|---------|------|
| Sprint 1 | T+0:00 → T+1:20 | MODULE-01 | Foundation complete |
| Sprint 2 | T+1:20 → T+2:40 | MODULE-02 + MODULE-07 | Runtime + Template Matching |
| Sprint 3 | T+2:40 → T+4:00 | MODULE-03 + MODULE-04 | AI Pipeline + ReAct Loop |

---

## Pre-Sprint Setup (T+0:00 → T+0:10)

```bash
# 1. Create project directory structure
mkdir -p src/crawlforge/{foundation,runtime,ai_pipeline,react_loop,checkpoint,evolution,template_matching,slot_game,data_collector,scheduler}
mkdir -p tests/{unit,integration}
mkdir -p configs
mkdir -p docs/modules

# 2. Initialize Python package
touch src/crawlforge/__init__.py
touch src/crawlforge/foundation/__init__.py
# ... etc for all modules

# 3. Create requirements.txt
cat > requirements.txt << 'EOF'
uiautomator2>=2.12.0
playwright>=1.40.0
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0
websockets>=12.0
orjson>=3.9.0
filelock>=3.12.0
pydantic>=2.0.0
requests>=2.31.0
pandas>=2.0.0
scipy>=1.11.0
matplotlib>=3.7.0
pyarrow>=14.0.0
dill>=0.3.7
pure-python-adb>=0.3.0
EOF

# 4. Create configs/games.yaml (seed with one game)
# 5. Verify Python 3.10+ available
# 6. Run: pip install -r requirements.txt --dry-run  # check deps
```

---

## Sprint 1: Foundation (T+0:10 → T+1:20)

**Goal:** MODULE-01 complete and testable

### Task 1.1: Enums + Dataclasses (T+0:10 → T+0:40)

**Time:** 30 minutes

```bash
# File: src/crawlforge/foundation/models.py
# Write all dataclasses:
#   - GameDefinition, GameTemplates, ReelConfig
#   - GameSession, SpinResult, CompetitorActivity
#   - Checkpoint, CheckpointMetadata, RecoveryInfo
#   - GameState, SpinState, SessionStatus, RuntimeType, GameType
```

**Acceptance:**
- [ ] All dataclasses import without errors
- [ ] All enums have `.value` serialization
- [ ] `python -c "from crawlforge.foundation.models import *; print('OK')"` succeeds

### Task 1.2: Exceptions (T+0:40 → T+0:55)

**Time:** 15 minutes

```bash
# File: src/crawlforge/foundation/exceptions.py
# Write all custom exceptions:
#   CrawlForgeError (base)
#   GameNotFoundError, RuntimeConnectionError, TemplateMatchError
#   CheckpointError, InsufficientBalanceError
#   EvolutionError, DataCollectionError, SchedulerError
```

**Acceptance:**
- [ ] All exceptions have `context` dict parameter
- [ ] `isinstance(e, CrawlForgeError)` catches all custom exceptions

### Task 1.3: Interfaces (T+0:55 → T+1:10)

**Time:** 15 minutes

```bash
# File: src/crawlforge/foundation/interfaces.py
# Write Protocol classes:
#   Runtime, TemplateMatcher, CheckpointManager, EvolutionEngine
# Use @runtime_checkable decorator
```

**Acceptance:**
- [ ] All protocols are `@runtime_checkable`
- [ ] `isinstance(obj, Runtime)` works for any object implementing Runtime methods

### Task 1.4: Event Bus (T+1:10 → T+1:20)

**Time:** 10 minutes

```bash
# File: src/crawlforge/foundation/events.py
# Write EventBus class with emit/subscribe/unsubscribe
# Write CrawlForgeEvent dataclass
```

**Acceptance:**
- [ ] `emit()` broadcasts to all subscribers
- [ ] `subscribe()`/`unsubscribe()` work correctly
- [ ] trace_id propagated through event chain

### Sprint 1 Review (T+1:20 → T+1:25)

```
✅ DONE: MODULE-01 foundation
❌ Blockers:
✅ Remaining: MODULE-02 through MODULE-10
```

---

## Sprint 2: Runtime + Template Matching (T+1:25 → T+2:40)

**Goal:** MODULE-02 (ADB + Playwright + OpenCV) and MODULE-07 (Template Matching) complete

### Task 2.1: Config for Runtime + Template Matching (T+1:25 → T+1:40)

**Time:** 15 minutes

```bash
# Files:
#   src/crawlforge/runtime/config.py
#   src/crawlforge/template_matching/config.py

# Write:
#   - RuntimeConfig, ADBConfig, PlaywrightConfig, VisualConfig
#   - TemplateMatcherConfig, MatchingMethod, ThresholdConfig
```

### Task 2.2: ADBRuntime (T+1:40 → T+2:00)

**Time:** 20 minutes

```bash
# File: src/crawlforge/runtime/adb_runtime.py

# Core methods:
#   connect(), disconnect(), is_connected()
#   take_screenshot() → bytes
#   tap(x, y), swipe(x1, y1, x2, y2, duration_ms)
#   is_app_open(package), start_app(package), stop_app(package)
#   get_orientation(), get_screen_size()
#   execute_shell(command)
```

**Acceptance:**
- [ ] `python -c "from crawlforge.runtime.adb_runtime import ADBRuntime"` succeeds
- [ ] Mock test: `connect()`/`disconnect()`/`take_screenshot()` work with mocked uiautomator2

### Task 2.3: PlaywrightRuntime (T+2:00 → T+2:15)

**Time:** 15 minutes

```bash
# File: src/crawlforge/runtime/playwright_runtime.py

# Core methods:
#   connect(), disconnect(), is_connected()
#   take_screenshot() → bytes
#   tap(selector), swipe(x1, y1, x2, y2), type_text(selector, text)
#   navigate(url), execute_js(script)
```

**Acceptance:**
- [ ] `python -c "from crawlforge.runtime.playwright_runtime import PlaywrightRuntime"` succeeds
- [ ] Mock test: `navigate()`/`take_screenshot()`/`execute_js()` work

### Task 2.4: OpenCV Visual Runtime (T+2:15 → T+2:25)

**Time:** 10 minutes

```bash
# File: src/crawlforge/runtime/opencv_runtime.py

# Core methods:
#   tap_on_template(template_path, threshold) → (x, y)
#   wait_for_template(template_path, threshold, timeout_ms)
#   Uses MODULE-07 TemplateMatcher
```

### Task 2.5: TemplateMatcher (T+2:25 → T+2:35)

**Time:** 10 minutes

```bash
# File: src/crawlforge/template_matching/matcher.py

# Core methods:
#   match(screenshot, template_path, threshold) → list[MatchResult]
#   match_best(screenshot, template_path, threshold) → MatchResult | None
#   match_with_fallback(screenshot, [template_paths], threshold)
#   calibrate(reference_screenshot, template_path) → float
```

**Acceptance:**
- [ ] `cv2.imread()` and `cv2.matchTemplate()` work
- [ ] Match results sorted by confidence
- [ ] Threshold filtering works correctly

### Task 2.6: RuntimeManager (T+2:35 → T+2:40)

**Time:** 5 minutes

```bash
# File: src/crawlforge/runtime/runtime_manager.py

# Core:
#   get_runtime(RuntimeType) → Runtime
#   select_runtime_for_game(GameDefinition) → Runtime
#   connect_all(), disconnect_all()
```

### Sprint 2 Review (T+2:40 → T+2:45)

```
✅ DONE: MODULE-02 (Runtime Abstraction)
✅ DONE: MODULE-07 (Template Matching)
❌ Blockers:
✅ Remaining: MODULE-03 (AI Pipeline), MODULE-04 (ReAct Loop), MODULE-05-10
```

---

## Sprint 3: AI Pipeline + ReAct Loop (T+2:45 → T+4:00)

**Goal:** MODULE-03 (AI Pipeline) and MODULE-04 (ReAct Loop) skeleton complete

### Task 3.1: AI Pipeline Dataclasses + Config (T+2:45 → T+3:00)

**Time:** 15 minutes

```bash
# File: src/crawlforge/ai_pipeline/models.py
# File: src/crawlforge/ai_pipeline/config.py

# Write:
#   - PipelineConfig, PipelineContext
#   - AnalysisResult, UIElement, BoundingBox, GameState
#   - ActionPlan, ActionStep, ActionType
#   - SandboxResult, ValidatedStep, SandboxError
#   - TestResult, ExecutedStep
```

### Task 3.2: AIPipeline Core (T+3:00 → T+3:25)

**Time:** 25 minutes

```bash
# File: src/crawlforge/ai_pipeline/pipeline.py

# Core:
#   analyze(screenshot, prompt) → AnalysisResult
#     → call vision model (qwen2.5-vl via airouter or mock)
#   generate(analysis, goal) → ActionPlan
#     → call LLM (qwen3.5-27b via airouter or mock)
#   sandbox(plan) → SandboxResult
#     → validate coordinates in bounds, check sequences
#   test(plan) → TestResult
#     → execute via runtime, return per-step results
#   run(context) → ActionPlan
#     → full pipeline: analyze → generate → sandbox → test
```

**Acceptance:**
- [ ] `AIPipeline.analyze()` returns valid AnalysisResult
- [ ] `AIPipeline.generate()` returns valid ActionPlan with steps
- [ ] `AIPipeline.sandbox()` catches out-of-bounds errors
- [ ] `AIPipeline.test()` executes and returns per-step results
- [ ] `AIPipeline.run()` chains all 4 stages

### Task 3.3: ReAct Loop Core (T+3:25 → T+3:45)

**Time:** 20 minutes

```bash
# File: src/crawlforge/react_loop/loop.py

# Core:
#   ReActLoop(game, runtime, pipeline, config)
#   run(goal, max_iterations) → LoopResult
#   step() → ReActStep  (OBSERVE → THINK → ACT → REFLECT)
#   observe() → ObservationResult
#   think(observation, goal) → ActionPlan
#   act(plan) → ExecutionResult
#   reflect(execution) → ReflectionResult
#   stop()
```

**Acceptance:**
- [ ] `ReActLoop.step()` completes one full cycle
- [ ] `ReActLoop.run()` respects max_iterations
- [ ] `ReActLoop.history` returns all ReActStep records
- [ ] Loop stops when `reflection.loop_should_stop = True`

### Task 3.4: @ability Decorator + Registry (T+3:45 → T+3:55)

**Time:** 10 minutes

```bash
# File: src/crawlforge/react_loop/abilities.py

# Core:
#   @ability(name, description, parameters, returns, tags)
#   AbilityRegistry.register(ability)
#   AbilityRegistry.call(name, params)
#   Built-in abilities: spin, collect_bonus, set_bet, get_game_state
```

### Task 3.5: MCP Protocol Handler (T+3:55 → T+4:00)

**Time:** 5 minutes

```bash
# File: src/crawlforge/react_loop/mcp_protocol.py

# Core:
#   MCPProtocolHandler(registry, event_bus)
#   tools_list() → list[dict]
#   tools_call(name, arguments) → Any
#   JSON-RPC request/response format
```

### Final Review (T+4:00)

```
✅ DONE: MODULE-01 (Foundation)
✅ DONE: MODULE-02 (Runtime Abstraction)
✅ DONE: MODULE-03 (AI Pipeline)
✅ DONE: MODULE-04 (ReAct Loop)
✅ DONE: MODULE-07 (Template Matching)
❌ Remaining: MODULE-05-06, MODULE-08-10
```

---

## Time Boxing Rules

| Situation | Action |
|---|---|
| Task not done at timebox end | **Cut scope**, move to next sprint |
| Task done early | **Add next task** from backlog |
| Blocker encountered | Log blocker, skip to next independent task |
| All tasks in sprint done | **Early review + advance to next sprint** |

---

## Post-4-Hour Backlog

These modules were not reached in the 4-hour sprint but should be prioritized next:

| Priority | Module | Estimated Time |
|---|---|---|
| 1 | MODULE-05 (Checkpoint) | 3-4 hrs |
| 2 | MODULE-08 (Slot Game Adapter) | 3-4 hrs |
| 3 | MODULE-09 (Data Collector) | 3-4 hrs |
| 4 | MODULE-06 (Evolution) | 3-4 hrs |
| 5 | MODULE-10 (Scheduler) | 3-4 hrs |

**Total remaining:** ~15-20 hours

---

## Success Metrics (at T+4:00)

| Metric | Target |
|---|---|
| Modules implemented | ≥ 5 (MODULE-01, 02, 03, 04, 07) |
| Unit tests written | ≥ 30 |
| Code that imports without error | 100% |
| Architecture diagram accurate | All module dependencies documented |
| Files in correct location | `src/crawlforge/<module>/` |
