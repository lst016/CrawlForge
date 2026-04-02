"""
Tests for SlotGameDetector.
"""

import pytest
from unittest.mock import MagicMock, patch

from crawlforge.core.dataclasses import GamePhase
from crawlforge.detectors.slot_detector import SlotGameDetector


class TestSlotGameDetector:
    @pytest.fixture
    def detector(self):
        return SlotGameDetector()

    @pytest.fixture
    def mock_screenshot(self):
        return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    def test_init(self, detector):
        assert detector.template_store is not None
        assert detector._templates == {}

    def test_detect_phase_without_cv2(self, detector, mock_screenshot):
        with patch("crawlforge.detectors.slot_detector.CV2_AVAILABLE", False):
            result = detector.detect_phase(mock_screenshot)
            assert result == GamePhase.UNKNOWN

    def test_detect_phase_idle(self, detector, mock_screenshot):
        with patch("crawlforge.detectors.slot_detector.CV2_AVAILABLE", True):
            with patch("cv2.imdecode", return_value=None):
                result = detector.detect_phase(mock_screenshot)
                assert result == GamePhase.UNKNOWN

    def test_detect_phase_spinning(self, detector, mock_screenshot):
        with patch("crawlforge.detectors.slot_detector.CV2_AVAILABLE", True):
            with patch("cv2.imdecode", return_value=MagicMock()):
                with patch("cv2.cvtColor", return_value=MagicMock()):
                    with patch("cv2.Laplacian") as mock_lap:
                        mock_result = MagicMock()
                        mock_result.var.return_value = 200  # High variance = spinning
                        mock_lap.return_value = mock_result
                        result = detector.detect_phase(mock_screenshot)
                        assert result == GamePhase.SPINNING

    def test_extract_balance_no_cv2(self, detector, mock_screenshot):
        with patch("crawlforge.detectors.slot_detector.CV2_AVAILABLE", False):
            result = detector.extract_balance(mock_screenshot)
            assert result == 0

    def test_detect_spin_button_no_cv2(self, detector, mock_screenshot):
        with patch("crawlforge.detectors.slot_detector.CV2_AVAILABLE", False):
            result = detector.detect_spin_button(mock_screenshot)
            assert result is None

    def test_detect_bonus_round_false(self, detector, mock_screenshot):
        with patch("crawlforge.detectors.slot_detector.CV2_AVAILABLE", False):
            result = detector.detect_bonus_round(mock_screenshot)
            assert result is False

    def test_detect_phase_idle_state(self, detector, mock_screenshot):
        """Test that low Laplacian variance returns IDLE."""
        with patch("crawlforge.detectors.slot_detector.CV2_AVAILABLE", True):
            with patch("cv2.imdecode", return_value=MagicMock()):
                with patch("cv2.cvtColor", return_value=MagicMock()):
                    with patch("cv2.Laplacian") as mock_lap:
                        mock_result = MagicMock()
                        mock_result.var.return_value = 50  # Low variance
                        mock_lap.return_value = mock_result
                        result = detector.detect_phase(mock_screenshot)
                        assert result == GamePhase.IDLE

    def test_match_template_not_found(self, detector, mock_screenshot):
        """Test template match returns None when template not found."""
        with patch("crawlforge.detectors.slot_detector.CV2_AVAILABLE", True):
            with patch("cv2.imdecode", return_value=MagicMock()):
                with patch("cv2.matchTemplate") as mock_match:
                    mock_match.return_value = MagicMock()
                    with patch("cv2.minMaxLoc") as mock_minmax:
                        mock_minmax.return_value = (None, 0.5, None, (0, 0))
                        result = detector.detect_spin_button(mock_screenshot)
                        assert result is None
