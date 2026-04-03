"""
ReAct Loop - Reasoning + Acting execution loop for game automation.

Observes game state, generates action plans, executes them, and reflects on results.
"""

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

from ..core import Action, GameState
from ..core.interfaces import Runtime
from ..ai_pipeline import AIPipeline, AIPipelineConfig, AnalysisResult, ActionPlan, TestResult
from ..evolution.fixer import AdapterFixer, FixResult
from .models import (
    ReActStep, ReActConfig, ReActState,
    ObservationResult, ExecutionResult, ReflectionResult,
    LoopResult, Ability, AbilityRegistry,
)


class ReActLoop:
    """
    ReAct loop: Observe → Think → Act → Reflect.

    Repeatedly:
    1. OBSERVE - capture screenshot and analyze
    2. THINK - generate action plan via AI pipeline
    3. ACT - execute plan via runtime
    4. REFLECT - evaluate result and decide next action
    """

    def __init__(
        self,
        runtime: Optional[Runtime] = None,
        pipeline: Optional[AIPipeline] = None,
        config: Optional[ReActConfig] = None,
        checkpoint_manager: Optional[Any] = None,
        game_adapter: Optional[Any] = None,
    ):
        self.runtime = runtime
        self.pipeline = pipeline or AIPipeline(AIPipelineConfig())
        self.config = config or ReActConfig()
        self.checkpoint_manager = checkpoint_manager
        self.game_adapter = game_adapter
        self._history: list[ReActStep] = []
        self._is_running = False
        self._current_state: Optional[ReActState] = None
        self._fixer = AdapterFixer() if game_adapter else None

    async def run(self, goal: str, max_iterations: int = 50) -> LoopResult:
        """
        Run the ReAct loop until goal is met or max_iterations reached.

        Args:
            goal: The goal to achieve (e.g., "spin 100 times")
            max_iterations: Maximum number of loop iterations

        Returns:
            LoopResult with execution history and final state
        """
        self._is_running = True
        start_time = time.monotonic()
        iteration = 0

        while self._is_running and iteration < max_iterations:
            iteration += 1

            # Execute one cycle
            step_result = await self.step(goal)

            self._history.append(step_result)

            # Check if we should stop
            if step_result.reflection.loop_should_stop:
                break

            # Check goal progress
            if step_result.reflection.goal_progress >= 1.0:
                break

            # Respect iteration limit
            if iteration >= max_iterations:
                break

            # Small delay between iterations
            if self.config.step_delay_ms > 0:
                await asyncio.sleep(self.config.step_delay_ms / 1000)

        elapsed_ms = (time.monotonic() - start_time) * 1000

        return LoopResult(
            goal=goal,
            total_iterations=iteration,
            history=self._history,
            final_state=self._current_state,
            total_duration_ms=elapsed_ms,
            success=any(s.reflection.goal_progress >= 1.0 for s in self._history),
        )

    async def step(self, goal: str) -> ReActStep:
        """
        Execute a single OBSERVE→THINK→ACT→REFLECT cycle.
        """
        step_num = len(self._history) + 1
        step_start = time.monotonic()

        # OBSERVE
        observation = await self.observe()

        # THINK
        plan = await self.think(observation, goal)

        # ACT
        execution = await self.act(plan)

        # REFLECT
        reflection = await self.reflect(execution, goal)

        self._current_state = ReActState(
            goal=goal,
            current_plan=plan,
            last_execution=execution,
            last_reflection=reflection,
            iteration=step_num,
        )

        duration_ms = (time.monotonic() - step_start) * 1000

        return ReActStep(
            step_number=step_num,
            timestamp=datetime.now(),
            observation=observation,
            plan=plan,
            execution=execution,
            reflection=reflection,
            duration_ms=duration_ms,
        )

    async def observe(self) -> ObservationResult:
        """OBSERVE: Capture screenshot and analyze game state."""
        if self.runtime:
            screenshot = await self.runtime.screenshot()
        else:
            screenshot = b"fake_screenshot"
        screenshot_hash = hashlib.sha256(screenshot).hexdigest()

        # Run AI analysis
        analysis = await self.pipeline.analyze(screenshot)

        return ObservationResult(
            screenshot=screenshot,
            screenshot_hash=screenshot_hash,
            analysis=analysis,
        )

    async def think(self, observation: ObservationResult, goal: str) -> ActionPlan:
        """THINK: Generate action plan from observation."""
        # Generate plan from analysis
        plan = await self.pipeline.generate(observation.analysis, goal)
        # Run sandbox validation
        if self.pipeline.config.sandbox_enabled:
            sandbox = self.pipeline.sandbox(plan)
            if not sandbox.is_valid:
                # Filter to valid steps
                plan.steps = [s.step for s in sandbox.validated_steps if s.status in ("valid", "warning")]
        return plan

    async def act(self, plan: ActionPlan) -> ExecutionResult:
        """ACT: Execute action plan via runtime with self-healing."""
        try:
            test_result = await self.pipeline.test(plan)
        except Exception as e:
            # Evolution self-healing: try to fix with AdapterFixer
            if self._fixer and self.game_adapter:
                fix_result = self._fix_with_evolution(e, plan)
                if fix_result.success:
                    # Retry with fixed plan
                    test_result = await self.pipeline.test(fix_result.fixed_plan)
                else:
                    raise
            else:
                raise

        # Get balance after
        if self.runtime:
            new_screenshot = await self.runtime.screenshot()
        else:
            new_screenshot = b"fake_screenshot"
        
        analysis = await self.pipeline.analyze(new_screenshot)
        balance_after = analysis.balance

        # Check if state changed
        old_analysis = getattr(self, '_last_analysis', None)
        state_changed = (
            old_analysis is None or
            old_analysis.balance != balance_after
        )
        self._last_analysis = analysis

        return ExecutionResult(
            plan_id=plan.plan_id,
            executed_steps=test_result.executed_steps,
            final_screenshot=new_screenshot,
            balance_after=balance_after,
            state_changed=state_changed,
            runtime_errors=[s.error for s in test_result.executed_steps if s.error],
        )

    def _fix_with_evolution(self, error: Exception, plan: ActionPlan) -> FixResult:
        """Use AdapterFixer to attempt auto-repair."""
        if not self._fixer:
            return FixResult(success=False, error_id="", fix_applied="")
        
        # Record the error
        from ..evolution.fixer import ErrorType
        error_id = self._fixer.record_error(
            error_type=ErrorType.ACTION_FAILURE,
            error_message=str(error),
            adapter_name=getattr(self.game_adapter, 'game_name', 'unknown'),
            context={"plan_id": plan.plan_id},
            exception=error,
        )
        
        # Analyze and apply fix
        suggestions = self._fixer.analyze(error_id)
        if suggestions:
            result = self._fixer.apply_fix(error_id, suggestions[0], self.game_adapter)
            if result.success:
                return FixResult(
                    success=True,
                    error_id=error_id,
                    fix_applied=result.fix_applied,
                    fixed_plan=plan,  # Use same plan after config changes
                )
        
        return FixResult(success=False, error_id=error_id, fix_applied="")

    async def reflect(self, execution: ExecutionResult, goal: str) -> ReflectionResult:
        """REFLECT: Evaluate execution result."""
        reasons = []
        should_continue = True
        loop_stop = False
        goal_progress = 0.0

        # Check for errors
        if execution.runtime_errors:
            reasons.append(f"Runtime errors: {execution.runtime_errors}")

        # Check if spin succeeded
        if execution.state_changed:
            reasons.append("Game state changed - action succeeded")
            goal_progress = 0.1  # Partial progress

        # Check for terminal states
        if execution.balance_after is not None and execution.balance_after <= 0:
            reasons.append("Balance is zero - stopping")
            loop_stop = True
            should_continue = False

        # Parse goal for progress tracking
        if "spin" in goal.lower():
            spin_count = len([s for s in execution.executed_steps if s.status == "success"])
            # Estimate progress based on spin count vs target
            if "100" in goal:
                goal_progress = min(1.0, spin_count / 100)
            elif "50" in goal:
                goal_progress = min(1.0, spin_count / 50)
            elif "spin" in goal.split()[-1] or goal.split()[-1].isdigit():
                goal_progress = min(1.0, spin_count / 10)

        # Determine next action suggestion
        suggested = None
        if execution.balance_after is not None and execution.balance_after < 100:
            suggested = "balance_low"
        elif execution.state_changed:
            suggested = "spin_again"

        return ReflectionResult(
            should_continue=should_continue,
            goal_progress=goal_progress,
            reasons=reasons,
            suggested_next_action=suggested,
            loop_should_stop=loop_stop,
        )

    def stop(self) -> None:
        """Gracefully stop the loop."""
        self._is_running = False

    @property
    def history(self) -> list[ReActStep]:
        """Return full execution history."""
        return self._history.copy()

    def save_checkpoint(self) -> dict:
        """Save current state for recovery."""
        return {
            "history": [
                {
                    "step_number": s.step_number,
                    "timestamp": s.timestamp.isoformat(),
                    "reflection_goal_progress": s.reflection.goal_progress,
                }
                for s in self._history
            ],
            "is_running": self._is_running,
        }
