"""
CrawlForge - AI-Driven Slot Game Crawler Framework
"""

__version__ = "0.2.0"
__author__ = "CrawlForge Team"

from .core import (
    GameState, Action, GameData, ActionResult, DetectionResult, RuntimeType,
    CrawlForgeError, AdapterError, DetectionError, ExecutionError,
    TemplateMatchError, EvolutionError, RuntimeError, ConfigurationError,
    Runtime, GameAdapter,
)
from .detector import (
    SlotPhase, SpinState, BalanceState,
    SlotGameDetector, SlotUI, SlotDetectionResult,
)
from .template_store import TemplateStore, Template, MatchResult, TemplateMatcher
from .uiauto import UIAutoRuntime, UIElement, UIElementEncoder
from .ai_pipeline import AIPipeline, AIRouter, PipelineConfig, PipelineContext
from .react import ReActLoop, ReActConfig, LoopResult

__all__ = [
    # Core
    "GameState", "Action", "GameData", "ActionResult", "DetectionResult",
    "RuntimeType", "CrawlForgeError", "AdapterError", "DetectionError",
    "ExecutionError", "TemplateMatchError", "EvolutionError",
    "RuntimeError", "ConfigurationError", "Runtime", "GameAdapter",
    # Detector
    "SlotPhase", "SpinState", "BalanceState",
    "SlotGameDetector", "SlotUI", "SlotDetectionResult",
    # Template
    "TemplateStore", "Template", "MatchResult", "TemplateMatcher",
    # uIAuto
    "UIAutoRuntime", "UIElement", "UIElementEncoder",
    # AI Pipeline
    "AIPipeline", "AIRouter", "PipelineConfig", "PipelineContext",
    # ReAct
    "ReActLoop", "ReActConfig", "LoopResult",
]
