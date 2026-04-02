# MODULE-09-data-collector.md — Game Data Collection & Algorithm Analysis

> **Module ID:** 09  
> **Depends on:** MODULE-01 (foundation), MODULE-08 (slot-game-adapter)  
> **Reference Influence:** PantheonOS's adaptive crawling + statistical analysis

---

## Module Overview

MODULE-09 collects and analyzes game data to support:
1. **Session data recording**: all spin results with balance changes
2. **Reel stop analysis**: symbol frequency, RTP calculation, volatility estimation
3. **Competitor activity intelligence**: extract and catalog competitor promotions
4. **Algorithm fingerprinting**: detect slot algorithm patterns (RNG characteristics, hit frequency)

This module feeds data to MODULE-06 (evolution engine) for fitness evaluation.

---

## Dependencies

| Module | Dependency Type | Reason |
|---|---|---|
| MODULE-01 | **Hard** | All dataclasses, SpinResult, CompetitorActivity |
| MODULE-08 | **Hard** | Uses SlotGameAdapter for data extraction |

### External Dependencies
```txt
# Statistical analysis
numpy>=1.24.0
scipy>=1.11.0  # for statistical tests

# Data persistence
pandas>=2.0.0  # for time-series analysis
pyarrow>=14.0.0  # for Parquet storage

# Visualization (optional for reports)
matplotlib>=3.7.0

# For RTP calculation
# (custom implementation, no external lib needed)
```

---

## API Design

### DataCollector

```python
class DataCollector:
    """Collects and analyzes slot game data."""
    
    def __init__(
        self,
        slot_adapter: SlotGameAdapter,
        event_bus: EventBus,
        storage_path: Path,
        config: DataCollectorConfig | None = None
    ):
        self._adapter = slot_adapter
        self._event_bus = event_bus
        self._storage = storage_path
        self._config = config or DataCollectorConfig()
        self._session_data: list[SpinResult] = []
        self._activities: list[CompetitorActivity] = []
    
    # ── Session Data Recording ──
    
    def record_spin(self, spin_result: SpinResult) -> None:
        """Record a single spin result."""
    
    def record_session(self, session: GameSession) -> None:
        """Record a complete game session."""
    
    # ── Reel Stop Analysis ──
    
    def analyze_reel_stops(self, spins: list[SpinResult]) -> ReelAnalysis:
        """Run statistical analysis on collected reel stops."""
    
    def compute_symbol_frequency(self, spins: list[SpinResult]) -> dict[int, float]:
        """Compute frequency of each symbol across all spins."""
    
    def compute_payline_hit_rate(self, spins: list[SpinResult]) -> dict[str, float]:
        """Compute hit rate per payline."""
    
    # ── RTP & Volatility ──
    
    def estimate_rtp(self, spins: list[SpinResult]) -> RTPEstimate:
        """Estimate Return-to-Player based on collected spin data."""
    
    def estimate_volatility(self, spins: list[SpinResult]) -> VolatilityEstimate:
        """Estimate game volatility (low/medium/high)."""
    
    def estimate_hit_frequency(self, spins: list[SpinResult]) -> float:
        """Estimate how often a winning combination occurs."""
    
    # ── Algorithm Analysis ──
    
    def detect_rng_patterns(self, spins: list[SpinResult]) -> RNGAnalysis:
        """Detect potential RNG patterns or anomalies."""
    
    def compute_symbol_correlation(self, spins: list[SpinResult]) -> dict[tuple[int, int], float]:
        """Compute correlation between symbol pairs across reels."""
    
    def detect_hot_streak(self, spins: list[SpinResult]) -> list[int]:
        """Detect spin indices that are part of a hot streak (above-expected wins)."""
    
    # ── Competitor Activity ──
    
    def record_activity(self, activity: CompetitorActivity) -> None:
        """Record a competitor activity observation."""
    
    def get_activity_summary(self, since: datetime | None = None) -> ActivitySummary:
        """Get summary of recorded competitor activities."""
    
    # ── Persistence ──
    
    def save_session_data(self, session_id: str) -> Path:
        """Save session data to Parquet file."""
    
    def load_session_data(self, session_id: str) -> list[SpinResult]: ...
    
    def export_csv(self, session_id: str, output_path: Path) -> None:
        """Export session data to CSV."""
```

### Statistical Analysis Results

```python
@dataclass
class ReelAnalysis:
    """Statistical analysis of reel stop data."""
    session_id: str
    total_spins: int
    symbol_frequency: dict[int, float]           # symbol_id → observed frequency
    expected_frequency: dict[int, float] | None  # from game metadata (if available)
    deviation_from_expected: dict[int, float]    # observed - expected
    symbol_correlation_matrix: np.ndarray | None  # correlation between reels
    anomalies: list[str]                          # detected anomalies
    confidence: float                             # analysis confidence 0-1

@dataclass
class RTPEstimate:
    """RTP estimation result."""
    estimated_rtp: float                          # 0.0 - 1.0+
    confidence_interval: tuple[float, float]      # (lower, upper)
    sample_size: int
    method: RTPMethod
    is_sufficient_sample: bool                   # True if sample >= min_spins
    confidence: float                             # 0.0 - 1.0

class RTPMethod(Enum):
    SIMPLE = "simple"            # (final - initial) / (total_bets)
    PAYTABLE = "paytable"       # sum(symbol_freq * payout) / total_bets
    SIMULATION = "simulation"   # Monte Carlo

@dataclass
class VolatilityEstimate:
    """Volatility estimation result."""
    volatility_index: float                # proprietary volatility index
    classification: Literal["low", "medium", "high"]
    std_deviation: float
    max_win_streak: int
    max_loss_streak: int
    sample_size: int

@dataclass
class RNGAnalysis:
    """RNG pattern detection result."""
    patterns_found: list[RNGPattern]
    randomness_score: float               # 0.0 (non-random) - 1.0 (random)
    chi_square_p_value: float | None      # None if insufficient data
    anomalies: list[str]
    recommendation: str                   # e.g., "RNG appears fair", "Possible bias detected"

@dataclass
class RNGPattern:
    pattern_type: RNGPatternType
    description: str
    significance: float                  # p-value or confidence
    affected_reels: list[int] | None

class RNGPatternType(Enum):
    REEL_BIAS = "reel_bias"               # certain symbols appear more on certain reels
    SEQUENCE_DEPENDENCY = "sequence_dependency"  # next spin influenced by previous
    CYCLE_DETECTION = "cycle_detection"   # repeating patterns in symbol sequences
    HOT_STREAK = "hot_streak"             # above-expected wins in sequence
    COLD_STREAK = "cold_streak"           # below-expected losses in sequence
```

### Competitor Activity Analysis

```python
@dataclass
class ActivitySummary:
    """Summary of competitor activities over a time period."""
    period_start: datetime
    period_end: datetime
    total_activities: int
    by_type: dict[str, int]               # activity_type → count
    by_provider: dict[str, int]           # source_game_id → count
    top_activities: list[CompetitorActivity]  # top 10 by confidence
    average_confidence: float

@dataclass
class ActivityTrend:
    """Trend analysis of competitor activities."""
    provider: str
    activity_type: str
    frequency_trend: Literal["increasing", "decreasing", "stable"]
    average_interval_hours: float
    last_seen: datetime
    prediction_next: datetime | None     # predicted next occurrence
```

---

## Data Structures

| Structure | Fields | Purpose |
|---|---|---|
| `ReelAnalysis` | session, spins, symbol_freq, expected_freq, deviation, correlation, anomalies | Reel statistical analysis |
| `RTPEstimate` | estimated_rtp, confidence_interval, sample_size, method, is_sufficient, confidence | RTP analysis result |
| `VolatilityEstimate` | volatility_index, classification, std_dev, streaks, sample_size | Volatility result |
| `RNGAnalysis` | patterns_found, randomness_score, chi_square_p, anomalies, recommendation | RNG pattern detection |
| `RNGPattern` | pattern_type, description, significance, affected_reels | Individual RNG pattern |
| `ActivitySummary` | period, totals, by_type, by_provider, top_activities, avg_confidence | Activity overview |
| `ActivityTrend` | provider, type, trend, interval, last_seen, prediction | Activity forecasting |
| `DataCollectorConfig` | storage_path, min_spins_for_analysis, save_interval | Collector configuration |

---

## Implementation Steps

### Step 1: Config + Data Recording (Day 1 - 1 hr)
```bash
mkdir -p src/crawlforge/data_collector

# Write config.py with DataCollectorConfig
# Write models.py with all analysis result dataclasses
# Implement DataCollector.record_spin() and record_session()
# Store in-memory list + write to Parquet on interval
```

### Step 2: RTP Calculation (Day 1 - 2 hrs)
```python
# Write rtp_calculator.py
# Implement estimate_rtp() — simple method: (final - initial) / total_bets
# Implement estimate_rtp_paytable() — sum of (symbol_freq * payout)
# Implement is_sufficient_sample() — check min_spins_for_analysis
# Compute confidence interval using binomial distribution
```

### Step 3: Volatility Estimation (Day 2 - 1.5 hrs)
```python
# Write volatility.py
# implement estimate_volatility()
# Compute std_deviation of net_win values
# Compute max_win_streak and max_loss_streak
# Classify: low (<0.5), medium (0.5-1.5), high (>1.5)
```

### Step 4: Symbol Frequency + Correlation (Day 2 - 1.5 hrs)
```python
# Write reel_analyzer.py
# implement compute_symbol_frequency()
# implement compute_symbol_correlation() — correlation matrix between reels
# implement detect_hot_streak() — sliding window of above-threshold wins
# Use numpy for efficient computation
```

### Step 5: RNG Pattern Detection (Day 3 - 2 hrs)
```python
# Write rng_analyzer.py
# implement detect_rng_patterns()
# implement chi_square_test() — test symbol distribution uniformity
# implement detect_sequence_dependency() — autocorrelation test
# implement detect_reel_bias() — per-reel symbol frequency comparison
# classify anomalies by severity
```

### Step 6: Competitor Activity (Day 3 - 1.5 hrs)
```python
# Write activity_analyzer.py
# Implement record_activity() — store CompetitorActivity
# Implement get_activity_summary() — aggregate statistics
# Implement detect_activity_trends() — frequency analysis per provider
# Use pandas for time-series aggregation
```

### Step 7: Persistence + Export (Day 3 - 1 hr)
```python
# Implement save_session_data() — Parquet via pyarrow
# Implement load_session_data()
# Implement export_csv() — for human review
# Auto-save every N spins or every minute
```

---

## Testing Strategy

| Test | What | Method |
|---|---|---|
| `test_rtp_simple_calculation` | RTP = (final - initial) / total_bets | Mock spin data |
| `test_rtp_paytable_method` | Paytable method matches expected | Known payout table |
| `test_volatility_classification` | Low/medium/high correctly classified | Mock variance data |
| `test_symbol_frequency_sums_to_one` | Frequencies sum to 1.0 | Unit test |
| `test_correlation_matrix_symmetric` | Correlation matrix is symmetric | numpy test |
| `test_hot_streak_detection` | Hot streaks detected in mock data | Mock streaks |
| `test_chi_square_goodness_of_fit` | Chi-square test on uniform distribution | scipy.stats |
| `test_activity_summary_by_type` | Summary correctly groups by type | Mock activities |
| `test_parquet_roundtrip` | Session data saves/loads correctly | Temp file |
| `test_csv_export` | CSV export readable | pandas read_csv |

---

## Success Criteria

1. ✅ `estimate_rtp()` returns RTP within ±2% of true RTP for 1000+ spin samples
2. ✅ `is_sufficient_sample()` returns True when spins >= min_spins_for_analysis
3. ✅ `estimate_volatility()` classifies volatility correctly based on std deviation
4. ✅ `compute_symbol_frequency()` returns frequencies that sum to 1.0
5. ✅ `detect_rng_patterns()` identifies sequence dependency at p < 0.05 significance
6. ✅ `compute_symbol_correlation()` returns symmetric correlation matrix
7. ✅ `detect_hot_streak()` identifies consecutive above-threshold wins
8. ✅ Competitor activities grouped and summarized by type and provider
9. ✅ Session data persists to Parquet and reloads correctly
10. ✅ All analysis results fire events to EventBus
11. ✅ Data feeds correctly into MODULE-06 fitness function
