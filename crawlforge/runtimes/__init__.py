"""
Runtimes module - runtime implementations for different platforms.

Provides:
- ADBRuntime: Android device control via ADB
- PlaywrightRuntime: Browser automation via Playwright
"""

from .adb_runtime import ADBRuntime
from .playwright_runtime import PlaywrightRuntime

__all__ = [
    "ADBRuntime",
    "PlaywrightRuntime",
]
