"""
Tests for Template Matching module.
"""

import pytest
import tempfile
from pathlib import Path
import numpy as np


# Check cv2 availability
_cv2_available = True
try:
    import cv2
except ImportError:
    _cv2_available = False


# ─── Config Tests ─────────────────────────────────────────────────────────────


def test_matching_method_enum():
    """MatchingMethod enum has expected values."""
    from crawlforge.template_matching.config import MatchingMethod

    assert MatchingMethod.TEMPLATE_SQDIFF.value == "tm_sqdiff"
    assert MatchingMethod.TEMPLATE_CCOEFF.value == "tmccoef"
    assert MatchingMethod.TEMPLATE_CCORR.value == "tmccorr"
    assert MatchingMethod.FEATURE_ORB.value == "feature_orb"
    assert MatchingMethod.FEATURE_AKAZE.value == "feature_akaze"


def test_template_matcher_config_defaults():
    """TemplateMatcherConfig has correct defaults."""
    from crawlforge.template_matching.config import TemplateMatcherConfig

    cfg = TemplateMatcherConfig()
    assert cfg.default_threshold == 0.8
    assert cfg.scale_min == 0.8
    assert cfg.scale_min == 0.8
    assert cfg.scale_max == 1.2
    assert cfg.use_grayscale is True
    assert cfg.preprocess is True
    assert cfg.cache_templates is True
    assert cfg.max_results == 10


def test_threshold_config_effective_threshold():
    """ThresholdConfig.effective_threshold returns calibrated or default."""
    from crawlforge.template_matching.config import ThresholdConfig

    cfg = ThresholdConfig(element_type="spin", template_path="/t.png")
    assert cfg.effective_threshold == 0.8  # default

    cfg.calibrated_threshold = 0.92
    assert cfg.effective_threshold == 0.92


# ─── Models Tests ─────────────────────────────────────────────────────────────


def test_match_result_center():
    """MatchResult.center returns correct center coordinates."""
    from crawlforge.template_matching.models import MatchResult
    from crawlforge.template_matching.config import MatchingMethod

    result = MatchResult(
        template_name="spin_btn",
        template_path="/t.png",
        x=100,
        y=200,
        width=50,
        height=60,
        confidence=0.95,
        method=MatchingMethod.TEMPLATE_SQDIFF,
        screenshot_hash="abc123",
    )
    cx, cy = result.center
    assert cx == 125  # 100 + 50//2
    assert cy == 230  # 200 + 60//2


def test_match_result_bbox():
    """MatchResult.bbox returns (x1, y1, x2, y2)."""
    from crawlforge.template_matching.models import MatchResult
    from crawlforge.template_matching.config import MatchingMethod

    result = MatchResult(
        template_name="spin_btn",
        template_path="/t.png",
        x=100,
        y=200,
        width=50,
        height=60,
        confidence=0.95,
        method=MatchingMethod.TEMPLATE_SQDIFF,
        screenshot_hash="abc123",
    )
    assert result.bbox == (100, 200, 150, 260)


def test_match_result_distance_to():
    """MatchResult.distance_to computes Euclidean distance."""
    from crawlforge.template_matching.models import MatchResult
    from crawlforge.template_matching.config import MatchingMethod

    result = MatchResult(
        template_name="spin_btn",
        template_path="/t.png",
        x=100,
        y=200,
        width=50,
        height=60,
        confidence=0.95,
        method=MatchingMethod.TEMPLATE_SQDIFF,
        screenshot_hash="abc123",
    )
    # center is (125, 230), distance to (125, 230) = 0
    assert result.distance_to(125, 230) == 0.0
    # distance to (125, 270) = 40
    assert result.distance_to(125, 270) == 40.0


def test_calibration_record_compute_metrics():
    """CalibrationRecord.compute_metrics computes precision/recall/F1."""
    from crawlforge.template_matching.models import CalibrationRecord

    record = CalibrationRecord(
        template_path="/t.png",
        calibrated_threshold=0.85,
        calibration_screenshots=100,
        true_positives=80,
        false_positives=5,
        true_negatives=10,
        false_negatives=5,
    )
    record.compute_metrics()
    assert record.precision == 80 / 85
    assert record.recall == 80 / 85
    assert abs(record.f1 - (2 * record.precision * record.recall) / (record.precision + record.recall)) < 0.001


# ─── Registry Tests ──────────────────────────────────────────────────────────


def test_registry_register_and_get():
    """ThresholdConfigRegistry.register/get works."""
    from crawlforge.template_matching.registry import ThresholdConfigRegistry
    from crawlforge.template_matching.config import ThresholdConfig

    registry = ThresholdConfigRegistry()
    cfg = ThresholdConfig(element_type="spin_button", template_path="/templates/spin.png")
    registry.register("game_a", "spin_button", cfg)

    retrieved = registry.get("game_a", "spin_button")
    assert retrieved is not None
    assert retrieved.template_path == "/templates/spin.png"
    assert retrieved.element_type == "spin_button"


def test_registry_get_missing():
    """Registry.get returns None for missing entries."""
    from crawlforge.template_matching.registry import ThresholdConfigRegistry

    registry = ThresholdConfigRegistry()
    assert registry.get("nonexistent", "spin") is None
    assert registry.get("game_a", "nonexistent") is None


def test_registry_list_games():
    """Registry.list_games returns all registered game IDs."""
    from crawlforge.template_matching.registry import ThresholdConfigRegistry
    from crawlforge.template_matching.config import ThresholdConfig

    registry = ThresholdConfigRegistry()
    registry.register("game_a", "spin", ThresholdConfig(element_type="s", template_path="/a"))
    registry.register("game_b", "spin", ThresholdConfig(element_type="s", template_path="/b"))
    registry.register("game_a", "balance", ThresholdConfig(element_type="b", template_path="/c"))

    games = registry.list_games()
    assert set(games) == {"game_a", "game_b"}


def test_registry_remove():
    """Registry.remove deletes an entry."""
    from crawlforge.template_matching.registry import ThresholdConfigRegistry
    from crawlforge.template_matching.config import ThresholdConfig

    registry = ThresholdConfigRegistry()
    registry.register("game_a", "spin", ThresholdConfig(element_type="s", template_path="/a"))
    assert registry.get("game_a", "spin") is not None

    removed = registry.remove("game_a", "spin")
    assert removed is True
    assert registry.get("game_a", "spin") is None


def test_registry_yaml_roundtrip(tmp_path):
    """Registry saves and loads from YAML correctly."""
    from crawlforge.template_matching.registry import ThresholdConfigRegistry
    from crawlforge.template_matching.config import ThresholdConfig, MatchingMethod

    registry = ThresholdConfigRegistry()
    registry.register(
        "pragmatic_gates_of_olympus",
        "spin_button",
        ThresholdConfig(
            element_type="spin_button",
            template_path="templates/go_spin.png",
            default_threshold=0.85,
            matching_method=MatchingMethod.TEMPLATE_CCOEFF,
        ),
    )

    yaml_path = tmp_path / "thresholds.yaml"
    registry.save_to_yaml(yaml_path)
    assert yaml_path.exists()

    new_registry = ThresholdConfigRegistry()
    new_registry.load_from_yaml(yaml_path)

    cfg = new_registry.get("pragmatic_gates_of_olympus", "spin_button")
    assert cfg is not None
    assert cfg.template_path == "templates/go_spin.png"
    assert cfg.default_threshold == 0.85
    assert cfg.matching_method == MatchingMethod.TEMPLATE_CCOEFF


def test_registry_yaml_load_nonexistent():
    """Registry.load_from_yaml handles missing file gracefully."""
    from crawlforge.template_matching.registry import ThresholdConfigRegistry

    registry = ThresholdConfigRegistry()
    registry.load_from_yaml(Path("/nonexistent/path.yaml"))  # Should not raise
    assert registry.list_games() == []


# ─── Matcher Tests (cv2 required) ─────────────────────────────────────────────


# 10x10 red PNG bytes
RED_PNG_10x10 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x0a"
    b"\x00\x00\x00\x0a\x08\x02\x00\x00\x00\x9a`\x1c\xfe"
    b"\x00\x00\x00\x1dIDATx\x9cc\xf8\x0f\x00\x00\x00ff"
    b"\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.mark.skipif(not _cv2_available, reason="opencv-python not installed")
def test_matcher_validate_template(tmp_path):
    """TemplateMatcher.validate_template returns bool."""
    from crawlforge.template_matching.matcher import TemplateMatcher

    matcher = TemplateMatcher()
    template_path = tmp_path / "spin.png"
    template_path.write_bytes(RED_PNG_10x10)

    assert matcher.validate_template(str(template_path)) is True
    assert matcher.validate_template("/nonexistent.png") is False


@pytest.mark.skipif(not _cv2_available, reason="opencv-python not installed")
def test_matcher_get_template_size(tmp_path):
    """TemplateMatcher.get_template_size returns correct dimensions."""
    from crawlforge.template_matching.matcher import TemplateMatcher

    matcher = TemplateMatcher()
    template_path = tmp_path / "spin.png"
    template_path.write_bytes(RED_PNG_10x10)

    w, h = matcher.get_template_size(str(template_path))
    assert (w, h) == (10, 10)


@pytest.mark.skipif(not _cv2_available, reason="opencv-python not installed")
def test_matcher_template_cache(tmp_path):
    """TemplateMatcher caches loaded templates."""
    from crawlforge.template_matching.matcher import TemplateMatcher

    matcher = TemplateMatcher()
    template_path = tmp_path / "spin.png"
    template_path.write_bytes(RED_PNG_10x10)

    matcher.get_template_size(str(template_path))
    assert str(template_path) in matcher._template_cache


@pytest.mark.skipif(not _cv2_available, reason="opencv-python not installed")
def test_matcher_clear_cache(tmp_path):
    """TemplateMatcher.clear_cache empties all caches."""
    from crawlforge.template_matching.matcher import TemplateMatcher

    matcher = TemplateMatcher()
    template_path = tmp_path / "spin.png"
    template_path.write_bytes(RED_PNG_10x10)

    matcher.get_template_size(str(template_path))
    assert str(template_path) in matcher._template_cache

    matcher.clear_cache()
    assert str(template_path) not in matcher._template_cache
    assert str(template_path) not in matcher._threshold_cache


@pytest.mark.skipif(not _cv2_available, reason="opencv-python not installed")
def test_matcher_set_calibrated_threshold(tmp_path):
    """TemplateMatcher.set_calibrated_threshold updates threshold cache."""
    from crawlforge.template_matching.matcher import TemplateMatcher

    matcher = TemplateMatcher()
    template_path = tmp_path / "spin.png"
    template_path.write_bytes(RED_PNG_10x10)

    assert str(template_path) not in matcher._threshold_cache
    matcher.set_calibrated_threshold(str(template_path), 0.92)
    assert matcher._threshold_cache[str(template_path)] == 0.92


@pytest.mark.skipif(not _cv2_available, reason="opencv-python not installed")
def test_matcher_match_bytes_input(tmp_path):
    """TemplateMatcher accepts screenshot as bytes."""
    from crawlforge.template_matching.matcher import TemplateMatcher

    matcher = TemplateMatcher()
    template_path = tmp_path / "spin.png"
    template_path.write_bytes(RED_PNG_10x10)

    results = matcher.match(RED_PNG_10x10, str(template_path), threshold=0.1)
    assert len(results) >= 1


@pytest.mark.skipif(not _cv2_available, reason="opencv-python not installed")
def test_matcher_match_with_fallback(tmp_path):
    """TemplateMatcher.match_with_fallback tries templates in order."""
    from crawlforge.template_matching.matcher import TemplateMatcher

    matcher = TemplateMatcher()
    t1 = tmp_path / "t1.png"
    t2 = tmp_path / "t2.png"
    t1.write_bytes(RED_PNG_10x10)
    t2.write_bytes(RED_PNG_10x10)

    result, path = matcher.match_with_fallback(RED_PNG_10x10, ["/nonexistent.png"], threshold=0.1)
    assert result is None
    assert path == ""

    result, path = matcher.match_with_fallback(RED_PNG_10x10, [str(t1), str(t2)], threshold=0.1)
    assert result is not None
    assert path == str(t1)
