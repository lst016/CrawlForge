"""
Tests for Evolution Engine.
"""

import pytest
from crawlforge.evolution import (
    FitnessMetric, FitnessScore, EvolutionCandidate,
    FeedbackRecord, FitnessEvaluator, GeneticEngine, FeedbackCollector,
)


def test_fitness_score():
    score = FitnessScore(metric=FitnessMetric.WIN_RATE, score=0.8, weight=0.5)
    assert score.weighted_score == 0.4


def test_evolution_candidate():
    candidate = EvolutionCandidate(
        candidate_id="test-1",
        adapter_code="print('hello')",
        fitness_scores=[
            FitnessScore(metric=FitnessMetric.WIN_RATE, score=0.8, weight=0.5),
            FitnessScore(metric=FitnessMetric.SPINS_PER_HOUR, score=0.9, weight=0.5),
        ],
        generation=1,
    )
    assert candidate.total_fitness == pytest.approx(0.85)  # (0.8*0.5 + 0.9*0.5)


def test_feedback_collector():
    collector = FeedbackCollector()
    record = collector.record(
        candidate_id="c1",
        session_id="s1",
        action_taken="spin",
        expected="reels_spin",
        actual="reels_spin",
        success=True,
        balance_delta=10.0,
        spin_count=1,
    )
    assert record.candidate_id == "c1"
    assert record.success is True

    records = collector.get_for_candidate("c1")
    assert len(records) == 1

    records = collector.get_for_candidate("nonexistent")
    assert len(records) == 0


def test_fitness_evaluator():
    collector = FeedbackCollector()
    collector.record("c1", "s1", "spin", "spin", "spin", True, spin_count=1)
    collector.record("c1", "s1", "spin", "spin", "spin", False, spin_count=1)

    evaluator = FitnessEvaluator()
    scores = evaluator.evaluate("c1", collector.get_all())

    assert len(scores) == 5
    win_rate_score = next(s for s in scores if s.metric == FitnessMetric.WIN_RATE)
    assert win_rate_score.score == 0.5  # 1 success out of 2


def test_genetic_engine_crossover():
    engine = GeneticEngine(evaluator=FitnessEvaluator(), population_size=10)
    parent1 = EvolutionCandidate(candidate_id="p1", adapter_code="aaaa", fitness_scores=[], generation=0)
    parent2 = EvolutionCandidate(candidate_id="p2", adapter_code="bbbb", fitness_scores=[], generation=0)

    child = engine._crossover(parent1, parent2)
    assert child.candidate_id != "p1"
    assert child.candidate_id != "p2"
    assert len(child.adapter_code) == 4  # len(parent1.code)


def test_genetic_engine_mutate():
    engine = GeneticEngine(evaluator=FitnessEvaluator(), population_size=10, mutation_rate=1.0)
    parent = EvolutionCandidate(candidate_id="p1", adapter_code="aaaa", fitness_scores=[], generation=0)

    child = engine._mutate(parent)
    assert child.candidate_id != "p1"
    assert child.generation == 0  # Since evolve hasn't been called yet
