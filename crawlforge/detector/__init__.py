"""
Slot Game Detector module.
"""

from .phases import SlotPhase, SpinState, BalanceState
from .slot_detector import SlotGameDetector, SlotUI, SlotDetectionResult

__all__ = [
    "SlotPhase",
    "SpinState",
    "BalanceState",
    "SlotGameDetector",
    "SlotUI",
    "SlotDetectionResult",
]
