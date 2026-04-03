"""
OpenCV-based template matcher.

Provides pixel-accurate visual fallback using cv2.matchTemplate and feature matching.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

from .config import MatchingMethod, TemplateMatcherConfig, ThresholdConfig
from .models import MatchResult

logger = logging.getLogger(__name__)

# Type alias for image input (bytes or numpy array)
ImageInput = Union[bytes, np.ndarray]


class TemplateMatcher:
    """
    OpenCV-based visual template matching.

    Supports multiple matching methods:
    - cv2.TM_SQDIFF: Square difference (lower = better match)
    - cv2.TM_CCOEFF: Cross-correlation (higher = better match)
    - cv2.TM_CCORR: Correlation (higher = better match)
    - Feature-based: ORB/AKAZE for scaled/rotated templates
    """

    _CV2_METHODS = {
        MatchingMethod.TEMPLATE_SQDIFF: cv2.TM_SQDIFF,
        MatchingMethod.TEMPLATE_CCOEFF: cv2.TM_CCOEFF_NORMED,
        MatchingMethod.TEMPLATE_CCORR: cv2.TM_CCORR_NORMED,
    }

    def __init__(self, config: Optional[TemplateMatcherConfig] = None):
        self._config = config or TemplateMatcherConfig()
        self._template_cache: dict[str, np.ndarray] = {}
        self._threshold_cache: dict[str, float] = {}
        self._template_size_cache: dict[str, tuple[int, int]] = {}

    # ── Core Matching ──────────────────────────────────────────────────────────

    def match(
        self,
        screenshot: ImageInput,
        template_path: str,
        threshold: Optional[float] = None,
    ) -> list[MatchResult]:
        """
        Find all matches of template in screenshot.

        Args:
            screenshot: Screenshot as bytes (PNG/JPEG) or numpy array (BGR).
            template_path: Path to template image file.
            threshold: Minimum confidence threshold (default from config).

        Returns:
            List of MatchResult sorted by confidence (highest first).
        """
        screenshot_arr = self._ensure_array(screenshot)
        template = self._load_template(template_path)
        threshold = threshold or self._config.default_threshold

        if self._config.use_grayscale:
            screenshot_arr = cv2.cvtColor(screenshot_arr, cv2.COLOR_BGR2GRAY)
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        if self._config.preprocess:
            screenshot_arr = self._histogram_equalize(screenshot_arr)
            template = self._histogram_equalize(template)

        screenshot_hash = hashlib.sha256(screenshot_arr.tobytes()).hexdigest()[:16]
        results: list[MatchResult] = []

        method = self._CV2_METHODS.get(self._config.method, cv2.TM_SQDIFF)
        use_sqdiff = method == cv2.TM_SQDIFF

        # Multi-scale matching
        scales = np.linspace(self._config.scale_min, self._config.scale_max, self._config.scale_steps)

        for scale in scales:
            scaled_w = int(template.shape[1] * scale)
            scaled_h = int(template.shape[0] * scale)

            if scaled_w > screenshot_arr.shape[1] or scaled_h > screenshot_arr.shape[0]:
                continue

            scaled_template = cv2.resize(template, (scaled_w, scaled_h))

            # Try different template matching methods
            for m in [cv2.TM_SQDIFF, cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED]:
                result = cv2.matchTemplate(screenshot_arr, scaled_template, m)
                result = np.abs(result)  # Normalize for SQDIFF

                # Find peaks
                if use_sqdiff:
                    # For SQDIFF, lower is better
                    result = 1.0 - result
                    local_max = result > threshold
                else:
                    local_max = result > threshold

                locations = np.where(local_max)
                for pt in zip(*locations[::-1]):  # (x, y)
                    confidence = float(result[pt[1], pt[0]])
                    results.append(MatchResult(
                        template_name=Path(template_path).stem,
                        template_path=template_path,
                        x=int(pt[0]),
                        y=int(pt[1]),
                        width=scaled_w,
                        height=scaled_h,
                        confidence=min(1.0, confidence),
                        method=self._config.method,
                        screenshot_hash=screenshot_hash,
                    ))

        # Deduplicate overlapping matches (Non-Maximum Suppression)
        results = self._non_max_suppression(results)

        # Sort by confidence descending
        results.sort(key=lambda r: r.confidence, reverse=True)

        # Limit results
        if self._config.max_results > 0:
            results = results[:self._config.max_results]

        return results

    def match_best(
        self,
        screenshot: ImageInput,
        template_path: str,
        threshold: Optional[float] = None,
    ) -> Optional[MatchResult]:
        """Return only the best match, or None if no match above threshold."""
        results = self.match(screenshot, template_path, threshold)
        return results[0] if results else None

    def match_with_fallback(
        self,
        screenshot: ImageInput,
        template_paths: list[str],
        threshold: Optional[float] = None,
    ) -> tuple[Optional[MatchResult], str]:
        """
        Try templates in order until one matches.

        Returns:
            (match, matched_template_path) — match is None if no template matched.
        """
        threshold = threshold or self._config.default_threshold
        for path in template_paths:
            result = self.match_best(screenshot, path, threshold)
            if result is not None:
                return result, path
        return None, ""

    def match_features(
        self,
        screenshot: ImageInput,
        template_path: str,
        threshold: float = 0.75,
    ) -> list[MatchResult]:
        """
        Use ORB feature matching for templates that may be scaled/rotated.

        Slower than template matching but more robust to geometric transforms.
        """
        screenshot_arr = self._ensure_array(screenshot)
        template = self._load_template(template_path)

        # Convert to grayscale
        if len(screenshot_arr.shape) == 3:
            screenshot_arr = cv2.cvtColor(screenshot_arr, cv2.COLOR_BGR2GRAY)
        if len(template.shape) == 3:
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # Detect ORB features
        orb = cv2.ORB_create(500)
        kp1, des1 = orb.detectAndCompute(template, None)
        kp2, des2 = orb.detectAndCompute(screenshot_arr, None)

        if des1 is None or des2 is None or len(kp1) == 0 or len(kp2) == 0:
            return []

        # Match features with Lowe's ratio test
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(des1, des2, k=2)

        # Apply Lowe's ratio test
        good = []
        for m_n in matches:
            if len(m_n) == 2:
                m, n = m_n
                if m.distance < self._config.feature_match_ratio * n.distance:
                    good.append(m)

        if len(good) < 4:
            return []

        # Find homography and transform
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if M is None:
            return []

        # Get bounding box of template in screenshot
        h, w = template.shape
        pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, M)

        # Calculate confidence from inlier count
        confidence = min(1.0, len(good) / max(len(kp1), 1) * 2)

        x, y, w, h = cv2.boundingRect(dst)
        screenshot_hash = hashlib.sha256(screenshot_arr.tobytes()).hexdigest()[:16]

        return [MatchResult(
            template_name=Path(template_path).stem,
            template_path=template_path,
            x=int(x),
            y=int(y),
            width=int(w),
            height=int(h),
            confidence=confidence,
            method=MatchingMethod.FEATURE_ORB,
            screenshot_hash=screenshot_hash,
        )]

    # ── Calibration ────────────────────────────────────────────────────────────

    def calibrate(
        self,
        reference_screenshot: ImageInput,
        template_path: str,
        expected_position: Optional[tuple[int, int]] = None,
        tolerance: int = 50,
    ) -> float:
        """
        Find the optimal threshold for a template against a reference screenshot.

        Args:
            reference_screenshot: Screenshot that should contain the template.
            template_path: Path to template image.
            expected_position: (x, y) of expected match center, if known.
            tolerance: Pixel tolerance for position validation.

        Returns:
            Optimal threshold value.
        """
        screenshot_arr = self._ensure_array(reference_screenshot)

        if self._config.use_grayscale:
            screenshot_arr = cv2.cvtColor(screenshot_arr, cv2.COLOR_BGR2GRAY)

        template = self._load_template(template_path)
        if self._config.use_grayscale:
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        method = cv2.TM_CCOEFF_NORMED
        result = cv2.matchTemplate(screenshot_arr, template, method)
        confidence = float(result.max())

        # Binary search for optimal threshold
        low, high = 0.0, 1.0
        best_thresh = confidence

        for _ in range(20):  # 20 iterations of binary search
            mid = (low + high) / 2
            # Check if match at mid threshold is near expected position
            locations = np.where(result >= mid)
            if len(locations[0]) > 0:
                best_idx = np.argmax(result[locations])
                mx = locations[1][best_idx] + template.shape[1] // 2
                my = locations[0][best_idx] + template.shape[0] // 2

                if expected_position:
                    ex, ey = expected_position
                    dist = ((mx - ex) ** 2 + (my - ey) ** 2) ** 0.5
                    if dist <= tolerance:
                        best_thresh = mid
                        high = mid
                    else:
                        low = mid
                else:
                    best_thresh = mid
                    high = mid
            else:
                low = mid

        self._threshold_cache[template_path] = best_thresh
        return best_thresh

    def calibrate_all(
        self,
        templates_dir: Path,
        reference_screenshot: ImageInput,
    ) -> dict[str, float]:
        """Calibrate all templates in a directory."""
        results = {}
        for path in Path(templates_dir).rglob("*.png"):
            try:
                thresh = self.calibrate(reference_screenshot, str(path))
                results[str(path)] = thresh
            except Exception as e:
                logger.warning(f"Calibration failed for {path}: {e}")
        return results

    def set_calibrated_threshold(self, template_path: str, threshold: float) -> None:
        """Set a pre-computed calibrated threshold."""
        self._threshold_cache[template_path] = threshold

    # ── Utility ────────────────────────────────────────────────────────────────

    def get_template_size(self, template_path: str) -> tuple[int, int]:
        """Return (width, height) of a template image."""
        if template_path in self._template_size_cache:
            return self._template_size_cache[template_path]

        template = self._load_template(template_path)
        size = (int(template.shape[1]), int(template.shape[0]))
        self._template_size_cache[template_path] = size
        return size

    def validate_template(self, template_path: str) -> bool:
        """Check if a template image is valid (readable, non-empty)."""
        try:
            template = self._load_template(template_path)
            return template is not None and template.size > 0
        except Exception:
            return False

    def clear_cache(self) -> None:
        """Clear all cached templates and thresholds."""
        self._template_cache.clear()
        self._threshold_cache.clear()
        self._template_size_cache.clear()

    # ── Internal ───────────────────────────────────────────────────────────────

    def _load_template(self, template_path: str) -> np.ndarray:
        """Load template from cache or disk."""
        if self._config.cache_templates and template_path in self._template_cache:
            return self._template_cache[template_path]

        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        template = cv2.imread(str(path))
        if template is None:
            raise ValueError(f"Failed to load template: {template_path}")

        if self._config.cache_templates:
            self._template_cache[template_path] = template

        return template

    def _ensure_array(self, img: ImageInput) -> np.ndarray:
        """Convert bytes to numpy array if needed."""
        if isinstance(img, bytes):
            nparr = np.frombuffer(img, np.uint8)
            arr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if arr is None:
                raise ValueError("Failed to decode screenshot bytes as image")
            return arr
        return img

    def _histogram_equalize(self, gray: np.ndarray) -> np.ndarray:
        """Apply CLAHE histogram equalization."""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def _non_max_suppression(
        self,
        results: list[MatchResult],
        overlap_thresh: float = 0.5,
    ) -> list[MatchResult]:
        """Remove overlapping matches, keeping highest confidence."""
        if not results:
            return results

        boxes = np.array([[r.x, r.y, r.x + r.width, r.y + r.height, r.confidence] for r in results])
        x1, y1, x2, y2, scores = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3], boxes[:, 4]

        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)

            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)

            inds = np.where(ovr <= overlap_thresh)[0]
            order = order[inds + 1]

        return [results[i] for i in keep]
