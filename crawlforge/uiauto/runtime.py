"""
uIAuto Runtime - Android UI automation via ADB + uiautomator2.

Provides UI hierarchy access, element finding, and action execution.
"""

import asyncio
import subprocess
import xml.etree.ElementTree as ET
from typing import Optional, Union
from pathlib import Path

from ..core.interfaces import Runtime
from ..core.models import Action, ActionResult
from .ui_element import UIElement


class UIElementEncoder:
    """Encodes/decodes UI hierarchy to/from XML."""

    @staticmethod
    def parse_hierarchy(xml_str: str) -> UIElement:
        """Parse uiautomator2 XML hierarchy into UIElement tree."""
        root = ET.fromstring(xml_str)
        return UIElementEncoder._parse_node(root)

    @staticmethod
    def _parse_node(node: ET.Element, depth: int = 0) -> UIElement:
        """Recursively parse XML node to UIElement."""
        bounds_str = node.attrib.get("bounds", "(0,0)(0,0)")
        bounds = UIElementEncoder._parse_bounds(bounds_str)

        attributes = {}
        for key, value in node.attrib.items():
            if key not in ("bounds", "index"):
                try:
                    attributes[key] = UIElementEncoder._str_to_basic(value)
                except Exception:
                    attributes[key] = value

        element = UIElement(
            resource_id=node.attrib.get("resource-id", ""),
            text=node.attrib.get("text", ""),
            content_desc=node.attrib.get("content-desc", ""),
            class_name=node.attrib.get("class", ""),
            bounds=bounds,
            clickable=node.attrib.get("clickable", "false") == "true",
            enabled=node.attrib.get("enabled", "true") == "true",
            focused=node.attrib.get("focused", "false") == "true",
            checked=node.attrib.get("checked", "false") == "true",
            selected=node.attrib.get("selected", "false") == "true",
            depth=depth,
            attributes=attributes,
        )

        for child in node:
            child_el = UIElementEncoder._parse_node(child, depth + 1)
            element.children.append(child_el)

        return element

    @staticmethod
    def _parse_bounds(s: str) -> tuple[int, int, int, int]:
        """Parse bounds string like '[0,0][1080,2340]' to (x1,y1,x2,y2)."""
        import re
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", s)
        if match:
            return (int(match.group(1)), int(match.group(2)),
                    int(match.group(3)), int(match.group(4)))
        return (0, 0, 0, 0)

    @staticmethod
    def _str_to_basic(s: str) -> Union[bool, int, float, str]:
        """Convert string attribute to basic Python type."""
        if s == "true":
            return True
        if s == "false":
            return False
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return s


class UIAutoRuntime(Runtime):
    """
    Android UI automation runtime using ADB + uiautomator2.

    Features:
    - UI hierarchy extraction via uiautomator2 dump
    - Element finding by resource-id, text, content-desc, class
    - Tap, swipe, text input, key events
    - Template screenshot matching via OpenCV
    """

    def __init__(self, device_id: Optional[str] = None, serial: Optional[str] = None):
        """
        Args:
            device_id: ADB device serial. Uses first device if None.
            serial: Alias for device_id.
        """
        self.device_id = serial or device_id
        self._adb_path = "adb"
        self._current_hierarchy: Optional[UIElement] = None
        self._screen_cache: Optional[bytes] = None

    async def start(self) -> None:
        """Start the runtime (verify device connection)."""
        result = await self._run_adb(["get-state"])
        if b"device" not in result:
            raise RuntimeError("No Android device connected")

    async def stop(self) -> None:
        """Stop the runtime."""
        self._current_hierarchy = None
        self._screen_cache = None

    async def screenshot(self) -> bytes:
        """Capture screenshot."""
        result = await self._run_adb(["exec-out", "screencap", "-p"])
        self._screen_cache = result
        return result

    async def execute(self, action: Action) -> ActionResult:
        """Execute an action."""
        import time
        start = time.monotonic()

        try:
            if action.action_type == "tap":
                await self._run_adb(["shell", "input", "tap", str(action.x), str(action.y)])
            elif action.action_type == "swipe":
                await self._run_adb([
                    "shell", "input", "swipe",
                    str(action.x1), str(action.y1),
                    str(action.x2), str(action.y2),
                    str(action.duration_ms)
                ])
            elif action.action_type == "text":
                text = (action.text or "").replace(" ", "%s")
                await self._run_adb(["shell", "input", "text", text])
            elif action.action_type == "key":
                await self._run_adb(["shell", "input", "keyevent", action.key or "BACK"])
            elif action.action_type == "wait":
                await asyncio.sleep(action.duration_ms / 1000)
            else:
                return ActionResult(success=False, error=f"Unknown action type: {action.action_type}")

            await asyncio.sleep(0.05)
            screenshot_after = await self.screenshot()
            duration = (time.monotonic() - start) * 1000
            return ActionResult(success=True, screenshot_after=screenshot_after, duration_ms=duration)

        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def is_alive(self) -> bool:
        """Check if device is connected."""
        try:
            result = subprocess.run(
                self._build_cmd(["get-state"]),
                capture_output=True, timeout=5
            )
            return b"device" in result.stdout
        except Exception:
            return False

    async def dump_hierarchy(self, compressed: bool = False) -> UIElement:
        """
        Dump the current UI hierarchy via uiautomator2.

        Args:
            compressed: If True, use compressed hierarchy format.

        Returns:
            Root UIElement of the hierarchy tree.
        """
        if compressed:
            xml_str = await self._run_adb([
                "shell", "uiautomator2", "dump", "/sdcard/dump.xml", "&&",
                "cat", "/sdcard/dump.xml"
            ])
        else:
            result = await self._run_adb(["shell", "uiautomator2", "dump", "/dev/tty"])
            xml_str = result

        self._current_hierarchy = UIElementEncoder.parse_hierarchy(xml_str)
        return self._current_hierarchy

    async def find_element(
        self,
        resource_id: Optional[str] = None,
        text: Optional[str] = None,
        content_desc: Optional[str] = None,
        class_name: Optional[str] = None,
        clickable: Optional[bool] = None,
    ) -> Optional[UIElement]:
        """
        Find UI element by attributes.

        Args:
            resource_id: Element resource ID
            text: Element text
            content_desc: Content description
            class_name: Element class name
            clickable: Element is clickable

        Returns:
            First matching UIElement or None.
        """
        hierarchy = await self.dump_hierarchy()

        return hierarchy.find_child(
            resource_id=resource_id or "",
            text=text or "",
            content_desc=content_desc or "",
            class_name=class_name or "",
            clickable=clickable if clickable is not None else False,
        )

    async def find_all_elements(
        self,
        resource_id: Optional[str] = None,
        text: Optional[str] = None,
        class_name: Optional[str] = None,
        clickable: Optional[bool] = None,
    ) -> list[UIElement]:
        """Find all UI elements matching attributes."""
        hierarchy = await self.dump_hierarchy()

        kwargs = {}
        if resource_id is not None:
            kwargs["resource_id"] = resource_id
        if text is not None:
            kwargs["text"] = text
        if class_name is not None:
            kwargs["class_name"] = class_name
        if clickable is not None:
            kwargs["clickable"] = clickable

        return hierarchy.find_all(**kwargs)

    async def tap_element(self, element: UIElement) -> ActionResult:
        """Tap a UI element by its center coordinates."""
        cx, cy = element.center
        return await self.execute(Action(action_type="tap", x=cx, y=cy))

    async def install_uiautomator2(self) -> bool:
        """Install/upgrade uiautomator2 on device."""
        try:
            await self._run_adb([
                "shell", "pip", "install", "uiautomator2", "uiautomator2-extlevels"
            ])
            return True
        except Exception:
            return False

    async def press_back(self) -> ActionResult:
        """Press back button."""
        return await self.execute(Action(action_type="key", key="BACK"))

    async def press_home(self) -> ActionResult:
        """Press home button."""
        return await self.execute(Action(action_type="key", key="HOME"))

    def _build_cmd(self, args: list[str]) -> list[str]:
        """Build ADB command."""
        cmd = [self._adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return cmd

    async def _run_adb(self, args: list[str]) -> bytes:
        """Run ADB command and return stdout."""
        cmd = self._build_cmd(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0 and stderr:
            raise RuntimeError(f"ADB error: {stderr.decode(errors='replace')}")
        return stdout
