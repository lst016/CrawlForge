"""
UI Element - represent UI hierarchy elements from uiautomator2.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UIElement:
    """A UI element from uiautomator2 hierarchy."""
    resource_id: str = ""
    text: str = ""
    content_desc: str = ""
    class_name: str = ""
    bounds: tuple[int, int, int, int] = (0, 0, 0, 0)  # (x1, y1, x2, y2)
    clickable: bool = False
    enabled: bool = True
    focused: bool = False
    checked: bool = False
    selected: bool = False
    depth: int = 0
    children: list["UIElement"] = field(default_factory=list)
    attributes: dict = field(default_factory=dict)

    @property
    def center(self) -> tuple[int, int]:
        """Get center coordinates."""
        x1, y1, x2, y2 = self.bounds
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    @property
    def bounds_dict(self) -> dict:
        """Get bounds as dict."""
        x1, y1, x2, y2 = self.bounds
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}

    def find_child(self, **kwargs) -> Optional["UIElement"]:
        """Find child matching attributes."""
        for child in self.children:
            if self._matches(child, kwargs):
                return child
            found = child.find_child(**kwargs)
            if found:
                return found
        return None

    def find_all(self, **kwargs) -> list["UIElement"]:
        """Find all children matching attributes."""
        results = []
        for child in self.children:
            if self._matches(child, kwargs):
                results.append(child)
            results.extend(child.find_all(**kwargs))
        return results

    @staticmethod
    def _matches(element: "UIElement", attrs: dict) -> bool:
        """Check if element matches attributes."""
        for key, value in attrs.items():
            if not hasattr(element, key):
                return False
            if getattr(element, key) != value:
                return False
        return True

    def to_dict(self) -> dict:
        """Convert to dict."""
        return {
            "resource_id": self.resource_id,
            "text": self.text,
            "content_desc": self.content_desc,
            "class_name": self.class_name,
            "bounds": self.bounds,
            "clickable": self.clickable,
            "enabled": self.enabled,
            "center": self.center,
            "children": [c.to_dict() for c in self.children],
        }
