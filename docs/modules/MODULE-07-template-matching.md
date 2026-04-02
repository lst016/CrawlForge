# MODULE-07-template-matching.md — OpenCV Visual Fallback

> **Module ID:** 07  
> **Depends on:** MODULE-01 (foundation)  
> **Reference Influence:** bombcrypto-bot's OpenCV template matching + threshold config

---

## Module Overview

MODULE-07 provides **pixel-accurate visual fallback** using OpenCV template matching — the same technique that makes bombcrypto-bot resilient to UI changes. When UI selectors fail (or as a primary detection method for games with no accessibility API), this module finds game elements by matching template images against the screen.

Key features:
- **Multi-threshold matching** with confidence scoring
- **Auto-calibration** to find optimal threshold per template
- **Multi-template fallback** (try provider A → provider B → provider C)
- **Feature-based matching** (ORB/AKAZE) for scaled/rotated templates
- **Template caching** with hash-based invalidation

---

## Dependencies

| Module | Dependency Type | Reason |
|---|---|---|
| MODULE-01 | **Hard** | Imports dataclasses, exceptions |

### External Dependencies
```txt
# OpenCV
opencv-python>=4.8.0
opencv-python-headless>=4.8.0  # for server environments

# NumPy (required by OpenCV)
numpy>=1.24.0

# Requests (for downloading remote templates)
requests>=2.31.0

# hashlib + pathlib (stdlib)
```

---

## API Design

### TemplateMatcher

```python
class TemplateMatcher:
    """OpenCV-based visual template matching."""
    
    def __init__(self, config: TemplateMatcherConfig | None = None):
        self._config = config or TemplateMatcherConfig()
        self._template_cache: dict[str, np.ndarray] = {}
        self._threshold_cache: dict[str, float] = {}  # template → calibrated threshold
    
    # ── Core Matching ──
    
    def match(
        self,
        screenshot: bytes | np.ndarray,
        template_path: str,
        threshold: float | None = None
    ) -> list[MatchResult]:
        """
        Find all matches of template in screenshot.
        Returns list sorted by confidence (highest first).
        """
    
    def match_best(
        self,
        screenshot: bytes | np.ndarray,
        template_path: str,
        threshold: float | None = None
    ) -> MatchResult | None:
        """Return only the best match, or None if no match."""
    
    # ── Calibration ──
    
    def calibrate(
        self,
        reference_screenshot: bytes | np.ndarray,
        template_path: str,
        expected_position: tuple[int, int] | None = None
    ) -> float:
        """
        Find the optimal threshold for a template against a reference screenshot.
        If expected_position is provided, validates match is at correct location.
        """
    
    def calibrate_all(self, templates_dir: Path, reference_screenshot: bytes) -> dict[str, float]:
        """Calibrate all templates in a directory against a reference screenshot."""
    
    # ── Multi-Template Fallback ──
    
    def match_with_fallback(
        self,
        screenshot: bytes | np.ndarray,
        template_paths: list[str],
        threshold: float | None = None
    ) -> tuple[MatchResult | None, str]:
        """
        Try templates in order until one matches.
        Returns (match, matched_template_path).
        """
    
    # ── Feature-Based Matching ──
    
    def match_features(
        self,
        screenshot: bytes | np.ndarray,
        template_path: str,
        threshold: float = 0.7
    ) -> list[MatchResult]:
        """
        Use ORB/AKAZE feature matching for templates that may be
        scaled or rotated. Slower than template matching but more robust.
        """
    
    # ── Utility ──
    
    def get_template_size(self, template_path: str) -> tuple[int, int]:
        """Return (width, height) of a template image."""
    
    def validate_template(self, template_path: str) -> bool:
        """Check if a template image is valid (readable, non-empty)."""
```

### MatchResult

```python
@dataclass
class MatchResult:
    """Result of a template match operation."""
    template_name: str
    template_path: str
    x: int                              # top-left x of match in screenshot
    y: int                              # top-left y of match in screenshot
    width: int
    height: int
    confidence: float                   # 0.0 - 1.0
    method: MatchingMethod
    screenshot_hash: str               # hash of the screenshot matched against

    @property
    def center(self) -> tuple[int, int]:
        """Center coordinates of the match."""
        return (self.x + self.width // 2, self.y + self.height // 2)

@dataclass
class MatchingMethod(Enum):
    TEMPLATE_SQDIFF = "tm_sqdiff"       # Square difference (lower = better)
    TEMPLATE_CCOEFF = "tmccoef"         # Cross-correlation
    TEMPLATE_CCORR = "tmccorr"          # Correlation
    FEATURE_ORB = "feature_orb"        # ORB feature matching
    FEATURE_AKAZE = "feature_akaze"    # AKAZE feature matching
```

### Threshold Config (from bombcrypto-bot)

```python
@dataclass
class ThresholdConfig:
    """Per-template or per-element-type threshold configuration."""
    element_type: str                   # e.g., "spin_button", "balance"
    template_path: str
    default_threshold: float = 0.8
    calibrated_threshold: float | None = None
    matching_method: MatchingMethod = MatchingMethod.TEMPLATE_SQDIFF
    scale_range: tuple[float, float] = (0.8, 1.2)  # scale factors to try
    use_grayscale: bool = True
    preprocessed: bool = True          # apply histogram equalization

class ThresholdConfigRegistry:
    """Registry of threshold configs per game/element."""
    
    def __init__(self):
        self._configs: dict[str, dict[str, ThresholdConfig]] = {}  # game_id → element_type → config
    
    def register(self, game_id: str, element_type: str, config: ThresholdConfig) -> None:
        """Register a threshold config for a game element."""
    
    def get(self, game_id: str, element_type: str) -> ThresholdConfig | None: ...
    
    def load_from_yaml(self, yaml_path: Path) -> None:
        """Load configs from a YAML file."""
    
    def save_to_yaml(self, yaml_path: Path) -> None:
        """Save configs to a YAML file."""
```

### Template Calibrator

```python
class TemplateCalibrator:
    """Auto-calibrates template thresholds against known game states."""
    
    def __init__(self, template_matcher: TemplateMatcher):
        self._matcher = template_matcher
        self._calibration_data: dict[str, CalibrationRecord] = {}
    
    def calibrate_template(
        self,
        template_path: str,
        screenshots: list[tuple[bytes, bool]],  # (screenshot, should_match)
        target_fpr: float = 0.01                 # target false positive rate
    ) -> float:
        """
        Find threshold that achieves target false positive rate.
        should_match=True screenshots should contain the template.
        should_match=False screenshots should NOT contain the template.
        """
    
    def validate_threshold(
        self,
        template_path: str,
        threshold: float,
        test_screenshots: list[tuple[bytes, bool]]
    ) -> dict:
        """
        Validate threshold against test set.
        Returns precision, recall, F1.
        """

@dataclass
class CalibrationRecord:
    """Record of a template calibration session."""
    template_path: str
    calibrated_threshold: float
    calibration_screenshots: int
    precision: float
    recall: float
    f1: float
    calibrated_at: datetime
```

---

## Data Structures

| Structure | Fields | Purpose |
|---|---|---|
| `MatchResult` | template, position, size, confidence, method, hash | Single match result |
| `MatchingMethod` | enum of TM_SQDIFF, TM_CCOEFF, TM_CCORR, FEATURE_ORB, FEATURE_AKAZE | Match algorithm |
| `ThresholdConfig` | element_type, template_path, threshold, method, scale_range | Per-element threshold |
| `ThresholdConfigRegistry` | game_id → element_type → ThresholdConfig | Global threshold registry |
| `TemplateCalibrator` | matcher, calibration_data | Auto-calibration logic |
| `CalibrationRecord` | template, threshold, precision, recall, F1, timestamp | Calibration metadata |

---

## Implementation Steps

### Step 1: Config + MatchResult (Day 1 - 1 hr)
```bash
mkdir -p src/crawlforge/template_matching

# Write config.py with TemplateMatcherConfig, ThresholdConfig, MatchingMethod
# Write models.py with MatchResult, CalibrationRecord
# Verify OpenCV loads correctly
```

### Step 2: TemplateMatcher Core (Day 1 - 2 hrs)
```python
# Write matcher.py
# Implement match() using cv2.matchTemplate()
# Support TM_SQDIFF, TM_CCOEFF, TM_CCORR methods
# Normalize results to 0.0-1.0 confidence
# Implement match_best() — return top result only
# Handle bytes input (decode to numpy)
```

### Step 3: Template Cache + Size Validation (Day 1 - 1 hr)
```python
# Add template caching by template_path hash
# Implement get_template_size()
# Implement validate_template()
# Handle missing template files gracefully
```

### Step 4: Multi-Template Fallback (Day 2 - 1 hr)
```python
# Implement match_with_fallback()
# Try each template_path in order
# Return first match above threshold
# Track which template matched
```

### Step 5: Calibration (Day 2 - 2 hrs)
```python
# Write calibrator.py
# Implement calibrate() — binary search for optimal threshold
# If expected_position provided: verify match center is within tolerance
# Implement calibrate_all() — batch calibrate a directory
# Store calibrated thresholds in _threshold_cache
```

### Step 6: Feature-Based Matching (Day 2 - 1.5 hrs)
```python
# Implement match_features() using ORB descriptor
# Good for templates that may be scaled/rotated
# Use cv2.ORB_create() + cv2.BFMatcher()
# Return matches above threshold
```

### Step 7: ThresholdRegistry + YAML (Day 3 - 1.5 hrs)
```python
# Write registry.py (ThresholdConfigRegistry class)
# Implement load_from_yaml() / save_to_yaml()
# YAML format: game_id → element_type → threshold config
# Integrate with TemplateMatcher.match() to auto-use calibrated threshold
```

### Step 8: Integration with MODULE-02 (Day 3 - 1 hr)
```python
# OpenCVVisualRuntime (MODULE-02) uses TemplateMatcher
# On match failure: try feature-based matching as fallback
# Emit MatchResult to event bus
# Test with real slot game screenshots
```

---

## Testing Strategy

| Test | What | Method |
|---|---|---|
| `test_match_returns_results_above_threshold` | Match filters by threshold | Real screenshot + template |
| `test_match_best_returns_top_result` | match_best returns highest confidence | Real screenshot |
| `test_match_with_fallback_tries_in_order` | Fallback stops at first match | Mock templates |
| `test_calibration_finds_optimal_threshold` | Binary search converges | Mock calibration data |
| `test_feature_matching_handles_rotation` | ORB matching works on rotated template | Rotated test image |
| `test_template_cache_avoids_reload` | Same template not reloaded | Mock |
| `test_threshold_registry_yaml_roundtrip` | YAML save/load works | Temp file |
| `test_match_result_center_calculation` | center property correct | Unit test |

---

## Success Criteria

1. ✅ `match()` returns list of `MatchResult` sorted by confidence descending
2. ✅ `match_best()` returns `MatchResult` or `None` (no false positives below threshold)
3. ✅ `match_with_fallback()` tries templates in order and returns first match
4. ✅ `calibrate()` finds threshold that maximizes F1 on calibration set
5. ✅ Feature-based matching works on templates scaled up to 1.2x
6. ✅ Template cache prevents reloading same template
7. ✅ All matching methods normalize confidence to 0.0-1.0 range
8. ✅ `ThresholdConfigRegistry` loads/saves correctly to YAML
9. ✅ Calibration records stored and retrievable by template path
10. ✅ Integration with MODULE-02 OpenCVVisualRuntime works with real slot game screenshots
