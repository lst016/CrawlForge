"""
Template matching engine using OpenCV.

Provides efficient template matching with multi-scale search and
confidence scoring.
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass
from .store import Template, TemplateStore, MatchResult


class TemplateMatcher:
    """
    OpenCV-based template matching engine.

    Features:
    - Multi-scale template matching (handles different screen densities)
    - Configurable match threshold
    - Best-match extraction
    - RGB/BGR support
    """

    def __init__(
        self,
        store: TemplateStore,
        use_multiscale: bool = True,
        scales: list[float] = None,
    ):
        """
        Args:
            store: TemplateStore instance.
            use_multiscale: Enable multi-scale matching.
            scales: Scale factors for multi-scale matching.
        """
        self.store = store
        self.use_multiscale = use_multiscale
        self.scales = scales or [0.8, 0.9, 1.0, 1.1, 1.2]

    def match(
        self,
        screenshot: bytes,
        template: Template,
    ) -> Optional[MatchResult]:
        """
        Find template in screenshot.

        Args:
            screenshot: Screenshot image bytes (PNG/JPEG).
            template: Template to find.

        Returns:
            MatchResult if found above threshold, else None.
        """
        try:
            import cv2
        except ImportError:
            return None

        # Decode images
        screen = cv2.imdecode(
            np.frombuffer(screenshot, dtype=np.uint8),
            cv2.IMREAD_COLOR
        )
        if screen is None:
            return None

        template_path = self.store.get_image_path(template)
        if not template_path.exists():
            return None

        template_img = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if template_img is None:
            return None

        if self.use_multiscale:
            return self._match_multiscale(screen, template_img, template)
        else:
            return self._match_single(screen, template_img, template)

    def _match_single(
        self,
        screen: np.ndarray,
        template_img: np.ndarray,
        template: Template,
    ) -> Optional[MatchResult]:
        """Single-scale template matching."""
        try:
            import cv2
        except ImportError:
            return None

        result = cv2.matchTemplate(screen, template_img, cv2.TM_CCOFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= template.threshold:
            h, w = template_img.shape[:2]
            x1, y1 = max_loc
            x2, y2 = x1 + w, y1 + h
            return MatchResult(
                template=template,
                confidence=float(max_val),
                bbox=(x1, y1, x2, y2),
                center=(x1 + w // 2, y1 + h // 2),
                matched=True,
            )
        return None

    def _match_multiscale(
        self,
        screen: np.ndarray,
        template_img: np.ndarray,
        template: Template,
    ) -> Optional[MatchResult]:
        """Multi-scale template matching."""
        try:
            import cv2
        except ImportError:
            return None

        best_match = None
        best_confidence = template.threshold - 0.01

        screen_h, screen_w = screen.shape[:2]
        template_h, template_w = template_img.shape[:2]

        for scale in self.scales:
            # Scale template
            scaled_w = int(template_w * scale)
            scaled_h = int(template_h * scale)

            if scaled_w > screen_w or scaled_h > screen_h:
                continue

            scaled = cv2.resize(template_img, (scaled_w, scaled_h))
            result = cv2.matchTemplate(screen, scaled, cv2.TM_CCOFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val > best_confidence:
                best_confidence = max_val
                x1, y1 = max_loc
                x2, y2 = x1 + scaled_w, y1 + scaled_h
                best_match = MatchResult(
                    template=template,
                    confidence=float(max_val),
                    bbox=(x1, y1, x2, y2),
                    center=(x1 + scaled_w // 2, y1 + scaled_h // 2),
                    matched=True,
                )

        return best_match

    def match_any(
        self,
        screenshot: bytes,
        templates: list[Template],
    ) -> Optional[MatchResult]:
        """
        Match against multiple templates, returning the best match.

        Args:
            screenshot: Screenshot image bytes.
            templates: List of templates to try.

        Returns:
            Best MatchResult or None.
        """
        best = None
        best_conf = 0.0

        for template in templates:
            result = self.match(screenshot, template)
            if result and result.confidence > best_conf:
                best = result
                best_conf = result.confidence

        return best

    def match_all(
        self,
        screenshot: bytes,
        templates: list[Template],
    ) -> list[MatchResult]:
        """
        Match against multiple templates, returning all matches above threshold.

        Args:
            screenshot: Screenshot image bytes.
            templates: List of templates to try.

        Returns:
            List of MatchResults.
        """
        results = []
        for template in templates:
            result = self.match(screenshot, template)
            if result:
                results.append(result)
        return results
