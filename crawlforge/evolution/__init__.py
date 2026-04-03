"""
Evolution module - feedback-driven adapter optimization and self-healing.

Provides:
- FitnessEvaluator: Evaluate adapter fitness from feedback
- GeneticEngine: Genetic algorithm for adapter evolution
- FeedbackCollector: Collect and store feedback
- AdapterFixer: Automatic diagnosis and repair of adapter failures
- SelfHealingAdapter: Adapter wrapper with auto-repair capability
"""

from .engine import (
    FitnessEvaluator,
    FitnessMetric,
    FitnessScore,
    EvolutionCandidate,
    FeedbackRecord,
    EvolutionResult,
    GeneticEngine,
    FeedbackCollector,
)
from .fixer import (
    AdapterFixer,
    ErrorType,
    ErrorRecord,
    FixSuggestion,
    FixResult,
    SelfHealingAdapter,
)

__all__ = [
    # Engine
    "FitnessEvaluator",
    "FitnessMetric",
    "FitnessScore",
    "EvolutionCandidate",
    "FeedbackRecord",
    "EvolutionResult",
    "GeneticEngine",
    "FeedbackCollector",
    # Fixer
    "AdapterFixer",
    "ErrorType",
    "ErrorRecord",
    "FixSuggestion",
    "FixResult",
    "SelfHealingAdapter",
]
