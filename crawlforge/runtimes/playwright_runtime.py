"""
Playwright Runtime - browser-based game runtime (H5 / web games).

Controls browsers via Playwright for web and H5 games.
"""

import asyncio
from pathlib import Path
from typing import Optional, Union

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from ..core.models import Action, ActionResult, RuntimeType
from ..core.interfaces import Runtime


class PlaywrightRuntime(Runtime):
    """
    Browser runtime via Playwright.

    Features:
    - Chromium, Firefox, WebKit support
    - Persistent context (cookies/login state)
    - Screenshot capture
    - Element interaction (tap, click, swipe, type)
    - JavaScript evaluation
    - Navigation

    Usage:
        runtime = PlaywrightRuntime(headless=True)
        await runtime.start()
        await runtime.navigate("https://example.com/game")
        screenshot = await runtime.screenshot()
        await runtime.execute(Action(action_type="tap", x=540, y=960))
        await runtime.stop()
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        user_data_dir: Optional[str] = None,
        viewport_size: tuple[int, int] = (1920, 1080),
        user_agent: Optional[str] = None,
        ignore_https_errors: bool = True,
        default_timeout_ms: float = 30000,
    ):
        """
        Args:
            headless: Run browser without UI
            browser_type: "chromium", "firefox", or "webkit"
            user_data_dir: Path for persistent browser profile
            viewport_size: Browser viewport dimensions
            user_agent: Custom user agent string
            ignore_https_errors: Ignore SSL certificate errors
            default_timeout_ms: Default timeout for all operations
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Run: pip install playwright && playwright install"
            )

        self.headless = headless
        self.browser_type = browser_type
        self.user_data_dir = user_data_dir
        self.viewport_size = viewport_size
        self.user_agent = user_agent
        self.ignore_https_errors = ignore_https_errors
        self.default_timeout_ms = default_timeout_ms

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._started = False

    async def start(self) -> None:
        """Start the browser and create a page."""
        if self._started:
            return

        self._playwright = await async_playwright().start()

        # Select browser
        if self.browser_type == "chromium":
            browser_cls = self._playwright.chromium
        elif self.browser_type == "firefox":
            browser_cls = self._playwright.firefox
        elif self.browser_type == "webkit":
            browser_cls = self._playwright.webkit
        else:
            raise ValueError(f"Unknown browser type: {self.browser_type}")

        # Launch options
        launch_options = {"headless": self.headless}

        if self.user_data_dir:
            # Use persistent context
            self._context = await browser_cls.launch_persistent_context(
                self.user_data_dir,
                **launch_options,
                viewport={"width": self.viewport_size[0], "height": self.viewport_size[1]},
                user_agent=self.user_agent,
                ignore_https_errors=self.ignore_https_errors,
            )
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        else:
            # Ephemeral context
            self._browser = await browser_cls.launch(**launch_options)
            self._context = await self._browser.new_context(
                viewport={"width": self.viewport_size[0], "height": self.viewport_size[1]},
                user_agent=self.user_agent,
                ignore_https_errors=self.ignore_https_errors,
            )
            self._page = await self._context.new_page()

        await self._page.set_default_timeout(self.default_timeout_ms)
        self._started = True

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """
        Navigate to a URL.

        Args:
            url: Target URL
            wait_until: "load", "domcontentloaded", "networkidle"
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        await self._page.goto(url, wait_until=wait_until)

    async def screenshot(self, full_page: bool = False) -> bytes:
        """
        Capture a screenshot.

        Args:
            full_page: If True, capture the entire scrollable page

        Returns:
            PNG image bytes
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")

        return bytes(await self._page.screenshot(full_page=full_page))

    async def execute(self, action: Action) -> ActionResult:
        """
        Execute an action in the browser.

        Args:
            action: Action to execute

        Returns:
            ActionResult
        """
        import time
        start = time.monotonic()

        if not self._page:
            return ActionResult(success=False, error="Browser not started")

        try:
            at = action.action_type.lower()

            if at in ("tap", "click"):
                x = action.x or action.x1
                y = action.y or action.y1
                if x is None or y is None:
                    return ActionResult(success=False, error="Missing coordinates for tap/click")
                await self._page.tap(f"x={x}, y={y}")

            elif at in ("swipe", "drag", "scroll"):
                x1 = action.x1 or action.x
                y1 = action.y1 or action.y
                x2 = action.x2 or action.x1
                y2 = action.y2 or action.y1
                if x1 is None or y1 is None or x2 is None or y2 is None:
                    return ActionResult(success=False, error="Missing swipe coordinates")

                await self._page.evaluate(
                    f"""
                    () => {{
                        const el = document.elementFromPoint({x1}, {y1});
                        if (el) {{
                            const startX = {x1}, startY = {y1};
                            const endX = {x2}, endY = {y2};
                            const duration = {action.duration_ms or 300};

                            const startEvent = new MouseEvent('mousedown', {{
                                clientX: startX, clientY: startY, bubbles: true
                            }});
                            const moveEvent = new MouseEvent('mousemove', {{
                                clientX: endX, clientY: endY, bubbles: true
                            }});
                            const endEvent = new MouseEvent('mouseup', {{
                                clientX: endX, clientY: endY, bubbles: true
                            }});

                            el.dispatchEvent(startEvent);
                            setTimeout(() => el.dispatchEvent(moveEvent), duration / 2);
                            setTimeout(() => el.dispatchEvent(endEvent), duration);
                        }}
                    }}
                    """
                )

            elif at == "type" or at == "text":
                if action.text:
                    await self._page.keyboard.type(action.text)
                else:
                    return ActionResult(success=False, error="No text provided for type action")

            elif at == "press" or at == "key":
                if action.key:
                    await self._page.keyboard.press(action.key)
                else:
                    return ActionResult(success=False, error="No key provided for press action")

            elif at == "wait":
                await asyncio.sleep(max(0, action.duration_ms / 1000))

            elif at == "evaluate" or at == "js":
                if action.text:
                    await self._page.evaluate(action.text)
                else:
                    return ActionResult(success=False, error="No JavaScript provided")

            else:
                return ActionResult(success=False, error=f"Unknown action type: {action.action_type}")

            return ActionResult(
                success=True,
                duration_ms=(time.monotonic() - start) * 1000,
            )

        except Exception as e:
            return ActionResult(
                success=False,
                error=f"{type(e).__name__}: {e}",
                duration_ms=(time.monotonic() - start) * 1000,
            )

    async def evaluate(self, script: str) -> any:
        """Execute JavaScript and return result."""
        if not self._page:
            raise RuntimeError("Browser not started")
        return await self._page.evaluate(script)

    async def wait_for_selector(self, selector: str, timeout_ms: float = 30000) -> bool:
        """Wait for a CSS selector to appear."""
        if not self._page:
            raise RuntimeError("Browser not started")
        try:
            await self._page.wait_for_selector(selector, timeout=timeout_ms)
            return True
        except Exception:
            return False

    async def get_title(self) -> str:
        """Get page title."""
        if not self._page:
            return ""
        return await self._page.title()

    async def get_url(self) -> str:
        """Get current page URL."""
        if not self._page:
            return ""
        return self._page.url

    async def stop(self) -> None:
        """Stop the browser."""
        if self._page:
            await self._page.close()
            self._page = None
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._started = False

    def is_alive(self) -> bool:
        """Check if browser is running."""
        return self._started and self._page is not None

    @property
    def runtime_type(self) -> RuntimeType:
        return RuntimeType.PLAYWRIGHT

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()
