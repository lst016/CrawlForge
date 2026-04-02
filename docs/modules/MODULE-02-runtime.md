# MODULE-02-runtime.md — Multi-Runtime Abstraction

> **Module ID:** 02  
> **Depends on:** MODULE-01 (foundation)  
> **Reference Influence:** Autono's runtime abstraction + bombcrypto-bot's ADB setup

---

## Module Overview

MODULE-02 provides a unified abstraction layer over three execution runtimes:
1. **ADB + uiautomator2** — Android emulator/device control
2. **Playwright** — Web-based game automation
3. **OpenCV Visual** — Pixel-based fallback for when UI automation is unavailable

The `RuntimeManager` selects the appropriate runtime based on `GameDefinition.runtime` and exposes a consistent interface to callers (MODULE-08, MODULE-10).

---

## Dependencies

| Module | Dependency Type | Reason |
|---|---|---|
| MODULE-01 | **Hard** | Imports dataclasses, exceptions, interfaces |

### External Dependencies
```txt
# uiautomator2 — Android UI automation
uiautomator2>=2.12.0

# Playwright — Web automation
playwright>=1.40.0

# OpenCV — Visual fallback
opencv-python>=4.8.0

# pure-python-adb — ADB wrapper (no GUI dependency)
pure-python-adb>=0.3.0
```

---

## API Design

### RuntimeManager

```python
from pathlib import Path

class RuntimeManager:
    """Factory + singleton manager for all runtime instances."""
    
    def __init__(self, config: RuntimeConfig):
        self._config = config
        self._runtimes: dict[RuntimeType, Runtime] = {}
        self._active_runtime: Runtime | None = None
        self._event_bus: EventBus  # injected
    
    def get_runtime(self, runtime_type: RuntimeType) -> Runtime:
        """Get or create a runtime instance."""
    
    def select_runtime_for_game(self, game: GameDefinition) -> Runtime:
        """Auto-select the best runtime for a given game."""
    
    def connect_all(self) -> None:
        """Pre-connect all configured runtimes."""
    
    def disconnect_all(self) -> None:
        """Disconnect all runtimes cleanly."""
```

### ADBRuntime

```python
class ADBRuntime:
    """Android device control via ADB + uiautomator2."""
    
    def __init__(self, config: ADBConfig):
        self._config = config
        self._device: u2.Device | None = None
    
    # ── Connection ──
    def connect(self) -> None:
        """Connect to Android device/emulator via ADB."""
    
    def disconnect(self) -> None:
        """Disconnect from device."""
    
    def is_connected(self) -> bool:
        """Check if device is reachable."""
    
    # ── Screenshot ──
    def take_screenshot(self) -> bytes:
        """Capture screenshot as PNG bytes."""
    
    def get_xml_hierarchy(self) -> str:
        """Get UI hierarchy as XML (for selector-based queries)."""
    
    # ── Input Actions ──
    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Swipe from (x1,y1) to (x2,y2)."""
    
    def press_back(self) -> None: ...
    def press_home(self) -> None: ...
    def press_enter(self) -> None: ...
    
    # ── App Control ──
    def is_app_open(self, package_name: str) -> bool:
        """Check if an app is in the foreground."""
    
    def start_app(self, package_name: str, activity: str | None = None) -> None:
        """Launch an app by package name."""
    
    def stop_app(self, package_name: str) -> None:
        """Force-stop an app."""
    
    # ── Device Info ──
    def get_orientation(self) -> Literal["portrait", "landscape"]: ...
    def get_screen_size(self) -> tuple[int, int]: ...
    def get_display_density(self) -> int: ...
    
    # ── Raw ADB ──
    def execute_shell(self, command: str) -> str:
        """Execute raw ADB shell command."""
```

### PlaywrightRuntime

```python
class PlaywrightRuntime:
    """Web game automation via Playwright."""
    
    def __init__(self, config: PlaywrightConfig):
        self._config = config
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
    
    # ── Connection ──
    def connect(self) -> None:
        """Launch browser and create persistent context."""
    
    def disconnect(self) -> None:
        """Close browser (optional: keep context for persistence)."""
    
    def is_connected(self) -> bool: ...
    
    # ── Screenshot ──
    def take_screenshot(self, full_page: bool = False) -> bytes:
        """Capture page screenshot as PNG bytes."""
    
    # ── Input Actions ──
    def tap(self, selector: str) -> None:
        """Click element by CSS selector."""
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Simulate touch swipe via JavaScript."""
    
    def type_text(self, selector: str, text: str) -> None:
        """Type text into an input field."""
    
    def press_key(self, key: str) -> None:
        """Press a keyboard key."""
    
    # ── Navigation ──
    def navigate(self, url: str, wait_until: str = "networkidle") -> None:
        """Navigate to URL."""
    
    def wait_for_selector(self, selector: str, timeout_ms: int = 10000) -> None: ...
    
    # ── JavaScript ──
    def execute_js(self, script: str) -> Any:
        """Execute arbitrary JavaScript in page context."""
    
    # ── App Control ──
    def is_app_open(self, url_pattern: str) -> bool:
        """Check if current URL matches pattern."""
```

### OpenCVVisualRuntime

```python
class OpenCVVisualRuntime:
    """Visual-only automation using OpenCV template matching as fallback."""
    
    def __init__(self, config: VisualConfig, delegate_runtime: Runtime | None = None):
        self._config = config
        self._delegate = delegate_runtime  # optional ADB/Playwright delegate
        self._matcher: TemplateMatcher  # from MODULE-07
    
    # ── Connection ──
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...
    
    # ── Screenshot ──
    def take_screenshot(self) -> bytes: ...
    
    # ── Visual-Only Actions ──
    def tap_on_template(
        self, 
        template_path: str, 
        threshold: float = 0.8,
        on_multiple: Literal["first", "center", "all"] = "center"
    ) -> tuple[int, int] | list[tuple[int, int]]:
        """Find template in screenshot and tap it. Returns tap coordinates."""
    
    def wait_for_template(
        self, 
        template_path: str, 
        threshold: float = 0.8,
        timeout_ms: int = 10000
    ) -> tuple[int, int] | None:
        """Wait until a template appears on screen."""
    
    def wait_for_template_disappear(
        self, 
        template_path: str, 
        threshold: float = 0.8,
        timeout_ms: int = 10000
    ) -> bool:
        """Wait until a template disappears from screen."""
    
    # ── Delegate passthrough ──
    def tap(self, x: int, y: int) -> None:
        """Passthrough to delegate if available."""
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Passthrough to delegate if available."""
```

### Config Classes

```python
@dataclass
class RuntimeConfig:
    adb_config: ADBConfig | None = None
    playwright_config: PlaywrightConfig | None = None
    visual_config: VisualConfig | None = None
    default_timeout_ms: int = 15000

@dataclass
class ADBConfig:
    device_serial: str | None = None   # None = first available
    host: str = "127.0.0.1"
    port: int = 7555                   # MEmu/BlueStacks default
    screenshot_method: Literal["uiautomator2", "minicap"] = "uiautomator2"

@dataclass
class PlaywrightConfig:
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = False
    user_data_dir: Path | None = None  # for persistent context
    user_agent: str | None = None
    viewport: tuple[int, int] = (1280, 720)

@dataclass
class VisualConfig:
    default_threshold: float = 0.8
    max_retries: int = 3
    retry_delay_ms: int = 500
```

---

## Data Structures

| Structure | Fields | Purpose |
|---|---|---|
| `RuntimeConfig` | adb, playwright, visual configs | Global runtime configuration |
| `ADBConfig` | serial, host, port, screenshot_method | ADB connection parameters |
| `PlaywrightConfig` | browser, headless, user_data_dir | Playwright launch parameters |
| `VisualConfig` | threshold, retries, delay | OpenCV fallback parameters |
| `MatchResult` | x, y, confidence, template_name | Template match output |

---

## Implementation Steps

### Step 1: Config & Enums (Day 1 - 1 hr)
```bash
# Create directory
mkdir -p src/crawlforge/runtime

# Write config.py with all config dataclasses
# Write enums.py if any additional enums needed
```

### Step 2: ADBRuntime Implementation (Day 1 - 2 hrs)
```python
# Use uiautomator2 for UI interaction
# Use pure-python-adb for shell commands
# Implement screenshot via device.screenshot()
# Implement tap via device.click(x, y)
# Implement swipe via device.swipe()
# Test with: adb devices (verify emulator visible)
```

### Step 3: PlaywrightRuntime Implementation (Day 2 - 2 hrs)
```python
# Use playwright.sync_api
# Implement persistent context for login state
# Implement screenshot via page.screenshot()
# Implement tap via locator.click()
# Test with a web slot game URL
```

### Step 4: OpenCVVisualRuntime Implementation (Day 2 - 1 hr)
```python
# Delegate to ADB or Playwright for actual taps
# Use MODULE-07 TemplateMatcher for visual search
# Implement wait_for_template with polling loop
```

### Step 5: RuntimeManager (Day 2 - 1 hr)
```python
# Factory pattern for runtime instances
# Caching: one runtime instance per RuntimeType
# Auto-selection based on GameDefinition.runtime
# Lifecycle: connect_all / disconnect_all
```

### Step 6: Integration with MODULE-07 (Day 2 - 1 hr)
```python
# OpenCVVisualRuntime imports from MODULE-07
# Ensure MODULE-07 is importable even if not fully implemented
# Use Optional[TemplateMatcher] pattern for graceful degradation
```

---

## Testing Strategy

| Test | What | Method |
|---|---|---|
| `test_adb_connect` | ADB connects to device | Mock `adb devices` output |
| `test_adb_screenshot` | Screenshot captured as PNG bytes | Mock uiautomator2 screenshot |
| `test_playwright_navigate` | Page loads and screenshot captured | Mock Playwright Page |
| `test_runtime_manager_selects_correct` | Correct runtime selected per game type | Unit test |
| `test_visual_runtime_tap_on_template` | Template found and tapped | Mock TemplateMatcher |
| `test_runtime_fires_events` | Runtime actions emit events to EventBus | Mock EventBus |

---

## Success Criteria

1. ✅ `RuntimeManager.get_runtime(RuntimeType.ADB_UIAUTOMATOR2)` returns `ADBRuntime`
2. ✅ `RuntimeManager.get_runtime(RuntimeType.PLAYWRIGHT)` returns `PlaywrightRuntime`
3. ✅ `RuntimeManager.get_runtime(RuntimeType.OPENCV_VISUAL)` returns `OpenCVVisualRuntime`
4. ✅ All runtime actions fire `CrawlForgeEvent` to the event bus
5. ✅ ADBRuntime `take_screenshot()` returns PNG bytes < 500KB
6. ✅ PlaywrightRuntime `execute_js()` can inject and extract from page
7. ✅ OpenCVVisualRuntime `tap_on_template()` returns correct tap coordinates
8. ✅ Runtimes can be swapped at runtime without restart
9. ✅ Config can be loaded from YAML file
