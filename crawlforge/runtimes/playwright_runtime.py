"""
Playwright Runtime - 页游/H5 运行时

使用 Playwright 控制浏览器。
"""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from .runtime import Runtime
from .adapter import Action


class PlaywrightRuntime(Runtime):
    """Playwright 浏览器运行时"""

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
    ):
        self.headless = headless
        self.browser_type = browser_type
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def start(self) -> None:
        """启动浏览器"""
        self._playwright = await async_playwright().start()
        if self.browser_type == "chromium":
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
        elif self.browser_type == "firefox":
            self._browser = await self._playwright.firefox.launch(headless=self.headless)
        elif self.browser_type == "webkit":
            self._browser = await self._playwright.webkit.launch(headless=self.headless)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

    async def navigate(self, url: str) -> None:
        """导航到 URL"""
        if not self._page:
            raise RuntimeError("Browser not started")
        await self._page.goto(url)

    async def screenshot(self) -> bytes:
        """截图"""
        if not self._page:
            raise RuntimeError("Browser not started")
        return await self._page.screenshot()

    async def execute(self, action: Action) -> None:
        """执行操作"""
        if not self._page:
            raise RuntimeError("Browser not started")

        if action.action_type == "tap":
            await self._page.tap(f"x={action.x}, y={action.y}")
        elif action.action_type == "click":
            await self._page.click(f"x={action.x}, y={action.y}")
        elif action.action_type == "swipe":
            await self._page.evaluate(
                f"""
                () => {{
                    const el = document.elementFromPoint({action.x1}, {action.y1});
                    if (el) {{
                        const rect = el.getBoundingClientRect();
                        el.dispatchEvent(new MouseEvent('mousedown', {{
                            clientX: {action.x1}, clientY: {action.y1}, bubbles: true
                        }}));
                        el.dispatchEvent(new MouseEvent('mousemove', {{
                            clientX: {action.x2}, clientY: {action.y2}, bubbles: true
                        }}));
                        el.dispatchEvent(new MouseEvent('mouseup', {{
                            clientX: {action.x2}, clientY: {action.y2}, bubbles: true
                        }}));
                    }}
                }}
                """
            )
        elif action.action_type == "wait":
            await asyncio.sleep(action.duration_ms / 1000)

    async def stop(self) -> None:
        """停止浏览器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    def is_alive(self) -> bool:
        return self._browser is not None

    async def evaluate(self, script: str):
        """执行 JavaScript"""
        if not self._page:
            raise RuntimeError("Browser not started")
        return await self._page.evaluate(script)
