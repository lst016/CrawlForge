# MODULE-06-evolution.md — Self-Evolution Engine

> **Module ID:** 06  
> **Depends on:** MODULE-01 (foundation), MODULE-03 (ai-pipeline), MODULE-04 (react-loop)  
> **Reference Influence:** PantheonOS's genetic evolution + crawl4ai integration

---

## Module Overview

MODULE-06 implements a **genetic evolution engine** that evolves game automation strategies over time. Inspired by PantheonOS:

- **Population** of strategy genomes (bet sizing, spin timing, game selection)
- **Fitness function** based on session ROI + data collection completeness
- **Selection** via tournament selection
- **Crossover** via uniform crossover
- **Mutation** via Gaussian perturbation
- **Integration** with crawl4ai-style adaptive crawling for competitor activity detection

Evolution runs in the background, evaluating strategies from MODULE-09 data, and produces improved genomes that MODULE-10 scheduler applies.

---

## Dependencies

| Module | Dependency Type | Reason |
|---|---|---|
| MODULE-01 | **Hard** | Imports dataclasses, exceptions |
| MODULE-03 | **Hard** | Uses AIPipeline for plan generation (evolved strategies) |
| MODULE-04 | **Hard** | Uses ReActLoop for execution |

### External Dependencies
```txt
# Genetic algorithm (or custom implementation)
# No external GA library — custom for fine control

# For numerical stability
numpy>=1.24.0

# Data persistence for population
dill>=0.3.7  # better pickle alternative for lambdas
```

---

## API Design

### EvolutionEngine

```python
class EvolutionEngine:
    """Genetic evolution engine for strategy optimization."""
    
    def __init__(
        self,
        config: EvolutionConfig,
        event_bus: EventBus,
        data_collector: DataCollector | None = None  # from MODULE-09
    ):
        self._config = config
        self._event_bus = event_bus
        self._data_collector = data_collector
        self._population: Population | None = None
        self._generation = 0
        self._best_genome: Genome | None = None
    
    # ── Lifecycle ──
    
    def initialize_population(self) -> Population:
        """Initialize a new random population."""
    
    def load_population(self, path: Path) -> Population:
        """Load a saved population from disk."""
    
    def save_population(self, path: Path) -> None:
        """Save current population to disk."""
    
    # ── Evolution Cycle ──
    
    def evolve_one_generation(self) -> EvolutionResult:
        """Run one complete generation: evaluate → select → crossover → mutate."""
    
    def evaluate_population(self) -> list[float]:
        """Evaluate fitness for all genomes in population."""
    
    def select_parents(self, fitness_scores: list[float]) -> list[Genome]:
        """Select parent genomes via tournament selection."""
    
    def crossover(self, parent1: Genome, parent2: Genome) -> Genome:
        """Uniform crossover of two parent genomes."""
    
    def mutate(self, genome: Genome) -> Genome:
        """Apply Gaussian mutation to a genome."""
    
    # ── Scheduling ──
    
    def should_evolve(self) -> bool:
        """Check if enough new data is available to justify evolution."""
    
    def get_best_genome(self) -> Genome | None:
        """Return the best genome from current population."""
    
    def apply_genome(self, genome: Genome) -> None:
        """Apply a genome's strategy to the active scheduler (MODULE-10)."""
```

### Genome (Strategy Encoding)

```python
@dataclass
class Genome:
    """A single strategy genome — encodes all tunable strategy parameters."""
    genome_id: str                     # UUID
    generation: int
    
    # ── Betting Strategy ──
    base_bet: float                    # base bet amount
    bet_multiplier: float               # bet = base_bet * bet_multiplier ^ level
    max_bet: float                     # absolute max bet
    min_bet: float                     # absolute min bet
    
    # ── Spin Strategy ──
    spins_per_session: int             # target spins per game session
    spin_delay_ms: int                 # delay between spins (humanization)
    stop_on_loss: float                # stop if balance drops by this amount
    stop_on_win: float                 # stop if balance rises by this amount
    
    # ── Game Selection ──
    preferred_providers: list[str]     # e.g., ["pragmatic_play", "pg_soft"]
    rtp_threshold: float               # minimum RTP to consider
    volatility_preference: Literal["low", "medium", "high"]
    
    # ── Activity Detection ──
    activity_check_interval_ms: int    # how often to check for activity/promo
    activity_priority_threshold: float  # only pursue activities above this score
    
    # ── Meta ──
    fitness: float = 0.0               # updated after evaluation
    created_at: datetime = field(default_factory=datetime.now)
    parent_ids: tuple[str, str] | None = None  # for lineage tracking

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> Genome: ...
```

### Population

```python
@dataclass
class Population:
    """A population of strategy genomes."""
    population_id: str
    generation: int
    genomes: list[Genome]
    config: EvolutionConfig
    fitness_history: list[float]       # best fitness per generation
    
    @property
    def best_genome(self) -> Genome | None:
        """Return genome with highest fitness."""
    
    @property
    def average_fitness(self) -> float: ...
    
    @property
    def diversity(self) -> float:
        """Measure of genetic diversity (avg pairwise distance)."""

@dataclass
class EvolutionConfig:
    """Configuration for the evolution engine."""
    population_size: int = 50
    elite_count: int = 5               # top N genomes carry over unchanged
    tournament_size: int = 5
    crossover_rate: float = 0.7
    mutation_rate: float = 0.1
    mutation_strength: float = 0.2     # Gaussian sigma as fraction of range
    min_fitness_samples: int = 30      # minimum spin data before evolving
    evolve_interval_seconds: int = 3600  # evolve at most once per hour

@dataclass
class EvolutionResult:
    """Result of one evolution generation."""
    generation: int
    best_fitness: float
    average_fitness: float
    new_genomes: list[Genome]
    best_genome: Genome
    elapsed_ms: int
    crossover_count: int
    mutation_count: int
```

### Fitness Function

```python
class FitnessFunction:
    """Evaluates how good a genome's strategy is."""
    
    def __init__(self, data_collector: DataCollector):
        self._dc = data_collector
    
    def evaluate(self, genome: Genome, session_data: list[SpinResult]) -> float:
        """
        Compute fitness score for a genome based on session data.
        
        Fitness = w1 * ROI + w2 * data_quality + w3 * consistency
        """
    
    def compute_roi(self, session_data: list[SpinResult]) -> float:
        """Return-of-Investment component."""
    
    def compute_data_quality(self, session_data: list[SpinResult]) -> float:
        """How complete the reel stop data is."""
    
    def compute_consistency(self, session_data: list[SpinResult]) -> float:
        """How consistent the strategy execution was (low deviation from plan)."""
    
    # Weights (configurable)
    ROI_WEIGHT: float = 0.5
    DATA_QUALITY_WEIGHT: float = 0.3
    CONSISTENCY_WEIGHT: float = 0.2
```

### Integration with crawl4ai (PantheonOS)

```python
class AdaptiveCrawlStrategy:
    """Adaptive strategy that evolves based on competitor activity patterns."""
    
    def __init__(self, evolution_engine: EvolutionEngine, event_bus: EventBus):
        self._engine = evolution_engine
        self._event_bus = event_bus
    
    def on_activity_detected(self, activity: CompetitorActivity) -> None:
        """When competitor activity is detected, update evolution weights."""
    
    def get_adaptive_interval(self, activity_type: str) -> int:
        """Get crawl interval based on activity type and current evolution state."""
    
    def should_prioritize_activity(
        self, 
        activity: CompetitorActivity, 
        current_genome: Genome
    ) -> bool:
        """Decide if activity should interrupt current strategy."""
```

---

## Data Structures

| Structure | Fields | Purpose |
|---|---|---|
| `Genome` | bet, spin, game selection, activity params + fitness | Strategy encoding |
| `Population` | population_id, generation, genomes, fitness_history | GA population |
| `EvolutionConfig` | population_size, elite, tournament, crossover, mutation rates | GA hyperparameters |
| `EvolutionResult` | generation, best/avg fitness, new genomes, timing stats | Generation output |
| `FitnessFunction` | data_collector reference | Fitness computation |
| `AdaptiveCrawlStrategy` | engine, event_bus | PantheonOS-style adaptive crawl |
| `CompetitorActivity` | source, type, title, description, confidence, screenshot | Activity data (from MODULE-09) |

---

## Implementation Steps

### Step 1: Config + Genome Dataclass (Day 1 - 1 hr)
```bash
mkdir -p src/crawlforge/evolution

# Write config.py with EvolutionConfig
# Write genome.py with Genome dataclass
# Implement to_dict() / from_dict() serialization
```

### Step 2: Population Management (Day 1 - 1 hr)
```python
# Write population.py
# Implement Population class with CRUD operations
# Implement initialize_population() with random genomes
# Diversity metric: average pairwise Euclidean distance in gene space
```

### Step 3: Selection + Crossover + Mutation (Day 2 - 2 hrs)
```python
# Write operators.py
# implement tournament_selection(population, fitness, tournament_size)
# implement uniform_crossover(parent1, parent2) — gene-by-gene flip
# implement gaussian_mutate(genome, mutation_rate, mutation_strength)
# Track parent_ids for lineage
```

### Step 4: Fitness Function (Day 2 - 2 hrs)
```python
# Write fitness.py
# Implement FitnessFunction.evaluate()
# Compute ROI = (final_balance - initial_balance) / initial_balance
# Compute data_quality = % of spins with complete reel_stop data
# Compute consistency = 1 - (actual_bet_deviation / expected_bet_deviation)
# Weights: 0.5 ROI + 0.3 data_quality + 0.2 consistency
```

### Step 5: Evolution Cycle (Day 3 - 1.5 hrs)
```python
# Write engine.py (EvolutionEngine class)
# implement evolve_one_generation()
# implement should_evolve() — check min_fitness_samples + evolve_interval
# Elite preservation: top 5 genomes carry over unchanged
# Generate rest via crossover + mutation
```

### Step 6: Adaptive Crawl Integration (Day 3 - 1.5 hrs)
```python
# Write adaptive_crawl.py
# AdaptiveCrawlStrategy.on_activity_detected()
# Increase activity_check_interval_ms when activity detected
# Interrupt current strategy for high-priority activities
# Emit evolution events to event bus
```

### Step 7: Scheduler Integration (Day 3 - 1 hr)
```python
# EvolutionEngine.apply_genome() updates scheduler strategy
# MODULE-10 scheduler reads best_genome periodically
# Test: evolve for 10 generations, verify fitness improves
```

---

## Testing Strategy

| Test | What | Method |
|---|---|---|
| `test_genome_serialization_roundtrip` | Genome saves and loads correctly | Unit test |
| `test_population_initialization` | Population has correct size + diversity | Unit test |
| `test_tournament_selection` | Top genomes selected more often | Statistical test |
| `test_crossover_preserves_gene_ranges` | Crossover respects min/max bounds | Unit test |
| `test_gaussian_mutation_stays_in_bounds` | Mutations respect gene ranges | Unit test |
| `test_fitness_computes_roi` | ROI computed correctly from spin data | Unit test |
| `test_evolution_improves_best_fitness` | Best fitness increases over generations | Mock data, 10 gens |
| `test_elite_preserved` | Top 5 genomes carry over unchanged | Unit test |
| `test_should_evolve_respects_interval` | Rate limiting works | Mock time |

---

## Success Criteria

1. ✅ Population initializes with `population_size` random genomes
2. ✅ Tournament selection favors higher-fitness genomes (statistically significant)
3. ✅ Uniform crossover produces valid offspring (all genes in range)
4. ✅ Gaussian mutation maintains gene bounds
5. ✅ Elite genomes (top 5) carry over unchanged to next generation
6. ✅ Fitness function returns 0.0-1.0 normalized score
7. ✅ After 10 generations with consistent data, best_fitness improves
8. ✅ `should_evolve()` respects `evolve_interval_seconds`
9. ✅ `save_population()` / `load_population()` roundtrip correctly
10. ✅ `apply_genome()` correctly updates scheduler's active strategy
