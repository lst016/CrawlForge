"""
UIAutoRuntime - uiautomator2-based runtime for Android automation.

Provides screenshot, tap, swipe, and template matching capabilities
via ADB and uiautomator2.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from ..core.interfaces import Runtime
from ..core.exceptions import RuntimeError


class UIAutoRuntime(Runtime):
    """
    UIAutoRuntime using uiautomator2 for Android UI automation.

    Requires:
    - ADB installed and in PATH
    - uiautomator2 Python package (uiautomator2)
    - Device with uiautomator2 server running
    """

    def __init__(self, device_id: Optional[str] = None):
        """
        Args:
            device_id: ADB device serial. None for first available device.
        """
        self.device_id = device_id
        self._adb_path = "adb"
        self._u2_device = None

    async def _ensure_u2(self) -> None:
        """Lazily initialize uiautomator2 connection."""
        if self._u2_device is None:
            try:
                import uiautomator2
                if self.device_id:
                    self._u2_device = uiautomator2.connect(self.device_id)
                else:
                    self._u2_device = uiautomator2.connect()
            except Exception as e:
                raise RuntimeError(f"Failed to connect uiautomator2: {e}")

    def _build_adb_cmd(self, args: list) -> list:
        """Build ADB command with device selection."""
        cmd = [self._adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return cmd

    async def screenshot(self) -> bytes:
        """
        Capture screenshot from device.

        Returns:
            PNG image bytes.
        """
        try:
            cmd = self._build_adb_cmd(
                ["exec-out", "screencap", "-p"]
            )
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if not stdout:
                raise RuntimeError("Empty screenshot from device")
            return stdout
        except asyncio.TimeoutError:
            raise RuntimeError("Screenshot timed out")
        except Exception as e:
            raise RuntimeError(f"Screenshot failed: {e}")

    async def tap(self, x: int, y: int) -> None:
        """Tap at coordinates (x, y)."""
        await self._ensure_u2()
        try:
            self._u2_device.click(x, y)
        except Exception as e:
            raise RuntimeError(f"Tap failed: {e}")

    async def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300
    ) -> None:
        """Swipe from (x1, y1) to (x2, y2)."""
        await self._ensure_u2()
        try:
            duration_sec = duration_ms / 1000.0
            self._u2_device.swipe(x1, y1, x2, y2, duration_sec)
        except Exception as e:
            raise RuntimeError(f"Swipe failed: {e}")

    async def press_back(self) -> None:
        """Press back button."""
        try:
            cmd = self._build_adb_cmd(["shell", "input", "keyevent", "KEYCODE_BACK"])
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception as e:
            raise RuntimeError(f"Press back failed: {e}")

    def is_alive(self) -> bool:
        """Check if device is connected and responsive."""
        try:
            result = subprocess.run(
                self._build_adb_cmd(["get-state"]),
                capture_output=True,
                timeout=5,
            )
            return b"device" in result.stdout
        except Exception:
            return False

    def template_match(
        self, template_path: str, threshold: float = 0.8
    ) -> Optional[tuple]:
        """
        Find template in last screenshot using cv2.matchTemplate.

        Args:
            template_path: Path to template image file.
            threshold: Match confidence threshold (0.0-1.0).

        Returns:
            (x, y, w, h) of best match, or None if not found.
        """
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV not available for template matching")

        try:
            import uiautomator2
            screen_bytes = asyncio.get_event_loop().run_until_complete(
                self.screenshot()
            )
            screenshot = cv2.imdecode(
                np.frombuffer(screen_bytes, np.uint8), cv2.IMREAD_COLOR
            )
            template = cv2.imread(template_path, cv2.IMREAD_COLOR)

            if screenshot is None or template is None:
                raise RuntimeError("Failed to load image")

            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= threshold:
                h, w = template.shape[:2]
                return (max_loc[0], max_loc[1], w, h)
            return None
        except Exception as e:
            raise RuntimeError(f"Template match failed: {e}")
