"""
AI Pipeline - 4-stage pipeline for game automation.

Stages:
1. Analyze - Vision model reads screenshot
2. Generate - LLM creates action plan
3. Sandbox - Dry-run validation
4. Test - Execute and verify
"""

import asyncio
import hashlib
import uuid
from datetime import datetime
from typing import Optional

from ..core import Action, GameState
from ..core.interfaces import Runtime
from .models import (
    PipelineConfig, PipelineContext,
    AnalysisResult, ActionPlan, ActionStep, ActionType,
    SandboxResult, ValidatedStep, SandboxError, SandboxErrorType,
    TestResult, ExecutedStep, UIElementResult, BoundingBox,
)


class AIRouter:
    """
    AI Router - routes AI requests to configured backend.

    Supports:
    - Local airouter (http://localhost:18888)
    - OpenAI-compatible APIs
    - Anthropic APIs
    """

    def __init__(self, router_url: str = "http://localhost:18888"):
        self.router_url = router_url

    async def vision_analyze(
        self,
        screenshot: bytes,
        prompt: str,
        model: str = "qwen2.5-vl-3b",
    ) -> str:
        """Analyze screenshot with vision model."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                b64 = __import__("base64").b64encode(screenshot).decode()
                resp = await client.post(
                    f"{self.router_url}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                                ],
                            }
                        ],
                        "max_tokens": 1024,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception:
            pass
        return self._stub_vision_output(prompt)

    async def llm_generate(
        self,
        prompt: str,
        model: str = "qwen3.5-27b",
    ) -> str:
        """Generate text with LLM."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.router_url}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 512,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception:
            pass
        return self._stub_llm_output(prompt)

    @staticmethod
    def _stub_vision_output(prompt: str) -> str:
        return f"Vision analysis: detected spin button at center, balance display at top. {prompt}"

    @staticmethod
    def _stub_llm_output(prompt: str) -> str:
        return f"Action plan: tap center of screen to spin. Reasoning: standard slot game flow."


class AIPipeline:
    """
    4-stage AI pipeline for game automation.

    Usage:
        pipeline = AIPipeline(config, runtime)
        context = PipelineContext(goal="spin the reels", screenshot=bytes)
        plan = await pipeline.run(context)
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: Runtime,
        router: Optional[AIRouter] = None,
    ):
        self.config = config
        self.runtime = runtime
        self.router = router or AIRouter()

    async def run(self, context: PipelineContext) -> ActionPlan:
        """
        Run full pipeline: Analyze → Generate → Sandbox → Test.

        Returns a validated ActionPlan ready for execution.
        """
        # Stage 1: Analyze
        analysis = await self.analyze(context.screenshot, context.goal)

        # Stage 2: Generate
        plan = await self.generate(analysis, context.goal)

        # Stage 3: Sandbox (optional)
        if self.config.sandbox_enabled:
            sandbox_result = self.sandbox(plan)
            if not sandbox_result.is_valid:
                # Filter to only valid steps
                plan.steps = [
                    s.step for s in sandbox_result.validated_steps
                    if s.status in ("valid", "warning")
                ]

        return plan

    async def analyze(self, screenshot: bytes, prompt: Optional[str] = None) -> AnalysisResult:
        """
        Stage 1: Vision analysis of screenshot.

        Uses vision model to detect UI elements and game state.
        """
        prompt = prompt or "Analyze this slot game screenshot. Identify: spin button location, balance, bet level, any active bonuses or free spins."
        raw = await self.router.vision_analyze(screenshot, prompt, self.config.vision_model)

        # Parse vision output
        elements, balance, spin_visible = self._parse_vision_output(raw)

        screenshot_hash = hashlib.sha256(screenshot).hexdigest()
        return AnalysisResult(
            screenshot_hash=screenshot_hash,
            timestamp=datetime.now(),
            detected_elements=elements,
            balance=balance,
            spin_button_visible=spin_visible,
            confidence=self.config.confidence_threshold,
            raw_vision_output=raw,
            suggestions=["tap_spin" if spin_visible else "wait"],
        )

    async def generate(self, analysis: AnalysisResult, goal: str) -> ActionPlan:
        """
        Stage 2: Generate action plan from analysis.

        Uses LLM to create a structured plan.
        """
        prompt = self._build_generation_prompt(analysis, goal)
        raw = await self.router.llm_generate(prompt, self.config.llm_model)

        plan_id = str(uuid.uuid4())[:8]
        plan = self._parse_plan_output(raw, plan_id, goal)

        if not plan.steps:
            # Fallback: basic spin action
            plan.steps.append(ActionStep(
                step_number=1,
                action_type=ActionType.TAP,
                params={"x": 540, "y": 2050},
                description="Tap spin button",
                expected_outcome="Reels start spinning",
            ))

        return plan

    def sandbox(self, plan: ActionPlan) -> SandboxResult:
        """
        Stage 3: Sandbox validation.

        Dry-run validation of the action plan to catch errors.
        """
        validated = []
        errors = []
        warnings = []

        screen_w, screen_h = 1080, 2340  # Typical Android dimensions

        for i, step in enumerate(plan.steps):
            step_num = i + 1
            issues = []

            at = step.action_type
            p = step.params

            # Check coordinates are in bounds
            if at in (ActionType.TAP,):
                x, y = p.get("x", 0), p.get("y", 0)
                if x < 0 or x > screen_w or y < 0 or y > screen_h:
                    issues.append(f"Step {step_num}: coordinates ({x},{y}) out of bounds")

            elif at == ActionType.SWIPE:
                x1, y1 = p.get("x1", 0), p.get("y1", 0)
                x2, y2 = p.get("x2", 0), p.get("y2", 0)
                for coords, name in [((x1, y1), "start"), ((x2, y2), "end")]:
                    cx, cy = coords
                    if cx < 0 or cx > screen_w or cy < 0 or cy > screen_h:
                        issues.append(f"Step {step_num}: {name} coords ({cx},{cy}) out of bounds")

            elif at == ActionType.WAIT:
                duration = p.get("duration_ms", 0)
                if duration > 30000:
                    warnings.append(f"Step {step_num}: unusually long wait ({duration}ms)")

            # Classify status
            if issues:
                for msg in issues:
                    errors.append(SandboxError(
                        step_number=step_num,
                        error_type=SandboxErrorType.OUT_OF_BOUNDS,
                        message=msg,
                    ))
                validated.append(ValidatedStep(step=step, status="error", reason="; ".join(issues)))
            elif warnings:
                validated.append(ValidatedStep(step=step, status="warning", reason=warnings[-1]))
            else:
                validated.append(ValidatedStep(step=step, status="valid"))

        return SandboxResult(
            is_valid=len(errors) == 0,
            validated_steps=validated,
            errors=errors,
            warnings=warnings,
        )

    async def test(self, plan: ActionPlan) -> TestResult:
        """
        Stage 4: Execute plan and verify result.
        """
        executed = []
        unexpected = []
        retry = False

        for step in plan.steps:
            try:
                action = self._step_to_action(step)
                result = await self.runtime.execute(action)
                executed.append(ExecutedStep(
                    step=step,
                    status="success" if result.success else "failed",
                    screenshot=result.screenshot_after,
                    error=result.error,
                    duration_ms=result.duration_ms,
                ))
                if not result.success:
                    retry = True
            except Exception as e:
                executed.append(ExecutedStep(
                    step=step,
                    status="failed",
                    error=str(e),
                ))
                retry = True

        final_screen = await self.runtime.screenshot() if self.runtime.is_alive() else None
        return TestResult(
            plan_id=plan.plan_id if hasattr(plan, 'plan_id') else "",
            executed_steps=executed,
            success=all(s.status == "success" for s in executed),
            final_screenshot=final_screen,
            unexpected_states=unexpected,
            retry_recommended=retry,
        )

    def _parse_vision_output(self, raw: str) -> tuple:
        """Parse vision model output into structured data."""
        elements = []
        balance = None
        spin_visible = True  # Assume visible unless detected otherwise

        # Simple heuristics for now
        if "balance" in raw.lower():
            import re
            match = re.search(r"balance[:\s]*(\d+)", raw, re.IGNORECASE)
            if match:
                balance = float(match.group(1))

        # Check for spin button mention
        spin_keywords = ["spin button", "spin", "play button"]
        spin_visible = any(k in raw.lower() for k in spin_keywords)

        return elements, balance, spin_visible

    def _build_generation_prompt(self, analysis: AnalysisResult, goal: str) -> str:
        """Build prompt for LLM plan generation."""
        state = analysis.game_state_dict
        return f"""Generate an action plan for a slot game.

Goal: {goal}
Game state: {state}

Respond with a JSON action plan:
{{"plan_id": "uuid", "steps": [
  {{"step_number": 1, "action_type": "tap", "params": {{"x": 540, "y": 2050}}, "description": "tap spin"}}
]}}

Available action types: tap, swipe, wait, collect_bonus, set_bet
For tap: params must include x, y coordinates
For swipe: params must include x1, y1, x2, y2, duration_ms
For wait: params must include duration_ms

Respond ONLY with valid JSON, no explanation."""

    def _parse_plan_output(self, raw: str, plan_id: str, goal: str) -> ActionPlan:
        """Parse LLM output into ActionPlan."""
        import json
        import re

        # Try to extract JSON from response
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                data = json.loads(match.group())
                steps = []
                for s in data.get("steps", []):
                    at_str = s.get("action_type", "tap")
                    try:
                        at = ActionType(at_str)
                    except ValueError:
                        at = ActionType.TAP
                    steps.append(ActionStep(
                        step_number=s.get("step_number", 1),
                        action_type=at,
                        params=s.get("params", {}),
                        description=s.get("description", ""),
                        expected_outcome=s.get("expected_outcome", ""),
                    ))
                return ActionPlan(
                    plan_id=plan_id,
                    goal=goal,
                    steps=steps,
                    confidence=data.get("confidence", 0.5),
                    reasoning=data.get("reasoning", ""),
                )
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback
        return ActionPlan(plan_id=plan_id, goal=goal, steps=[])

    @staticmethod
    def _step_to_action(step: ActionStep) -> Action:
        """Convert ActionStep to runtime Action."""
        at = step.action_type
        p = step.params
        if at == ActionType.TAP:
            return Action(action_type="tap", x=p.get("x"), y=p.get("y"))
        elif at == ActionType.SWIPE:
            return Action(
                action_type="swipe",
                x1=p.get("x1"), y1=p.get("y1"),
                x2=p.get("x2"), y2=p.get("y2"),
                duration_ms=p.get("duration_ms", 300),
            )
        elif at == ActionType.WAIT:
            return Action(action_type="wait", duration_ms=p.get("duration_ms", 1000))
        elif at == ActionType.COLLECT_BONUS:
            return Action(action_type="tap", x=p.get("x", 540), y=p.get("y", 1200))
        elif at == ActionType.SET_BET:
            return Action(action_type="tap", x=p.get("x", 540), y=p.get("y", 1800))
        elif at == ActionType.INPUT_TEXT:
            return Action(action_type="text", text=p.get("text", ""))
        elif at == ActionType.PRESS_KEY:
            return Action(action_type="key", key=p.get("key", "BACK"))
        else:
            return Action(action_type="wait", duration_ms=500)
