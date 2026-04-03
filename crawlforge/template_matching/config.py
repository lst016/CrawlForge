"""
Template matching configuration and threshold settings.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class MatchingMethod(Enum):
    """OpenCV template matching methods."""

    TEMPLATE_SQDIFF = "tm_sqdiff"  # Square difference (lower = better)
    TEMPLATE_CCOEFF = "tmccoef"  # Cross-correlation (higher = better)
    TEMPLATE_CCORR = "tmccorr"  # Correlation (higher = better)
    FEATURE_ORB = "feature_orb"  # ORB feature matching
    FEATURE_AKAZE = "feature_akaze"  # AKAZE feature matching


@dataclass
class TemplateMatcherConfig:
    """Configuration for TemplateMatcher."""

    # Default threshold for template matching (0.0 - 1.0)
    default_threshold: float = 0.8

    # Scale range for multi-scale matching
    scale_min: float = 0.8
    scale_max: float = 1.2
    scale_steps: int = 5

    # Use grayscale for matching (faster, more robust to color changes)
    use_grayscale: bool = True

    # Preprocess with histogram equalization
    preprocess: bool = True

    # Cache templates in memory
    cache_templates: bool = True

    # Max results to return (0 = unlimited)
    max_results: int = 10

    # Match method preference
    method: MatchingMethod = MatchingMethod.TEMPLATE_SQDIFF

    # Feature matching parameters
    feature_match_threshold: float = 0.75
    feature_match_ratio: float = 0.75  # Lowe's ratio test

    # Calibration settings
    calibration_target_fpr: float = 0.01  # target false positive rate

    # Logging
    verbose: bool = False


@dataclass
class ThresholdConfig:
    """Per-template or per-element-type threshold configuration."""

    element_type: str  # e.g., "spin_button", "balance"
    template_path: str
    default_threshold: float = 0.8
    calibrated_threshold: Optional[float] = None
    matching_method: MatchingMethod = MatchingMethod.TEMPLATE_SQDIFF
    scale_range: tuple[float, float] = (0.8, 1.2)
    use_grayscale: bool = True
    preprocessed: bool = True
    description: str = ""

    @property
    def effective_threshold(self) -> float:
        """Return calibrated threshold if set, otherwise default."""
        return self.calibrated_threshold or self.default_threshold
