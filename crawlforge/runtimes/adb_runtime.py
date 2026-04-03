"""
ADB Runtime - Android mobile game runtime.

Controls Android emulators or physical devices via ADB.
"""

import asyncio
import subprocess
import time
from pathlib import Path
from typing import Optional, Union

from ..core.models import Action, ActionResult, RuntimeType
from ..core.interfaces import Runtime


class ADBRuntime(Runtime):
    """
    Android runtime via ADB.

    Features:
    - Screenshot capture (screencap)
    - Tap, swipe, text input
    - APK installation
    - Package management
    - Device state queries

    Usage:
        runtime = ADBRuntime(device_id="emulator-5554")
        await runtime.start()
        screenshot = await runtime.screenshot()
        await runtime.execute(Action(action_type="tap", x=540, y=960))
        await runtime.stop()
    """

    def __init__(
        self,
        device_id: Optional[str] = None,
        adb_path: str = "adb",
        screenshot_format: str = "png",
        default_action_cooldown_ms: float = 100,
    ):
        """
        Args:
            device_id: ADB device serial (None = first device)
            adb_path: Path to adb binary
            screenshot_format: "png" or "jpg"
            default_action_cooldown_ms: Delay after each action
        """
        self.device_id = device_id
        self.adb_path = adb_path
        self.screenshot_format = screenshot_format
        self.default_action_cooldown_ms = default_action_cooldown_ms
        self._started = False
        self._last_action_time = 0.0

    async def start(self) -> None:
        """Start ADB server."""
        await self._run_cmd([self.adb_path, "start-server"])
        self._started = True

    async def stop(self) -> None:
        """Stop the runtime (no-op for ADB)."""
        self._started = False

    async def screenshot(self) -> bytes:
        """
        Capture screenshot from device.

        Returns PNG bytes.
        """
        cmd = self._build_cmd(["exec-out", "screencap", "-p"])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"screencap failed: {stderr.decode()}")

        if not stdout:
            raise RuntimeError("screencap returned empty data")

        return bytes(stdout)

    async def execute(self, action: Action) -> ActionResult:
        """
        Execute an action on the device.

        Args:
            action: Action to execute

        Returns:
            ActionResult with success status and optional screenshot
        """
        start = time.monotonic()

        try:
            # Enforce cooldown
            await self._cooldown()

            cmd = self._action_to_adb(action)
            if not cmd:
                return ActionResult(
                    success=False,
                    error=f"Unknown action type: {action.action_type}",
                    duration_ms=(time.monotonic() - start) * 1000,
                )

            proc = await asyncio.create_subprocess_exec(
                *self._build_cmd(cmd),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            duration_ms = (time.monotonic() - start) * 1000

            if proc.returncode != 0:
                return ActionResult(
                    success=False,
                    error=stderr.decode().strip() or f"ADB command failed (code {proc.returncode})",
                    duration_ms=duration_ms,
                )

            self._last_action_time = time.monotonic()

            return ActionResult(
                success=True,
                duration_ms=duration_ms,
            )

        except Exception as e:
            return ActionResult(
                success=False,
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    async def execute_with_screenshot(self, action: Action) -> ActionResult:
        """Execute action and return screenshot of result."""
        result = await self.execute(action)
        try:
            result.screenshot_after = await self.screenshot()
        except Exception:
            pass
        return result

    async def _cooldown(self) -> None:
        """Enforce minimum time between actions."""
        elapsed = time.monotonic() - self._last_action_time
        if elapsed < self.default_action_cooldown_ms / 1000:
            await asyncio.sleep(self.default_action_cooldown_ms / 1000 - elapsed)

    def is_alive(self) -> bool:
        """Check if device is connected and responsive."""
        try:
            result = subprocess.run(
                self._build_cmd(["get-state"]),
                capture_output=True,
                timeout=5,
            )
            return b"device" in result.stdout
        except Exception:
            return False

    def _build_cmd(self, args: list[str]) -> list[str]:
        """Build ADB command with device serial."""
        cmd = [self.adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return cmd

    @staticmethod
    def _action_to_adb(action: Action) -> list[str]:
        """Convert Action to ADB shell command."""
        at = action.action_type.lower()

        if at == "tap":
            if action.x is None or action.y is None:
                return []
            return ["shell", "input", "tap", str(action.x), str(action.y)]

        elif at in ("click", "long_press", "longpress"):
            x = action.x or action.x1
            y = action.y or action.y1
            if x is None or y is None:
                return []
            duration = max(500, action.duration_ms)
            return ["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration)]

        elif at == "swipe":
            if action.x1 is None or action.y1 is None or action.x2 is None or action.y2 is None:
                return []
            duration = max(100, action.duration_ms)
            return [
                "shell", "input", "swipe",
                str(action.x1), str(action.y1),
                str(action.x2), str(action.y2),
            ]

        elif at == "text":
            if action.text is None:
                return []
            text = action.text.replace(" ", "%s")
            return ["shell", "input", "text", text]

        elif at == "key" or at == "press":
            if action.key:
                return ["shell", "input", "keyevent", action.key]
            return []

        elif at == "wait":
            import math
            seconds = max(0, action.duration_ms / 1000)
            return ["shell", "sleep", f"{seconds:.1f}"]

        elif at == "drag":
            # ADB doesn't have native drag, simulate with swipe
            if action.x1 is not None and action.y1 is not None:
                return [
                    "shell", "input", "swipe",
                    str(action.x1), str(action.y1),
                    str(action.x2 or action.x1), str(action.y2 or action.y1),
                    "500",  # 500ms duration for drag feel
                ]

        return []

    # -------------------------------------------------------------------------
    # Device management
    # -------------------------------------------------------------------------

    async def install_apk(self, apk_path: Union[str, Path], grant_permissions: bool = True) -> bool:
        """Install or update an APK."""
        apk_path = Path(apk_path)
        if not apk_path.exists():
            raise FileNotFoundError(f"APK not found: {apk_path}")

        cmd = ["install"]
        if grant_permissions:
            cmd.append("-g")  # Grant all runtime permissions
        cmd.append("-r")  # Replace existing
        cmd.append(str(apk_path))

        proc = await asyncio.create_subprocess_exec(
            *self._build_cmd(cmd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = (stdout + stderr).decode()

        return "Success" in output

    async def uninstall_package(self, package_name: str) -> bool:
        """Uninstall an app."""
        proc = await asyncio.create_subprocess_exec(
            *self._build_cmd(["uninstall", package_name]),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return b"Success" in stdout

    async def list_packages(self) -> list[str]:
        """List installed packages."""
        cmd = self._build_cmd(["shell", "pm", "list", "packages"])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return [
            line.replace("package:", "").strip()
            for line in stdout.decode().splitlines()
            if line.startswith("package:")
        ]

    async def start_activity(self, package: str, activity: str, wait: bool = True) -> bool:
        """Start an Activity."""
        component = f"{package}/{activity}"
        cmd = self._build_cmd(["shell", "am", "start"])
        if wait:
            cmd.append("-W")
        cmd.extend(["-n", component])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        return b"Starting" in stderr or proc.returncode == 0

    async def dump_hierarchy(self) -> str:
        """Dump UI hierarchy (UI Automator XML)."""
        cmd = self._build_cmd(["shell", "uiautomator", "dump", "/sdcard/dump.xml"])
        await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.sleep(0.5)

        proc = await asyncio.create_subprocess_exec(
            *self._build_cmd(["shell", "cat", "/sdcard/dump.xml"]),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode("utf-8", errors="replace")

    async def get_screen_size(self) -> tuple[int, int]:
        """Get device screen resolution."""
        cmd = self._build_cmd(["shell", "wm", "size"])
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode().strip()

        # Parse "Physical size: 1080x1920"
        if "x" in output:
            size_part = output.split(":")[-1].strip()
            w, h = size_part.split("x")
            return int(w), int(h)

        return 1080, 1920  # Default

    @staticmethod
    async def _run_cmd(cmd: list[str]) -> bytes:
        """Run a command and return stdout."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout

    @property
    def runtime_type(self) -> RuntimeType:
        return RuntimeType.ADB
