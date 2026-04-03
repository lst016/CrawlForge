"""
Data models for template matching.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .config import MatchingMethod


@dataclass
class MatchResult:
    """Result of a template match operation."""

    template_name: str
    template_path: str
    x: int  # top-left x of match in screenshot
    y: int  # top-left y of match in screenshot
    width: int
    height: int
    confidence: float  # 0.0 - 1.0 (normalized)
    method: MatchingMethod
    screenshot_hash: str  # hash of the screenshot matched against

    @property
    def center(self) -> tuple[int, int]:
        """Center coordinates of the match."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """Bounding box as (x1, y1, x2, y2)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    def distance_to(self, other_x: int, other_y: int) -> float:
        """Euclidean distance from match center to another point."""
        cx, cy = self.center
        return ((cx - other_x) ** 2 + (cy - other_y) ** 2) ** 0.5


@dataclass
class CalibrationRecord:
    """Record of a template calibration session."""

    template_path: str
    calibrated_threshold: float
    calibration_screenshots: int
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    calibrated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def compute_metrics(self) -> None:
        """Compute precision, recall, F1 from confusion counts."""
        if self.true_positives + self.false_positives > 0:
            self.precision = self.true_positives / (self.true_positives + self.false_positives)
        if self.true_positives + self.false_negatives > 0:
            self.recall = self.true_positives / (self.true_positives + self.false_negatives)
        if self.precision + self.recall > 0:
            self.f1 = 2 * (self.precision * self.recall) / (self.precision + self.recall)
