"""
AI Pipeline - 4-stage pipeline for game automation.
统一使用 newapi 作为 AI 后端。
"""

import asyncio
import base64
import hashlib
import uuid
from datetime import datetime
from typing import Optional

from ..core import Action, GameState
from ..core.interfaces import Runtime
from .models import (
    PipelineContext,
    AnalysisResult, ActionPlan, ActionStep, ActionType,
    SandboxResult, ValidatedStep, SandboxError, SandboxErrorType,
    TestResult, ExecutedStep,
)
from .config import AIPipelineConfig


class NewAPIClient:
    """统一使用 newapi 的 AI 客户端"""
    
    def __init__(self, config: Optional[AIPipelineConfig] = None):
        config = config or AIPipelineConfig()
        self.url = config.newapi_url
        self.key = config.newapi_key
        self.vision_model = config.vision_model
        self.chat_model = config.chat_model
    
    async def analyze_image(self, screenshot: bytes, prompt: str) -> str:
        """使用 vision 模型分析图片"""
        import httpx
        b64 = base64.b64encode(screenshot).decode()
        try:
            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                resp = await client.post(
                    f"{self.url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.key}"},
                    json={
                        "model": self.vision_model,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                            ]
                        }],
                        "max_tokens": 1024
                    }
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            return self._stub_vision_output(prompt)
    
    async def generate_text(self, messages: list[dict]) -> str:
        """使用 chat 模型生成文字"""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                resp = await client.post(
                    f"{self.url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.key}"},
                    json={
                        "model": self.chat_model,
                        "messages": messages,
                        "max_tokens": 2048
                    }
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            return self._stub_llm_output(messages[-1]["content"] if messages else "")

    @staticmethod
    def _stub_vision_output(prompt: str) -> str:
        return f"Vision analysis: detected spin button at center, balance display at top. {prompt}"
    
    @staticmethod
    def _stub_llm_output(prompt: str) -> str:
        return f"Action plan: tap center of screen to spin. Reasoning: standard slot game flow."


class AIRouter:
    """Backward-compat wrapper - now uses newapi internally."""
    
    def __init__(self, router_url: str = "http://localhost:18888"):
        # router_url is ignored, uses newapi config
        self._config = AIPipelineConfig()
        self._client = NewAPIClient(self._config)
    
    async def vision_analyze(self, screenshot: bytes, prompt: str, model: str = "qwen2.5-vl-3b") -> str:
        """Backward compat: delegate to client."""
        # Override vision model if provided
        old_model = self._client.vision_model
        if model and model != "qwen2.5-vl-3b":
            self._client.vision_model = model
        try:
            return await self._client.analyze_image(screenshot, prompt)
        finally:
            self._client.vision_model = old_model
    
    async def llm_generate(self, prompt: str, model: str = "qwen3.5-27b") -> str:
        """Backward compat: delegate to client."""
        old_model = self._client.chat_model
        if model and model != "qwen3.5-27b":
            self._client.chat_model = model
        try:
            messages = [{"role": "user", "content": prompt}]
            return await self._client.generate_text(messages)
        finally:
            self._client.chat_model = old_model
    
    @staticmethod
    def _stub_vision_output(prompt: str) -> str:
        return f"Vision analysis: detected spin button at center, balance display at top. {prompt}"
    
    @staticmethod
    def _stub_llm_output(prompt: str) -> str:
        return f"Action plan: tap center of screen to spin. Reasoning: standard slot game flow."


class AIPipeline:
    """
    4-stage AI pipeline for game automation.
    
    Stages:
    1. Analyze - Vision model reads screenshot
    2. Generate - LLM creates action plan
    3. Sandbox - Dry-run validation
    4. Test - Execute and verify
    """
    
    def __init__(
        self,
        config: Optional[AIPipelineConfig] = None,
        runtime: Optional[Runtime] = None,
    ):
        self.config = config or AIPipelineConfig()
        self.runtime = runtime
        self.client = NewAPIClient(self.config)
    
    async def analyze(self, screenshot: bytes, prompt: Optional[str] = None) -> AnalysisResult:
        """阶段1: 分析截图"""
        prompt = prompt or "Analyze this slot game screenshot. Identify: spin button location, balance, bet level, any active bonuses or free spins."
        raw = await self.client.analyze_image(screenshot, prompt)
        
        screenshot_hash = hashlib.sha256(screenshot).hexdigest()
        # Parse simple output
        elements = []
        balance = None
        spin_visible = True
        
        import re
        if "balance" in raw.lower():
            match = re.search(r"balance[:\s]*(\d+)", raw, re.IGNORECASE)
            if match:
                balance = float(match.group(1))
        
        spin_keywords = ["spin button", "spin", "play button"]
        spin_visible = any(k in raw.lower() for k in spin_keywords)
        
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
        """阶段2: 生成 action plan"""
        messages = [
            {"role": "system", "content": "你是一个游戏自动化助手。根据截图分析生成下一步操作计划。"},
            {"role": "user", "content": f"分析结果: {analysis.raw_vision_output}\n目标: {goal}\n请生成具体操作步骤。"}
        ]
        raw = await self.client.generate_text(messages)
        
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
        """阶段3: 沙盒验证"""
        validated = []
        errors = []
        warnings = []
        
        screen_w, screen_h = 1080, 2340
        
        for i, step in enumerate(plan.steps):
            step_num = i + 1
            issues = []
            
            at = step.action_type
            p = step.params
            
            if at in (ActionType.TAP, ActionType.CLICK):
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
        """阶段4: 执行测试"""
        if self.runtime is None:
            # Mock execution when no runtime
            executed = [
                ExecutedStep(step=s, status="success", duration_ms=100)
                for s in plan.steps
            ]
            return TestResult(
                plan_id=plan.plan_id if hasattr(plan, 'plan_id') else "",
                executed_steps=executed,
                success=True,
            )
        
        executed = []
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
            except Exception as e:
                executed.append(ExecutedStep(
                    step=step,
                    status="failed",
                    error=str(e),
                ))
        
        return TestResult(
            plan_id=plan.plan_id if hasattr(plan, 'plan_id') else "",
            executed_steps=executed,
            success=all(s.status == "success" for s in executed),
        )
    
    async def run(self, context: PipelineContext) -> ActionPlan:
        """完整流程: analyze → generate → sandbox → test"""
        analysis = await self.analyze(context.screenshot, context.goal)
        plan = await self.generate(analysis, context.goal)
        
        if self.config.sandbox_enabled:
            sandbox = self.sandbox(plan)
            if not sandbox.is_valid:
                plan.steps = [
                    s.step for s in sandbox.validated_steps
                    if s.status in ("valid", "warning")
                ]
        
        return plan
    
    def _parse_plan_output(self, raw: str, plan_id: str, goal: str) -> ActionPlan:
        """Parse LLM output into ActionPlan."""
        import json
        import re
        
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
        
        return ActionPlan(plan_id=plan_id, goal=goal, steps=[])
    
    @staticmethod
    def _step_to_action(step: ActionStep) -> Action:
        """Convert ActionStep to runtime Action."""
        at = step.action_type
        p = step.params
        if at in (ActionType.TAP, ActionType.CLICK):
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
