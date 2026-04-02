"""
Tests for SlotGameDetector.
"""

import pytest
from crawlforge.uiauto.ui_element import UIElement
from crawlforge.detector.slot_detector import SlotGameDetector
from crawlforge.detector.phases import SlotPhase, SpinState, BalanceState


def make_hierarchy(elements):
    root = UIElement(
        resource_id="com.game:id/root",
        class_name="android.widget.FrameLayout",
        bounds=(0, 0, 1080, 2340),
    )
    for el_dict in elements:
        node = UIElement(
            resource_id=el_dict.get("resource_id", ""),
            text=el_dict.get("text", ""),
            content_desc=el_dict.get("content_desc", ""),
            class_name=el_dict.get("class", "android.widget.TextView"),
            bounds=el_dict.get("bounds", (0, 0, 100, 50)),
            clickable=el_dict.get("clickable", False),
            enabled=el_dict.get("enabled", True),
        )
        root.children.append(node)
    return root


class TestSlotGameDetector:

    def test_detector_init(self):
        detector = SlotGameDetector(None, "TestGame")
        assert detector.game_name == "TestGame"

    def test_extract_number_basic(self):
        assert SlotGameDetector._extract_number("5000") == 5000
        assert SlotGameDetector._extract_number("1,000,000") == 1000000
        assert SlotGameDetector._extract_number("Balance: 5000 coins") == 5000
        assert SlotGameDetector._extract_number("No numbers here") is None
        assert SlotGameDetector._extract_number("") is None
        assert SlotGameDetector._extract_number(None) is None

    def test_detect_game_ready(self):
        h = make_hierarchy([
            {"resource_id": "com.game:id/spin_btn", "text": "SPIN", "clickable": True},
            {"resource_id": "com.game:id/balance", "text": "Balance: 10000"},
            {"resource_id": "com.game:id/bet", "text": "Bet: 100"},
        ])
        detector = SlotGameDetector(None, "TestGame")
        result = detector.detect(h)
        assert result.phase == SlotPhase.GAME_READY
        assert result.ui.spin_button is not None
        assert result.balance == 10000

    def test_detect_spinning(self):
        h = make_hierarchy([
            {"resource_id": "com.game:id/status", "text": "Spinning..."},
        ])
        detector = SlotGameDetector(None, "TestGame")
        result = detector.detect(h)
        assert result.phase == SlotPhase.SPINNING

    def test_detect_win_display(self):
        h = make_hierarchy([
            {"resource_id": "com.game:id/win_amount", "text": "Win: 5000"},
            {"resource_id": "com.game:id/collect_btn", "text": "COLLECT", "clickable": True},
        ])
        detector = SlotGameDetector(None, "TestGame")
        result = detector.detect(h)
        assert result.phase == SlotPhase.WIN_DISPLAY
        assert result.win_amount == 5000

    def test_detect_loading(self):
        h = make_hierarchy([
            {"resource_id": "com.game:id/loading", "text": "Loading..."},
        ])
        detector = SlotGameDetector(None, "TestGame")
        result = detector.detect(h)
        assert result.phase == SlotPhase.LOADING

    def test_detect_balance_low(self):
        h = make_hierarchy([
            {"resource_id": "com.game:id/spin_btn", "text": "SPIN", "clickable": True},
            {"resource_id": "com.game:id/balance", "text": "Balance: 50"},
        ])
        detector = SlotGameDetector(None, "TestGame")
        result = detector.detect(h)
        assert result.balance == 50
        assert result.balance_state == BalanceState.LOW

    def test_detect_balance_empty(self):
        h = make_hierarchy([
            {"resource_id": "com.game:id/spin_btn", "text": "SPIN", "clickable": True},
            {"resource_id": "com.game:id/balance", "text": "Balance: 0"},
        ])
        detector = SlotGameDetector(None, "TestGame")
        result = detector.detect(h)
        assert result.balance == 0
        assert result.balance_state == BalanceState.EMPTY

    def test_detect_unknown(self):
        h = make_hierarchy([])
        detector = SlotGameDetector(None, "TestGame")
        result = detector.detect(h)
        assert result.phase == SlotPhase.UNKNOWN
        assert result.confidence < 0.5
