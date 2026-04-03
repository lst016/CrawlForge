"""
CrawlForge - AI-Driven Slot Game Crawler Framework

A modular framework for automating game interactions, collecting data,
and evolving adapters through feedback-driven optimization.
"""

__version__ = "0.3.0"
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
from .ai_pipeline import AIPipeline, AIPipelineConfig, NewAPIClient, AIRouter, PipelineContext
from .react import ReActLoop, ReActConfig, LoopResult

# Adapter module
from .adapter import (
    GameAdapter,
    AdapterConfig,
    AdapterMetadata,
    GameAdapterMixin,
    SlotGameAdapter,
    PokerGameAdapter,
    ArcadeGameAdapter,
    AdapterRegistry,
    get_registry,
    register_adapter,
    create_adapter,
)

# Data module
from .data import (
    DataCollector,
    BatchCollector,
    AlgorithmAnalyzer,
    SpinRecord,
    SessionSummary,
    AlgorithmInsight,
    DataExporter,
    SchemaValidator,
)

# Scheduler module
from .scheduler import (
    PriorityQueue,
    TaskRunner,
    Task,
    TaskStatus,
    CronParser,
    CronScheduler,
    CronExpression,
    ScheduleEntry,
    RetryPolicy,
    RetryBudget,
    RetryManager,
    RetryResult,
    retry,
    retry_with_result,
    SessionPool,
    ScheduleStrategy,
    GameSession,
    ResourceGate,
)

# Evolution module
from .evolution import (
    FitnessEvaluator,
    FitnessMetric,
    FitnessScore,
    EvolutionCandidate,
    FeedbackRecord,
    EvolutionResult,
    GeneticEngine,
    FeedbackCollector,
    AdapterFixer,
    ErrorType,
    ErrorRecord,
    FixSuggestion,
    FixResult,
    SelfHealingAdapter,
)

# Runtimes module
from .runtimes import (
    ADBRuntime,
    PlaywrightRuntime,
)

# Checkpoint module
from .checkpoint.manager import (
    CheckpointManager,
    CheckpointData,
    IncrementalCheckpoint,
    RollbackManager,
    AutoSnapshotPolicy,
    AutoSnapshotStrategy,
    FileLock,
)

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
    # UIAuto
    "UIAutoRuntime", "UIElement", "UIElementEncoder",
    # AI Pipeline
    "AIPipeline", "AIPipelineConfig", "NewAPIClient", "AIRouter", "PipelineContext",
    # ReAct
    "ReActLoop", "ReActConfig", "LoopResult",
    # Adapters
    "GameAdapter", "AdapterConfig", "AdapterMetadata", "GameAdapterMixin",
    "SlotGameAdapter", "PokerGameAdapter", "ArcadeGameAdapter",
    "AdapterRegistry", "get_registry", "register_adapter", "create_adapter",
    # Data
    "DataCollector", "BatchCollector", "AlgorithmAnalyzer",
    "SpinRecord", "SessionSummary", "AlgorithmInsight",
    "DataExporter", "SchemaValidator",
    # Scheduler
    "PriorityQueue", "TaskRunner", "Task", "TaskStatus",
    "CronParser", "CronScheduler", "CronExpression", "ScheduleEntry",
    "RetryPolicy", "RetryBudget", "RetryManager", "RetryResult",
    "retry", "retry_with_result",
    "SessionPool", "ScheduleStrategy", "GameSession", "ResourceGate",
    # Evolution
    "FitnessEvaluator", "FitnessMetric", "FitnessScore",
    "EvolutionCandidate", "FeedbackRecord", "EvolutionResult",
    "GeneticEngine", "FeedbackCollector",
    "AdapterFixer", "ErrorType", "ErrorRecord",
    "FixSuggestion", "FixResult", "SelfHealingAdapter",
    # Runtimes
    "ADBRuntime", "PlaywrightRuntime",
    # Checkpoint
    "CheckpointManager", "CheckpointData", "IncrementalCheckpoint",
    "RollbackManager", "AutoSnapshotPolicy", "AutoSnapshotStrategy", "FileLock",
]
