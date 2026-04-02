"""
Slot Game Detector - detects slot game states from UI hierarchy.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List

from ..uiauto.ui_element import UIElement
from ..uiauto.runtime import UIAutoRuntime
from .phases import SlotPhase, SpinState, BalanceState


@dataclass
class SlotUI:
    """Identified slot game UI elements."""
    spin_button: Optional[UIElement] = None
    balance_display: Optional[UIElement] = None
    bet_display: Optional[UIElement] = None
    lines_display: Optional[UIElement] = None
    auto_spin_button: Optional[UIElement] = None
    max_bet_button: Optional[UIElement] = None
    collect_button: Optional[UIElement] = None
    close_button: Optional[UIElement] = None
    reel_area: Optional[UIElement] = None
    win_amount_display: Optional[UIElement] = None
    free_spin_counter: Optional[UIElement] = None
    bonus_indicator: Optional[UIElement] = None
    loading_indicator: Optional[UIElement] = None


@dataclass
class SlotDetectionResult:
    """Result of slot game detection."""
    phase: Optional[SlotPhase]
    spin_state: SpinState = SpinState.IDLE
    balance_state: BalanceState = BalanceState.NORMAL
    balance: Optional[int] = None
    bet: Optional[int] = None
    lines: Optional[int] = None
    win_amount: Optional[int] = None
    free_spins_remaining: int = 0
    ui: SlotUI = field(default_factory=SlotUI)
    confidence: float = 0.0
    hints: List[str] = field(default_factory=list)


class SlotGameDetector:
    """
    Detects slot game state from Android UI hierarchy.

    Uses resource IDs, text patterns, and UI structure to identify
    game phases and extract balance/bet information.
    """

    SPIN_BUTTON_IDS = [
        "spin", "btn_spin", "bt_spin", "spin_btn",
        "start_btn", "play_btn", "btn_play", "go_btn",
        "gamble_btn", "gamble", "bet_btn", "btn_bet",
    ]
    BALANCE_IDS = [
        "balance", "credit", "coins", "money", "gold",
        "cash", "wallet", "amount", "total",
    ]
    BET_IDS = ["bet", "stake", "wager", "bet_amount", "bet_display"]
    LINES_IDS = ["lines", "paylines", "line", "active_lines", "line_count"]
    WIN_IDS = ["win", "win_amount", "win_txt", "prize", "reward", "win_display"]
    AUTO_SPIN_IDS = ["auto", "auto_spin", "autoplay", "auto_play"]
    COLLECT_IDS = ["collect", "claim", "take", "ok", "confirm"]
    FREE_SPIN_IDS = ["free_spin", "freespin", "free", "bonus_spin", "freegame"]
    LOADING_IDS = ["loading", "load", "wait", "please_wait", "connecting"]

    TITLE_KEYWORDS = ["slot", "slots", "casino", "vegas", "jackpot", "777", "lucky", "fortune"]

    def __init__(self, runtime: Optional[UIAutoRuntime], game_name: str = "generic"):
        self.runtime = runtime
        self.game_name = game_name
        self._last_ui: Optional[UIElement] = None

    def detect(self, hierarchy: Optional[UIElement] = None) -> SlotDetectionResult:
        """Detect current slot game state."""
        if hierarchy is None and self.runtime:
            try:
                hierarchy = self.runtime.dump_hierarchy()
                self._last_ui = hierarchy
            except Exception:
                pass

        if hierarchy is None:
            return SlotDetectionResult(phase=None, confidence=0.0, hints=["no_hierarchy"])

        phase = self._detect_phase(hierarchy)
        spin_state = self._detect_spin_state(hierarchy, phase)
        balance_state, balance = self._detect_balance(hierarchy)
        bet, lines = self._detect_bet_lines(hierarchy)
        win_amount = self._detect_win_amount(hierarchy)
        free_spins = self._detect_free_spins(hierarchy)
        ui = self._extract_ui_elements(hierarchy)
        hints = self._generate_hints(hierarchy, phase)
        confidence = self._calculate_confidence(phase, ui, hints)

        return SlotDetectionResult(
            phase=phase,
            spin_state=spin_state,
            balance_state=balance_state,
            balance=balance,
            bet=bet,
            lines=lines,
            win_amount=win_amount,
            free_spins_remaining=free_spins,
            ui=ui,
            confidence=confidence,
            hints=hints,
        )

    def _detect_phase(self, root: UIElement) -> Optional[SlotPhase]:
        if self._has_loading_indicator(root):
            return SlotPhase.LOADING
        if self._has_error_state(root):
            return SlotPhase.CONNECTION_ERROR
        if self._is_settings_screen(root):
            return SlotPhase.SETTINGS
        if self._is_bonus_game(root):
            return SlotPhase.BONUS_GAME
        if self._has_free_spin_indicator(root):
            return SlotPhase.FREE_SPINS
        if self._is_win_display(root):
            return SlotPhase.WIN_DISPLAY
        if self._is_spinning(root):
            return SlotPhase.SPINNING
        if self._has_spin_button(root):
            return SlotPhase.GAME_READY
        if self._has_collect_button(root):
            return SlotPhase.WIN_DISPLAY
        if self._is_lobby(root):
            return SlotPhase.MAIN_LOBBY
        if self._is_title_screen(root):
            return SlotPhase.TITLE_SCREEN
        return SlotPhase.UNKNOWN

    def _detect_spin_state(self, root: UIElement, phase: Optional[SlotPhase]) -> SpinState:
        if phase != SlotPhase.SPINNING:
            return SpinState.IDLE
        if self._has_spinning_stop_indicator(root):
            return SpinState.STOPPING
        return SpinState.SPINNING

    def _detect_balance(self, root: UIElement) -> tuple:
        balance_el = self._find_element_by_ids(root, self.BALANCE_IDS)
        if balance_el is None:
            return BalanceState.NORMAL, None
        balance = self._extract_number(balance_el.text)
        if balance is None:
            return BalanceState.NORMAL, None
        if balance <= 0:
            return BalanceState.EMPTY, 0
        if balance < 100:
            return BalanceState.LOW, balance
        return BalanceState.NORMAL, balance

    def _detect_bet_lines(self, root: UIElement) -> tuple:
        bet_el = self._find_element_by_ids(root, self.BET_IDS)
        lines_el = self._find_element_by_ids(root, self.LINES_IDS)
        bet = self._extract_number(bet_el.text) if bet_el else None
        lines = self._extract_number(lines_el.text) if lines_el else None
        return bet, lines

    def _detect_win_amount(self, root: UIElement) -> Optional[int]:
        win_el = self._find_element_by_ids(root, self.WIN_IDS)
        if win_el is None:
            return None
        return self._extract_number(win_el.text)

    def _detect_free_spins(self, root: UIElement) -> int:
        free_el = self._find_element_by_ids(root, self.FREE_SPIN_IDS)
        if free_el is None:
            return 0
        count = self._extract_number(free_el.text)
        return max(0, count or 0)

    def _extract_ui_elements(self, root: UIElement) -> SlotUI:
        return SlotUI(
            spin_button=self._find_element_by_ids(root, self.SPIN_BUTTON_IDS),
            balance_display=self._find_element_by_ids(root, self.BALANCE_IDS),
            bet_display=self._find_element_by_ids(root, self.BET_IDS),
            lines_display=self._find_element_by_ids(root, self.LINES_IDS),
            auto_spin_button=self._find_element_by_ids(root, self.AUTO_SPIN_IDS),
            max_bet_button=self._find_max_bet_button(root),
            collect_button=self._find_element_by_ids(root, self.COLLECT_IDS),
            close_button=self._find_close_button(root),
            win_amount_display=self._find_element_by_ids(root, self.WIN_IDS),
            free_spin_counter=self._find_element_by_ids(root, self.FREE_SPIN_IDS),
            loading_indicator=self._find_loading_indicator(root),
        )

    def _find_element_by_ids(self, root: UIElement, ids: list) -> Optional[UIElement]:
        for el in root.find_all() if hasattr(root, 'find_all') else []:
            for pid in ids:
                if pid.lower() in (el.resource_id or "").lower():
                    return el
        return None

    def _find_max_bet_button(self, root: UIElement) -> Optional[UIElement]:
        for el in root.find_all() if hasattr(root, 'find_all') else []:
            text_lower = (el.text or "").lower()
            resource_lower = (el.resource_id or "").lower()
            if "max" in text_lower and "bet" in text_lower:
                return el
            if "max" in text_lower and "bet" in resource_lower:
                return el
            if "maxbet" in resource_lower:
                return el
        return None

    def _find_close_button(self, root: UIElement) -> Optional[UIElement]:
        for el in root.find_all() if hasattr(root, 'find_all') else []:
            text_lower = (el.text or "").lower()
            desc_lower = (el.content_desc or "").lower()
            if text_lower in ("x", "close", "back", "✕", "×") or desc_lower in ("close", "back", "x"):
                if el.clickable:
                    return el
        return None

    def _find_loading_indicator(self, root: UIElement) -> Optional[UIElement]:
        return self._find_element_by_ids(root, self.LOADING_IDS)

    def _has_spin_button(self, root: UIElement) -> bool:
        return self._find_element_by_ids(root, self.SPIN_BUTTON_IDS) is not None

    def _has_collect_button(self, root: UIElement) -> bool:
        return self._find_element_by_ids(root, self.COLLECT_IDS) is not None

    def _has_loading_indicator(self, root: UIElement) -> bool:
        return self._find_loading_indicator(root) is not None

    def _has_free_spin_indicator(self, root: UIElement) -> bool:
        el = self._find_element_by_ids(root, self.FREE_SPIN_IDS)
        if el is None:
            return False
        text = (el.text or "").lower()
        desc = (el.content_desc or "").lower()
        return "free" in text or "free" in desc or any(c.isdigit() for c in text)

    def _has_error_state(self, root: UIElement) -> bool:
        for el in root.find_all() if hasattr(root, 'find_all') else []:
            text_lower = (el.text or "").lower()
            desc_lower = (el.content_desc or "").lower()
            if "error" in text_lower or "error" in desc_lower:
                return True
            if "disconnect" in text_lower or "connection" in text_lower:
                return True
        return False

    def _is_settings_screen(self, root: UIElement) -> bool:
        for el in root.find_all() if hasattr(root, 'find_all') else []:
            text_lower = (el.text or "").lower()
            desc_lower = (el.content_desc or "").lower()
            if text_lower == "settings" or desc_lower == "settings":
                return True
        return False

    def _is_bonus_game(self, root: UIElement) -> bool:
        for el in root.find_all() if hasattr(root, 'find_all') else []:
            text_lower = (el.text or "").lower()
            desc_lower = (el.content_desc or "").lower()
            if "bonus" in text_lower and ("game" in text_lower or "pick" in text_lower):
                return True
            if "bonus" in desc_lower:
                return True
        return False

    def _is_win_display(self, root: UIElement) -> bool:
        win_el = self._find_element_by_ids(root, self.WIN_IDS)
        if win_el is None:
            return False
        win_amount = self._extract_number(win_el.text)
        return win_amount is not None and win_amount > 0

    def _is_spinning(self, root: UIElement) -> bool:
        for el in root.find_all() if hasattr(root, 'find_all') else []:
            text_lower = (el.text or "").lower()
            desc_lower = (el.content_desc or "").lower()
            if "spin" in text_lower and "ing" in text_lower:
                return True
            if "spinning" in text_lower or "spinning" in desc_lower:
                return True
        return False

    def _has_spinning_stop_indicator(self, root: UIElement) -> bool:
        for el in root.find_all() if hasattr(root, 'find_all') else []:
            if "stop" in (el.text or "").lower():
                return True
        return False

    def _is_lobby(self, root: UIElement) -> bool:
        return (self._find_element_by_ids(root, self.BET_IDS) is not None and
                self._find_element_by_ids(root, self.LINES_IDS) is not None)

    def _is_title_screen(self, root: UIElement) -> bool:
        for el in root.find_all() if hasattr(root, 'find_all') else []:
            text_lower = (el.text or "").lower()
            desc_lower = (el.content_desc or "").lower()
            for keyword in self.TITLE_KEYWORDS:
                if keyword in text_lower or keyword in desc_lower:
                    if self._has_spin_button(root):
                        return True
        return False

    @staticmethod
    def _extract_number(text: Optional[str]) -> Optional[int]:
        if not text:
            return None
        match = re.search(r"[\d,]+", text.replace(",", ""))
        if match:
            try:
                return int(match.group().replace(",", ""))
            except ValueError:
                return None
        return None

    def _generate_hints(self, root: UIElement, phase: Optional[SlotPhase]) -> list:
        hints = [f"phase={phase.value if phase else 'none'}"]
        if not self._has_spin_button(root):
            hints.append("no_spin_button")
        if not self._find_element_by_ids(root, self.BALANCE_IDS):
            hints.append("no_balance_display")
        return hints

    def _calculate_confidence(self, phase: Optional[SlotPhase], ui: SlotUI, hints: list) -> float:
        if phase is None or phase == SlotPhase.UNKNOWN:
            return 0.3
        confidence = 0.5
        if ui.spin_button:
            confidence += 0.15
        if ui.balance_display:
            confidence += 0.1
        if ui.bet_display:
            confidence += 0.1
        if phase != SlotPhase.UNKNOWN:
            confidence += 0.15
        if "no_spin_button" in hints:
            confidence -= 0.1
        return min(1.0, max(0.0, confidence))
