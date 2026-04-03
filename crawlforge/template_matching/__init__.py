"""
Template Matching - OpenCV-based visual fallback for game element detection.

Provides pixel-accurate template matching when AI-based detection fails or as
a primary detection method for games with no accessibility API.

Requires: opencv-python, numpy
"""

from .config import MatchingMethod, TemplateMatcherConfig, ThresholdConfig
from .models import MatchResult, CalibrationRecord
from .registry import ThresholdConfigRegistry

# Optional: only importable when opencv-python is installed
try:
    from .matcher import TemplateMatcher
    from .calibrator import TemplateCalibrator
    _cv2_available = True
except ImportError:
    TemplateMatcher = None  # type: ignore
    TemplateCalibrator = None  # type: ignore
    _cv2_available = False

__all__ = [
    "MatchingMethod",
    "TemplateMatcherConfig",
    "ThresholdConfig",
    "MatchResult",
    "CalibrationRecord",
    "TemplateMatcher",
    "TemplateCalibrator",
    "ThresholdConfigRegistry",
    "_cv2_available",
]
