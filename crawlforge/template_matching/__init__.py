"""
Template Matching - OpenCV-based visual fallback for game element detection.

Provides pixel-accurate template matching when AI-based detection fails or as
a primary detection method for games with no accessibility API.
"""

from .config import MatchingMethod, TemplateMatcherConfig, ThresholdConfig
from .models import MatchResult, CalibrationRecord
from .matcher import TemplateMatcher
from .calibrator import TemplateCalibrator
from .registry import ThresholdConfigRegistry

__all__ = [
    "MatchingMethod",
    "TemplateMatcherConfig",
    "ThresholdConfig",
    "MatchResult",
    "CalibrationRecord",
    "TemplateMatcher",
    "TemplateCalibrator",
    "ThresholdConfigRegistry",
]
