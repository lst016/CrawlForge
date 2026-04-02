"""
SlotGameDetector - Game state detection for slot games.

Uses template matching and image processing to detect:
- Game phase (idle, spinning, bonus, etc.)
- Balance display
- Spin button location
- Bonus round detection
"""

from typing import Optional

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from ..core.dataclasses import GamePhase
from ..core.interfaces import GameDetector
from ..core.exceptions import DetectionError
from ..uiauto.template_store import TemplateStore


class SlotGameDetector(GameDetector):
    """
    Detector for slot game UI elements and states.

    Uses template matching and image analysis to identify
    game phases and UI elements.
    """

    def __init__(self, template_store: Optional[TemplateStore] = None):
        """
        Args:
            template_store: Template store for slot game templates.
        """
        self.template_store = template_store or TemplateStore()
        self._templates = {}

    def _load_template(self, name: str):
        """Load template image from store."""
        if name not in self._templates:
            meta = self.template_store.get(name)
            if not meta or not CV2_AVAILABLE:
                return None
            path = meta.get("path")
            if path:
                self._templates[name] = cv2.imread(path)
            else:
                return None
        return self._templates.get(name)

    def _screenshot_to_image(self, screenshot: bytes):
        """Convert screenshot bytes to OpenCV image."""
        if not CV2_AVAILABLE:
            raise DetectionError("OpenCV not available")
        arr = np.frombuffer(screenshot, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise DetectionError("Failed to decode screenshot")
        return img

    def _match_template(self, img, template, threshold: float = 0.8):
        """Match template in image, return center coordinates."""
        if img is None or template is None:
            return None
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            h, w = template.shape[:2]
            cx = max_loc[0] + w // 2
            cy = max_loc[1] + h // 2
            return (cx, cy)
        return None

    def detect_phase(self, screenshot: bytes) -> GamePhase:
        """
        Detect current game phase from screenshot.

        Args:
            screenshot: Screenshot bytes.

        Returns:
            Detected GamePhase.
        """
        if not CV2_AVAILABLE:
            return GamePhase.UNKNOWN

        try:
            img = self._screenshot_to_image(screenshot)

            # Check for spinning (reels in motion - blur detection)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var > 100:
                return GamePhase.SPINNING

            # Check for bonus round templates
            bonus_template = self._load_template("bonus_icon")
            if bonus_template is not None:
                if self._match_template(img, bonus_template) is not None:
                    return GamePhase.BONUS

            # Check for free spin indicators
            free_spin_template = self._load_template("free_spin")
            if free_spin_template is not None:
                if self._match_template(img, free_spin_template) is not None:
                    return GamePhase.FREE_SPIN

            # Check for collecting state (collect button visible)
            collect_template = self._load_template("collect_button")
            if collect_template is not None:
                if self._match_template(img, collect_template) is not None:
                    return GamePhase.COLLECTING

            return GamePhase.IDLE
        except DetectionError:
            return GamePhase.UNKNOWN

    def extract_balance(self, screenshot: bytes) -> int:
        """
        Extract balance from screenshot using OCR or template.

        Args:
            screenshot: Screenshot bytes.

        Returns:
            Current balance as integer.
        """
        if not CV2_AVAILABLE:
            return 0

        try:
            img = self._screenshot_to_image(screenshot)

            # Try template matching first
            balance_template = self._load_template("balance_display")
            if balance_template is not None:
                match = self._match_template(img, balance_template)
                if match:
                    # Extract region around match for OCR
                    x, y = match
                    h, w = balance_template.shape[:2]
                    roi = img[y : y + h, x : x + w]
                    return self._simple_ocr_number(roi)

            return 0
        except Exception:
            return 0

    def detect_spin_button(self, screenshot: bytes) -> Optional[tuple]:
        """
        Find spin button coordinates.

        Args:
            screenshot: Screenshot bytes.

        Returns:
            (x, y) center of spin button, or None.
        """
        if not CV2_AVAILABLE:
            return None

        try:
            img = self._screenshot_to_image(screenshot)
            template = self._load_template("spin_button")
            if template is not None:
                return self._match_template(img, template)
            return None
        except DetectionError:
            return None

    def detect_bonus_round(self, screenshot: bytes) -> bool:
        """
        Detect if bonus round is active.

        Args:
            screenshot: Screenshot bytes.

        Returns:
            True if bonus round detected.
        """
        phase = self.detect_phase(screenshot)
        return phase == GamePhase.BONUS

    def _simple_ocr_number(self, roi) -> int:
        """
        Simple number OCR for balance extraction.

        In production, use pytesseract or ML-based OCR.
        """
        if not CV2_AVAILABLE:
            return 0
        try:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(
                binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if 0.3 < w / h < 3 and w > 3 and h > 3:
                    pass  # placeholder
            return 0
        except Exception:
            return 0
