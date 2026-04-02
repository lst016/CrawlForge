"""
uIAuto module - Android UI automation via ADB + uiautomator2.
"""

from .runtime import UIAutoRuntime, UIElementEncoder
from .ui_element import UIElement

__all__ = ["UIAutoRuntime", "UIElement", "UIElementEncoder"]
