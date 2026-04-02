"""
Evolution Engine - feedback-driven adapter optimization.

Provides:
- Fitness evaluation
- Genetic algorithm for adapter evolution
- Feedback collection and analysis
"""

import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any
from enum import Enum
import random


class FitnessMetric(Enum):
    """Metrics for fitness evaluation."""
    WIN_RATE = "win_rate"
    SPINS_PER_HOUR = "spins_per_hour"
    BALANCE_STABILITY = "balance_stability"
    ACTION_ACCURACY = "action_accuracy"
    DATA_QUALITY = "data_quality"


@dataclass
class FitnessScore:
    """Fitness evaluation result."""
    metric: FitnessMetric
    score: float  # 0.0 - 1.0
    weight: float = 1.0
    details: dict = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class EvolutionCandidate:
    """A candidate adapter for evolution."""
    candidate_id: str
    adapter_code: str
    fitness_scores: list[FitnessScore] = field(default_factory=list)
    generation: int = 0
    parent_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_fitness(self) -> float:
        return sum(s.weighted_score for s in self.fitness_scores)

    def fitness_hash(self) -> str:
        return hashlib.md5(self.adapter_code.encode()).hexdigest()[:8]


@dataclass
class FeedbackRecord:
    """Feedback from a game session."""
    feedback_id: str
    candidate_id: str
    session_id: str
    action_taken: str
    expected_outcome: str
    actual_outcome: str
    success: bool
    balance_delta: float = 0.0
    spin_count: int = 0
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class EvolutionResult:
    """Result of an evolution cycle."""
    generation: int
    best_candidate: EvolutionCandidate
    population: list[EvolutionCandidate]
    improvements: list[str]
    converged: bool


class FitnessEvaluator:
    """
    Evaluates adapter fitness based on collected feedback.
    """

    def __init__(self, weights: Optional[dict[FitnessMetric, float]] = None):
        default_weights = {
            FitnessMetric.WIN_RATE: 0.3,
            FitnessMetric.SPINS_PER_HOUR: 0.2,
            FitnessMetric.BALANCE_STABILITY: 0.25,
            FitnessMetric.ACTION_ACCURACY: 0.15,
            FitnessMetric.DATA_QUALITY: 0.1,
        }
        self.weights = weights or default_weights

    def evaluate(
        self,
        candidate_id: str,
        feedback_records: list[FeedbackRecord],
    ) -> list[FitnessScore]:
        """
        Evaluate a candidate's fitness from feedback records.
        """
        scores = []
        records = [r for r in feedback_records if r.candidate_id == candidate_id]

        if not records:
            return [FitnessScore(metric=m, score=0.0, weight=w) for m, w in self.weights.items()]

        # Win rate
        successes = sum(1 for r in records if r.success)
        win_rate = successes / len(records) if records else 0.0
        scores.append(FitnessScore(
            metric=FitnessMetric.WIN_RATE,
            score=win_rate,
            weight=self.weights.get(FitnessMetric.WIN_RATE, 1.0),
            details={"successes": successes, "total": len(records)},
        ))

        # Spins per hour (estimate from feedback)
        total_spins = sum(r.spin_count for r in records)
        if records:
            time_span = (records[-1].timestamp - records[0].timestamp).total_seconds() / 3600
            spins_per_hour = total_spins / max(time_span, 0.1)
            # Normalize: 1000 spins/hr = perfect
            spins_score = min(1.0, spins_per_hour / 1000)
        else:
            spins_score = 0.0
        scores.append(FitnessScore(
            metric=FitnessMetric.SPINS_PER_HOUR,
            score=spins_score,
            weight=self.weights.get(FitnessMetric.SPINS_PER_HOUR, 1.0),
        ))

        # Balance stability
        balance_deltas = [r.balance_delta for r in records]
        if balance_deltas:
            # Good stability = not too volatile
            avg_delta = sum(balance_deltas) / len(balance_deltas)
            # Score based on positive but not too volatile
            stability = 1.0 - min(1.0, abs(avg_delta) / 1000)
        else:
            stability = 0.0
        scores.append(FitnessScore(
            metric=FitnessMetric.BALANCE_STABILITY,
            score=stability,
            weight=self.weights.get(FitnessMetric.BALANCE_STABILITY, 1.0),
        ))

        # Action accuracy
        accurate = sum(1 for r in records if r.actual_outcome == r.expected_outcome)
        accuracy = accurate / len(records) if records else 0.0
        scores.append(FitnessScore(
            metric=FitnessMetric.ACTION_ACCURACY,
            score=accuracy,
            weight=self.weights.get(FitnessMetric.ACTION_ACCURACY, 1.0),
        ))

        # Data quality (has required fields)
        quality = 1.0 if all(r.metadata for r in records) else 0.5
        scores.append(FitnessScore(
            metric=FitnessMetric.DATA_QUALITY,
            score=quality,
            weight=self.weights.get(FitnessMetric.DATA_QUALITY, 1.0),
        ))

        return scores


class GeneticEngine:
    """
    Genetic algorithm for evolving adapter code.
    """

    def __init__(
        self,
        evaluator: FitnessEvaluator,
        population_size: int = 10,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
    ):
        self.evaluator = evaluator
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self._generation = 0
        self._population: list[EvolutionCandidate] = []

    def evolve(
        self,
        population: list[EvolutionCandidate],
        feedback: list[FeedbackRecord],
    ) -> EvolutionResult:
        """
        Run one generation of genetic evolution.

        1. Evaluate fitness
        2. Select parents
        3. Crossover
        4. Mutate
        """
        self._generation += 1

        # Evaluate fitness
        for candidate in population:
            if not candidate.fitness_scores:
                candidate.fitness_scores = self.evaluator.evaluate(
                    candidate.candidate_id, feedback
                )

        # Sort by total fitness
        sorted_pop = sorted(population, key=lambda c: c.total_fitness, reverse=True)

        # Selection: keep top performers
        survivors = sorted_pop[:max(2, self.population_size // 3)]

        # Generate new offspring
        offspring = []
        while len(offspring) + len(survivors) < self.population_size:
            parent1, parent2 = self._select_parents(survivors + sorted_pop)

            if random.random() < self.crossover_rate and parent1 and parent2:
                child = self._crossover(parent1, parent2)
            elif parent1:
                child = self._mutate(parent1)
            else:
                continue

            child.generation = self._generation
            offspring.append(child)

        new_population = survivors + offspring

        improvements = []
        if sorted_pop and new_population:
            old_best = sorted_pop[0].total_fitness
            new_best = max(c.total_fitness for c in new_population)
            if new_best > old_best:
                improvements.append(f"Fitness improved: {old_best:.3f} -> {new_best:.3f}")

        best = max(new_population, key=lambda c: c.total_fitness)
        converged = len(set(c.fitness_hash() for c in new_population)) <= 2

        return EvolutionResult(
            generation=self._generation,
            best_candidate=best,
            population=new_population,
            improvements=improvements,
            converged=converged,
        )

    def _select_parents(self, candidates: list[EvolutionCandidate]) -> tuple:
        """Tournament selection."""
        if len(candidates) < 2:
            return None, None
        a = random.choice(candidates)
        b = random.choice(candidates)
        return (a, b) if a.total_fitness >= b.total_fitness else (b, a)

    def _crossover(self, parent1: EvolutionCandidate, parent2: EvolutionCandidate) -> EvolutionCandidate:
        """Single-point crossover on adapter code."""
        code1, code2 = parent1.adapter_code, parent2.adapter_code
        min_len = min(len(code1), len(code2))
        if min_len < 2:
            return parent1

        point = random.randint(1, min_len - 1)
        new_code = code1[:point] + code2[point:]

        return EvolutionCandidate(
            candidate_id=str(uuid.uuid4())[:12],
            adapter_code=new_code,
            generation=self._generation,
            parent_ids=[parent1.candidate_id, parent2.candidate_id],
        )

    def _mutate(self, candidate: EvolutionCandidate) -> EvolutionCandidate:
        """Point mutation on adapter code."""
        code = list(candidate.adapter_code)
        for i in range(len(code)):
            if random.random() < self.mutation_rate:
                # Simple character mutation
                code[i] = chr(ord(code[i]) ^ random.randint(0, 31))
        return EvolutionCandidate(
            candidate_id=str(uuid.uuid4())[:12],
            adapter_code="".join(code),
            generation=self._generation,
            parent_ids=[candidate.candidate_id],
        )


class FeedbackCollector:
    """
    Collects and stores feedback from game sessions.
    """

    def __init__(self):
        self._records: list[FeedbackRecord] = []

    def record(
        self,
        candidate_id: str,
        session_id: str,
        action_taken: str,
        expected: str,
        actual: str,
        success: bool,
        balance_delta: float = 0.0,
        spin_count: int = 0,
        metadata: Optional[dict] = None,
    ) -> FeedbackRecord:
        """Record feedback from an action."""
        record = FeedbackRecord(
            feedback_id=str(uuid.uuid4())[:12],
            candidate_id=candidate_id,
            session_id=session_id,
            action_taken=action_taken,
            expected_outcome=expected,
            actual_outcome=actual,
            success=success,
            balance_delta=balance_delta,
            spin_count=spin_count,
            metadata=metadata or {},
        )
        self._records.append(record)
        return record

    def get_for_candidate(self, candidate_id: str) -> list[FeedbackRecord]:
        return [r for r in self._records if r.candidate_id == candidate_id]

    def get_all(self) -> list[FeedbackRecord]:
        return self._records.copy()

    def clear(self) -> None:
        self._records.clear()
