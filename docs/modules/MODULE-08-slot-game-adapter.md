# MODULE-08-slot-game-adapter.md — Slot Game Adapter

> **Module ID:** 08  
> **Depends on:** MODULE-01, MODULE-02, MODULE-04, MODULE-05, MODULE-07  
> **Reference Influence:** bombcrypto-bot's game-specific logic + custom slot game domain knowledge

---

## Module Overview

MODULE-08 is the **domain-specific adapter** for slot game automation. It wraps the generic ReAct loop (MODULE-04) and template matching (MODULE-07) with slot-game intelligence:

- **State detection**: identify spin button, balance, free spin indicators, bonus rounds
- **Activity extraction**: detect promo banners, bonus triggers, competitor activity
- **Reel/stop detection**: extract symbol positions for algorithm analysis (MODULE-09)
- **Multi-template support**: handle different slot providers (Pragmatic Play, PG Soft, etc.)

This is the module most specific to the user's requirements (slot games / 棋牌类, competitor activity, algorithm analysis).

---

## Dependencies

| Module | Dependency Type | Reason |
|---|---|---|
| MODULE-01 | **Hard** | All dataclasses, exceptions |
| MODULE-02 | **Hard** | Runtime for screenshot and tap actions |
| MODULE-04 | **Hard** | ReActLoop for execution |
| MODULE-05 | **Hard** | CheckpointManager for state persistence |
| MODULE-07 | **Hard** | TemplateMatcher for visual detection |

### External Dependencies
```txt
# Image processing for reel extraction
Pillow>=10.0.0
numpy>=1.24.0

# Optional: game-specific APIs if available
# (depends on target platforms — leave extensible)
```

---

## API Design

### SlotGameAdapter

```python
class SlotGameAdapter:
    """
    Domain adapter for slot game automation.
    Wraps ReActLoop with slot-game-specific state machine and detection.
    """
    
    def __init__(
        self,
        game: GameDefinition,
        runtime: Runtime,
        template_matcher: TemplateMatcher,
        react_loop: ReActLoop,
        checkpoint_manager: CheckpointManager,
        config: SlotGameConfig | None = None
    ):
        self._game = game
        self._runtime = runtime
        self._matcher = template_matcher
        self._loop = react_loop
        self._checkpoint = checkpoint_manager
        self._config = config or SlotGameConfig()
        self._state_machine = SlotStateMachine()
        self._provider_templates: dict[str, GameTemplates] = {}
    
    # ── Lifecycle ──
    
    def initialize(self) -> None:
        """Initialize the adapter: load templates, detect provider."""
    
    def start_session(self, initial_balance: float) -> GameSession:
        """Start a new game session."""
    
    def end_session(self) -> GameSession:
        """End current session and save final state."""
    
    # ── State Detection ──
    
    def detect_state(self, screenshot: bytes) -> SlotGameState:
        """Detect current slot game state from screenshot."""
    
    def find_spin_button(self, screenshot: bytes) -> tuple[int, int] | None:
        """Find spin button coordinates. Uses template matching + AI fallback."""
    
    def read_balance(self, screenshot: bytes) -> float | None:
        """Read current balance from screenshot (OCR or template)."""
    
    def is_free_spin_active(self, screenshot: bytes) -> bool:
        """Detect if free spin mode is active."""
    
    def is_bonus_round(self, screenshot: bytes) -> bool:
        """Detect if bonus round is active."""
    
    # ── Reel / Stop Detection ──
    
    def extract_reel_stops(self, screenshot: bytes) -> list[list[int]] | None:
        """
        Extract reel stop positions from screenshot.
        Returns matrix of symbol indices: [[r1c1, r1c2, ...], [r2c1, ...], ...]
        Uses column crop + row segmentation per reel.
        """
    
    def detect_symbols_by_column(
        self, 
        screenshot: bytes, 
        reel_config: ReelConfig
    ) -> list[list[int]]:
        """Detect symbols column by column using template matching."""
    
    def segment_reel_columns(
        self, 
        screenshot: bytes, 
        reel_config: ReelConfig
    ) -> list[np.ndarray]:
        """Segment screenshot into individual reel columns."""
    
    # ── Activity Extraction ──
    
    def extract_activity_info(self, screenshot: bytes) -> list[CompetitorActivity]:
        """Extract competitor activity info from screenshot (promo banners, bonuses)."""
    
    def detect_promo_banner(self, screenshot: bytes) -> CompetitorActivity | None:
        """Detect promotional banners."""
    
    def detect_bonus_trigger(self, screenshot: bytes) -> CompetitorActivity | None:
        """Detect bonus round trigger UI."""
    
    def extract_bonus_info(self, screenshot: bytes) -> BonusInfo | None:
        """Extract bonus round details (type, multiplier, requirements)."""
    
    # ── Actions ──
    
    def spin(self, bet_amount: float | None = None) -> SpinResult:
        """Execute a single spin. Finds spin button, taps, waits for result."""
    
    def collect_bonus(self) -> bool:
        """Tap to collect active bonus."""
    
    def collect_promo(self, activity: CompetitorActivity) -> bool:
        """Tap to collect a promotional bonus."""
    
    def set_bet_level(self, level: int) -> bool:
        """Navigate to bet settings and set bet level."""
    
    # ── Provider-Specific Templates ──
    
    def register_provider_templates(
        self, 
        provider: str, 
        templates: GameTemplates
    ) -> None:
        """Register template images for a specific provider."""
    
    def select_provider_templates(self, provider: str) -> GameTemplates:
        """Get templates for a specific provider."""
    
    def detect_provider(self, screenshot: bytes) -> str | None:
        """Auto-detect slot game provider from screenshot."""
```

### SlotGameState

```python
@dataclass
class SlotGameState:
    """Complete state of a slot game at a point in time."""
    timestamp: datetime
    balance: float | None
    bet_level: int | None
    bet_amount: float | None
    spin_button: tuple[int, int] | None   # (x, y) if visible
    state: SpinState                      # from MODULE-01: IDLE, SPINNING, FREE_SPIN, BONUS_ROUND, BIG_WIN
    free_spins_remaining: int = 0
    bonus_active: bool = False
    reel_stops: list[list[int]] | None = None  # from MODULE-09 data
    detected_elements: list[UIElement] | None = None
    provider: str | None = None

@dataclass
class BonusInfo:
    """Information about an active or available bonus round."""
    bonus_type: BonusType
    multiplier: float | None
    spins_remaining: int | None
    requirements: str | None            # e.g., "land 3 scatters"
    screenshot: bytes | None = None

class BonusType(Enum):
    FREE_SPINS = "free_spins"
    PICK_BONUS = "pick_bonus"
    WHEEL_BONUS = "wheel_bonus"
    MULTIPLIER_BONUS = "multiplier_bonus"
    CASCADE_BONUS = "cascade_bonus"
```

### Slot State Machine

```python
class SlotStateMachine:
    """
    State machine for slot game flow.
    Validates transitions and ensures legal game actions.
    """
    
    def __init__(self):
        self._current_state: SpinState = SpinState.IDLE
        self._transition_log: list[StateTransition] = []
    
    def transition(self, new_state: SpinState, reason: str) -> bool:
        """
        Attempt state transition. Returns True if valid, False otherwise.
        Logs all transitions for debugging.
        """
    
    def validate_action(self, action: ActionType) -> bool:
        """Check if an action is legal in the current state."""
    
    @property
    def current_state(self) -> SpinState: ...
    
    @property
    def can_spin(self) -> bool:
        """True if we're in a state where spinning is legal."""
    
    @property
    def can_collect_bonus(self) -> bool:
        """True if bonus collection is available."""
    
    def reset(self) -> None: ...

@dataclass
class StateTransition:
    from_state: SpinState
    to_state: SpinState
    reason: str
    timestamp: datetime
```

### Config

```python
@dataclass
class SlotGameConfig:
    """Configuration for slot game adapter."""
    
    # Detection settings
    spin_button_threshold: float = 0.8
    balance_ocr_enabled: bool = True
    balance_template_matching: bool = True    # use template instead of OCR when available
    
    # Reel extraction
    reel_extraction_method: Literal["template", "ml", "hybrid"] = "hybrid"
    reel_column_overlap: float = 0.1         # overlap fraction for column segmentation
    symbol_template_dir: Path | None = None   # directory of symbol templates per game
    
    # Timing
    spin_result_wait_ms: int = 3000           # wait for reels to stop
    balance_update_wait_ms: int = 500        # wait for balance to update
    bonus_appear_wait_ms: int = 1000
    
    # Activity extraction
    activity_detection_enabled: bool = True
    promo_banner_threshold: float = 0.75
    activity_screenshot_on_detect: bool = True
    
    # Provider handling
    auto_detect_provider: bool = True
    default_provider: str = "pragmatic_play"
    fallback_provider: str = "generic"
```

### Provider Template Registry

```python
@dataclass
class ProviderTemplates:
    """Template images for a specific slot game provider."""
    provider: str
    game_id: str
    
    # UI Elements
    spin_button: str | None = None
    balance_display: str | None = None
    bet_level_up: str | None = None
    bet_level_down: str | None = None
    
    # State Indicators
    free_spin_active: str | None = None
    bonus_round_active: str | None = None
    big_win_indicator: str | None = None
    
    # Symbols (for reel extraction)
    symbols: dict[int, str] | None = None   # symbol_id → template_path
    
    # Activity Elements
    promo_banner: str | None = None
    bonus_collect_button: str | None = None
    
    # Provider-specific detection patterns
    provider_logo: str | None = None         # for auto-detection

class SlotGameTemplateRegistry:
    """Registry of templates for all supported slot game providers."""
    
    def __init__(self, templates_base_dir: Path):
        self._base_dir = templates_base_dir
        self._providers: dict[str, ProviderTemplates] = {}
    
    def register(self, provider: str, templates: ProviderTemplates) -> None:
        """Register templates for a provider."""
    
    def get(self, provider: str) -> ProviderTemplates | None: ...
    
    def list_providers(self) -> list[str]: ...
    
    def auto_detect_provider(self, screenshot: bytes) -> str | None:
        """Use provider_logo template to detect which provider the game is from."""
    
    def load_from_directory(self, provider: str, directory: Path) -> ProviderTemplates:
        """Auto-load templates from a directory structure."""
```

---

## Data Structures

| Structure | Fields | Purpose |
|---|---|---|
| `SlotGameState` | balance, bet, spin_button, state, free_spins, bonus, reels, elements, provider | Full game state snapshot |
| `BonusInfo` | bonus_type, multiplier, spins, requirements, screenshot | Bonus round details |
| `BonusType` | enum of bonus round types | Bonus classification |
| `SlotStateMachine` | current_state, transition_log | State validation |
| `StateTransition` | from, to, reason, timestamp | State change record |
| `SlotGameConfig` | thresholds, timing, extraction method, activity detection | Adapter configuration |
| `ProviderTemplates` | provider, game_id, all template paths | Per-provider template set |
| `SlotGameTemplateRegistry` | providers, base_dir | Template management |

---

## Implementation Steps

### Step 1: Config + State Machine (Day 1 - 1 hr)
```bash
mkdir -p src/crawlforge/slot_game

# Write config.py with SlotGameConfig
# Write state_machine.py with SlotStateMachine
# Define valid state transitions (IDLE→SPINNING→IDLE, etc.)
# Block illegal actions in validate_action()
```

### Step 2: SlotGameState + BonusInfo (Day 1 - 30 min)
```python
# Write models.py
# Define SlotGameState, BonusInfo, BonusType dataclasses
# Define StateTransition
```

### Step 3: State Detection (Day 1 - 2 hrs)
```python
# Write state_detection.py
# implement detect_state() — orchestrates all detection methods
# implement find_spin_button() — try MODULE-07 template matching first, then MODULE-03 AI fallback
# implement read_balance() — try template matching, then OCR fallback
# implement is_free_spin_active() — template match free_spin_indicator
# implement is_bonus_round() — template match bonus_round_active
```

### Step 4: Reel Stop Extraction (Day 2 - 2.5 hrs)
```python
# Write reel_extractor.py
# implement extract_reel_stops() — main entry point
# implement segment_reel_columns() — crop columns based on reel_config
# implement detect_symbols_by_column() — match each column against symbol templates
# Use hybrid approach: template matching for known symbols, ML for unknown
# Return matrix of symbol indices
```

### Step 5: Activity Extraction (Day 2 - 2 hrs)
```python
# Write activity_extractor.py
# implement extract_activity_info() — scan for all activity types
# implement detect_promo_banner() — template match promo_banner area
# implement detect_bonus_trigger() — detect bonus round entry UI
# implement extract_bonus_info() — parse bonus type, multiplier, requirements
# Return CompetitorActivity dataclasses (from MODULE-01)
```

### Step 6: Provider Templates (Day 3 - 1.5 hrs)
```python
# Write templates.py
# Define ProviderTemplates dataclass
# Implement SlotGameTemplateRegistry
# implement detect_provider() — match provider_logo template
# implement register_provider_templates() / get()
# Pre-register Pragmatic Play, PG Soft, Play'n GO, etc.
```

### Step 7: Spin + Action Execution (Day 3 - 1.5 hrs)
```python
# Write actions.py
# implement spin() — find button, tap, wait for result, record SpinResult
# implement collect_bonus() — tap collect button if visible
# implement set_bet_level() — navigate bet UI
# All actions go through state machine validation
# Emit events to event bus
```

### Step 8: Integration + End-to-End (Day 3 - 1.5 hrs)
```python
# Write adapter.py (SlotGameAdapter class)
# Orchestrate all sub-modules
# Connect to MODULE-04 ReActLoop
# Connect to MODULE-05 CheckpointManager
# Test with real slot game screenshots
```

---

## Testing Strategy

| Test | What | Method |
|---|---|---|
| `test_state_machine_allows_legal_transitions` | IDLE→SPINNING→IDLE allowed | Unit test |
| `test_state_machine_blocks_illegal_transitions` | SPINNING→SPINNING blocked | Unit test |
| `test_find_spin_button_finds_template` | Template match returns coordinates | Real screenshot |
| `test_find_spin_button_falls_back_to_ai` | Template fails → AI fallback called | Mock template failure |
| `test_read_balance_returns_float` | Balance parsed from screenshot | Real screenshot |
| `test_extract_reel_stops_returns_matrix` | Reel stops as list of symbol lists | Real screenshot |
| `test_extract_reel_stops_respects_reel_config` | Correct rows/cols based on config | Mock config |
| `test_detect_promo_banner_returns_activity` | Promo banner detected | Real screenshot |
| `test_provider_auto_detection` | Correct provider detected | Multiple screenshots |
| `test_spin_updates_state_machine` | State transitions correctly | Mock runtime |
| `test_activity_extraction_fires_event` | CompetitorActivity emitted | Mock EventBus |

---

## Success Criteria

1. ✅ `find_spin_button()` returns correct coordinates for Pragmatic Play slots
2. ✅ `find_spin_button()` falls back to AI (MODULE-03) when template matching fails
3. ✅ `read_balance()` returns float within 2 seconds of screenshot capture
4. ✅ `extract_reel_stops()` returns correct symbol matrix for configured reel layout
5. ✅ `is_free_spin_active()` correctly detects free spin mode
6. ✅ `is_bonus_round()` correctly detects bonus round entry
7. ✅ `extract_activity_info()` returns `CompetitorActivity` list for promo banners
8. ✅ State machine blocks illegal state transitions
9. ✅ `detect_provider()` correctly identifies Pragmatic Play, PG Soft, Play'n GO
10. ✅ Multi-template fallback: if Pragmatic template fails, falls back to generic
11. ✅ `spin()` waits for `spin_result_wait_ms` and records `SpinResult`
12. ✅ All adapter actions emit events to EventBus
13. ✅ Adapter works with both ADB and Playwright runtimes
