"""
Template calibrator - auto-calibrates thresholds for optimal precision/recall.
"""

import logging
from typing import Optional

from .models import CalibrationRecord
from .matcher import TemplateMatcher

logger = logging.getLogger(__name__)


class TemplateCalibrator:
    """
    Auto-calibrates template thresholds against known game states.

    Uses a set of calibration screenshots with known labels (should_match
    or should_not_match) to find the threshold that maximizes F1 score.
    """

    def __init__(self, template_matcher: TemplateMatcher):
        self._matcher = template_matcher
        self._calibration_data: dict[str, CalibrationRecord] = {}

    def calibrate_template(
        self,
        template_path: str,
        screenshots: list[tuple[bytes, bool]],
        target_fpr: float = 0.01,
    ) -> float:
        """
        Find threshold that achieves target false positive rate.

        Args:
            template_path: Path to template image.
            screenshots: List of (screenshot_bytes, should_match) tuples.
            target_fpr: Target false positive rate (0.01 = 1%).

        Returns:
            Optimal threshold value.
        """
        positive_scores: list[float] = []
        negative_scores: list[float] = []

        for img_bytes, should_match in screenshots:
            score = self._get_match_score(img_bytes, template_path)
            if should_match:
                positive_scores.append(score)
            else:
                negative_scores.append(score)

        if not positive_scores:
            logger.warning(f"No positive samples for {template_path}")
            return 0.8

        # Binary search for threshold that achieves target FPR
        threshold = 0.8
        low, high = 0.0, 1.0

        for _ in range(30):
            mid = (low + high) / 2
            fpr = sum(1 for s in negative_scores if s >= mid) / max(len(negative_scores), 1)

            if fpr > target_fpr:
                low = mid
            else:
                high = mid
                threshold = mid

            if abs(fpr - target_fpr) < 0.001:
                break

        # Record calibration
        tp = sum(1 for s in positive_scores if s >= threshold)
        fp = sum(1 for s in negative_scores if s >= threshold)
        fn = sum(1 for s in positive_scores if s < threshold)
        tn = sum(1 for s in negative_scores if s < threshold)

        record = CalibrationRecord(
            template_path=template_path,
            calibrated_threshold=threshold,
            calibration_screenshots=len(screenshots),
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
        )
        record.compute_metrics()
        self._calibration_data[template_path] = record

        # Update matcher threshold cache
        self._matcher.set_calibrated_threshold(template_path, threshold)

        return threshold

    def validate_threshold(
        self,
        template_path: str,
        threshold: float,
        test_screenshots: list[tuple[bytes, bool]],
    ) -> dict:
        """
        Validate threshold against test set.

        Returns:
            Dict with precision, recall, F1, accuracy.
        """
        tp = fp = tn = fn = 0

        for img_bytes, should_match in test_screenshots:
            score = self._get_match_score(img_bytes, template_path)
            matched = score >= threshold

            if should_match and matched:
                tp += 1
            elif should_match and not matched:
                fn += 1
            elif not should_match and matched:
                fp += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "accuracy": accuracy,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        }

    def get_record(self, template_path: str) -> Optional[CalibrationRecord]:
        """Get calibration record for a template."""
        return self._calibration_data.get(template_path)

    def _get_match_score(self, screenshot: bytes, template_path: str) -> float:
        """Get the best match confidence score for a screenshot."""
        result = self._matcher.match_best(screenshot, template_path, threshold=0.0)
        return result.confidence if result else 0.0
