"""
Evolution Fixer - automatic repair of failed/broken adapters.

When an adapter fails (detection errors, action failures), the fixer
attempts to automatically diagnose and repair the issue.

Provides:
- Root cause analysis for adapter failures
- Automatic selector/strategy repair
- Fallback strategy activation
- Error classification and recovery
"""

import ast
import inspect
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Callable, Type, Union
from enum import Enum

from .engine import FitnessEvaluator, FitnessMetric, FeedbackRecord


class ErrorType(Enum):
    """Classification of adapter errors."""
    DETECTION_FAILURE = "detection_failure"      # State detection failed
    ACTION_FAILURE = "action_failure"           # Action execution failed
    RUNTIME_ERROR = "runtime_error"             # Runtime-level error
    TIMEOUT = "timeout"                         # Operation timed out
    ASSERTION_FAILURE = "assertion_failure"     # State assertion failed
    UNKNOWN = "unknown"                          # Unclassified error


@dataclass
class ErrorRecord:
    """Record of an error that occurred."""
    error_id: str
    timestamp: datetime
    error_type: ErrorType
    error_message: str
    stack_trace: str
    adapter_name: str
    context: dict = field(default_factory=dict)  # Phase, state, action at time of error
    fix_attempted: bool = False
    fix_succeeded: bool = False
    fix_applied: str = ""


@dataclass
class FixSuggestion:
    """A suggested fix for an error."""
    fix_id: str
    error_type: ErrorType
    description: str
    confidence: float  # 0.0 - 1.0
    code_patch: Optional[str] = None
    config_changes: dict = field(default_factory=dict)
    requires_restart: bool = False


@dataclass
class FixResult:
    """Result of attempting to fix an error."""
    success: bool
    error_id: str
    fix_applied: str
    new_error: Optional[str] = None
    suggestions: list[FixSuggestion] = field(default_factory=list)


class AdapterFixer:
    """
    Automatically diagnose and fix adapter failures.

    Usage:
        fixer = AdapterFixer()

        # Record an error
        error_id = fixer.record_error(
            error_type=ErrorType.DETECTION_FAILURE,
            error_message="Failed to detect spin button",
            adapter_name="SlotGameAdapter",
            context={"screenshot_size": (1080, 1920)},
        )

        # Get fix suggestions
        suggestions = fixer.analyze(error_id)

        # Apply fix
        result = fixer.apply_fix(error_id, suggestions[0])
    """

    def __init__(self):
        self._error_history: list[ErrorRecord] = []
        self._fix_strategies: dict[ErrorType, list[Callable]] = {
            et: [] for et in ErrorType
        }
        self._register_default_strategies()

    def record_error(
        self,
        error_type: ErrorType,
        error_message: str,
        adapter_name: str,
        context: Optional[dict] = None,
        exception: Optional[Exception] = None,
    ) -> str:
        """Record an error and return its ID."""
        error_id = str(uuid.uuid4())[:12]
        record = ErrorRecord(
            error_id=error_id,
            timestamp=datetime.now(),
            error_type=error_type,
            error_message=error_message,
            stack_trace=traceback.format_exc() if exception else "",
            adapter_name=adapter_name,
            context=context or {},
        )
        self._error_history.append(record)
        return error_id

    def analyze(self, error_id: str) -> list[FixSuggestion]:
        """
        Analyze an error and return fix suggestions.

        Returns a list of fix suggestions ordered by confidence.
        """
        record = self._find_error(error_id)
        if record is None:
            return []

        suggestions = []

        # Classify error and generate suggestions
        if record.error_type == ErrorType.DETECTION_FAILURE:
            suggestions.extend(self._analyze_detection_failure(record))
        elif record.error_type == ErrorType.ACTION_FAILURE:
            suggestions.extend(self._analyze_action_failure(record))
        elif record.error_type == ErrorType.TIMEOUT:
            suggestions.extend(self._analyze_timeout(record))
        elif record.error_type == ErrorType.RUNTIME_ERROR:
            suggestions.extend(self._analyze_runtime_error(record))

        # Apply generic strategies
        for strategy in self._fix_strategies.get(record.error_type, []):
            suggestion = strategy(record)
            if suggestion:
                suggestions.append(suggestion)

        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions

    def apply_fix(
        self,
        error_id: str,
        suggestion: FixSuggestion,
        adapter: Any = None,
    ) -> FixResult:
        """
        Apply a fix suggestion to an adapter.

        Args:
            error_id: The error to fix
            suggestion: The fix suggestion to apply
            adapter: Optional adapter instance to modify

        Returns:
            FixResult with outcome
        """
        record = self._find_error(error_id)
        if record is None:
            return FixResult(success=False, error_id=error_id, fix_applied="")

        record.fix_attempted = True

        try:
            if suggestion.code_patch and adapter:
                self._apply_code_patch(adapter, suggestion.code_patch)

            if suggestion.config_changes:
                self._apply_config_changes(adapter, suggestion.config_changes)

            record.fix_applied = suggestion.description
            record.fix_succeeded = True

            return FixResult(
                success=True,
                error_id=error_id,
                fix_applied=suggestion.description,
            )

        except Exception as e:
            record.fix_applied = suggestion.description
            record.fix_applied = ""  # Clear since it failed
            return FixResult(
                success=False,
                error_id=error_id,
                fix_applied=suggestion.description,
                new_error=str(e),
                suggestions=[suggestion],
            )

    def get_error_stats(self) -> dict:
        """Get statistics about recorded errors."""
        total = len(self._error_history)
        by_type = {}
        for et in ErrorType:
            by_type[et.value] = sum(1 for r in self._error_history if r.error_type == et)

        fixed = sum(1 for r in self._error_history if r.fix_succeeded)
        failed = sum(1 for r in self._error_history if r.fix_attempted and not r.fix_succeeded)

        return {
            "total_errors": total,
            "by_type": by_type,
            "fixes_succeeded": fixed,
            "fixes_failed": failed,
        }

    def list_errors(
        self,
        error_type: Optional[ErrorType] = None,
        since: Optional[datetime] = None,
    ) -> list[ErrorRecord]:
        """List errors, optionally filtered."""
        results = list(self._error_history)
        if error_type:
            results = [r for r in results if r.error_type == error_type]
        if since:
            results = [r for r in results if r.timestamp >= since]
        return sorted(results, key=lambda r: r.timestamp, reverse=True)

    def register_strategy(
        self,
        error_type: ErrorType,
        strategy: Callable[[ErrorRecord], Optional[FixSuggestion]],
    ) -> None:
        """Register a custom fix strategy for an error type."""
        self._fix_strategies[error_type].append(strategy)

    # -------------------------------------------------------------------------
    # Error analysis methods
    # -------------------------------------------------------------------------

    def _analyze_detection_failure(self, record: ErrorRecord) -> list[FixSuggestion]:
        """Generate fix suggestions for detection failures."""
        suggestions = []
        ctx = record.context

        # Low confidence detection
        if ctx.get("confidence", 1.0) < 0.5:
            suggestions.append(FixSuggestion(
                fix_id=str(uuid.uuid4())[:12],
                error_type=ErrorType.DETECTION_FAILURE,
                description="Lower confidence threshold from 0.7 to 0.5",
                confidence=0.8,
                config_changes={"confidence_threshold": 0.5},
            ))

        # Template not found
        if "template" in record.error_message.lower() or "match" in record.error_message.lower():
            suggestions.append(FixSuggestion(
                fix_id=str(uuid.uuid4())[:12],
                error_type=ErrorType.DETECTION_FAILURE,
                description="Update/fallback template matcher strategy",
                confidence=0.7,
                requires_restart=True,
            ))

        # OCR failure
        if "ocr" in record.error_message.lower() or "text" in record.error_message.lower():
            suggestions.append(FixSuggestion(
                fix_id=str(uuid.uuid4())[:12],
                error_type=ErrorType.DETECTION_FAILURE,
                description="Enable OCR fallback with cached templates",
                confidence=0.6,
                config_changes={"use_ocr_fallback": True},
            ))

        # No screenshot
        if "screenshot" in record.error_message.lower() or "screen" in record.error_message.lower():
            suggestions.append(FixSuggestion(
                fix_id=str(uuid.uuid4())[:12],
                error_type=ErrorType.DETECTION_FAILURE,
                description="Check runtime screenshot capture; increase timeout",
                confidence=0.9,
                config_changes={"screenshot_timeout_ms": 5000},
            ))

        return suggestions

    def _analyze_action_failure(self, record: ErrorRecord) -> list[FixSuggestion]:
        """Generate fix suggestions for action failures."""
        suggestions = []
        ctx = record.context

        # Invalid coordinates
        if "coordinate" in record.error_message.lower() or "x" in record.error_message.lower():
            suggestions.append(FixSuggestion(
                fix_id=str(uuid.uuid4())[:12],
                error_type=ErrorType.ACTION_FAILURE,
                description="Validate/re-calibrate action coordinates",
                confidence=0.8,
                config_changes={"coordinate_validation": True},
            ))

        # Element not found
        if "element" in record.error_message.lower() or "not found" in record.error_message.lower():
            suggestions.append(FixSuggestion(
                fix_id=str(uuid.uuid4())[:12],
                error_type=ErrorType.ACTION_FAILURE,
                description="Retry with longer wait; use fallback position",
                confidence=0.7,
                config_changes={"action_retry_wait_ms": 2000, "use_fallback_position": True},
            ))

        # Wrong action type
        if "action" in record.error_message.lower():
            suggestions.append(FixSuggestion(
                fix_id=str(uuid.uuid4())[:12],
                error_type=ErrorType.ACTION_FAILURE,
                description="Review and fix action type mapping",
                confidence=0.6,
            ))

        return suggestions

    def _analyze_timeout(self, record: ErrorRecord) -> list[FixSuggestion]:
        """Generate fix suggestions for timeouts."""
        suggestions = []
        ctx = record.context

        wait_time = ctx.get("wait_ms", ctx.get("timeout_ms", 0))
        suggestions.append(FixSuggestion(
            fix_id=str(uuid.uuid4())[:12],
            error_type=ErrorType.TIMEOUT,
            description=f"Increase timeout from {wait_time}ms to {int(wait_time * 2)}ms",
            confidence=0.9,
            config_changes={"timeout_ms": int(wait_time * 2)},
        ))

        return suggestions

    def _analyze_runtime_error(self, record: ErrorRecord) -> list[FixSuggestion]:
        """Generate fix suggestions for runtime errors."""
        suggestions = []

        # ADB disconnection
        if "adb" in record.error_message.lower() and ("disconnect" in record.error_message.lower() or "offline" in record.error_message.lower()):
            suggestions.append(FixSuggestion(
                fix_id=str(uuid.uuid4())[:12],
                error_type=ErrorType.RUNTIME_ERROR,
                description="Reconnect ADB device; check USB debugging",
                confidence=0.9,
                requires_restart=True,
            ))

        # Browser crash
        if "browser" in record.error_message.lower() or "playwright" in record.error_message.lower():
            suggestions.append(FixSuggestion(
                fix_id=str(uuid.uuid4())[:12],
                error_type=ErrorType.RUNTIME_ERROR,
                description="Restart browser runtime with new context",
                confidence=0.8,
                requires_restart=True,
            ))

        # Memory error
        if "memory" in record.error_message.lower() or "oom" in record.error_message.lower():
            suggestions.append(FixSuggestion(
                fix_id=str(uuid.uuid4())[:12],
                error_type=ErrorType.RUNTIME_ERROR,
                description="Reduce concurrent sessions; clear memory cache",
                confidence=0.7,
                config_changes={"max_concurrent_sessions": 1},
            ))

        return suggestions

    # -------------------------------------------------------------------------
    # Fix application
    # -------------------------------------------------------------------------

    def _apply_code_patch(self, adapter: Any, patch: str) -> None:
        """Apply a code patch to an adapter."""
        # In a full implementation, this would parse and modify adapter code
        # For now, we provide a safe stub
        pass

    def _apply_config_changes(self, adapter: Any, changes: dict) -> None:
        """Apply configuration changes to an adapter."""
        if adapter is not None and hasattr(adapter, "config"):
            config = adapter.config
            for key, value in changes.items():
                if hasattr(config, key):
                    setattr(config, key, value)

    # -------------------------------------------------------------------------
    # Default strategies
    # -------------------------------------------------------------------------

    def _register_default_strategies(self) -> None:
        """Register built-in fix strategies."""

        def retry_strategy(record: ErrorRecord) -> Optional[FixSuggestion]:
            """Suggest retry with exponential backoff for transient errors."""
            transient_keywords = ["connection", "timeout", "temporary", "unavailable"]
            for kw in transient_keywords:
                if kw in record.error_message.lower():
                    return FixSuggestion(
                        fix_id=str(uuid.uuid4())[:12],
                        error_type=record.error_type,
                        description="Retry with exponential backoff (transient error detected)",
                        confidence=0.6,
                        config_changes={"retry_enabled": True, "retry_base_delay_ms": 1000},
                    )
            return None

        self.register_strategy(ErrorType.UNKNOWN, retry_strategy)


import uuid  # for fix_id generation in FixSuggestion


class SelfHealingAdapter:
    """
    Wrapper that adds self-healing capabilities to any adapter.

    Usage:
        wrapped = SelfHealingAdapter(adapter, fixer=AdapterFixer())
        state = await wrapped.detect_state(screenshot)
    """

    def __init__(
        self,
        adapter: Any,
        fixer: Optional[AdapterFixer] = None,
        max_fix_attempts: int = 3,
    ):
        self.adapter = adapter
        self.fixer = fixer or AdapterFixer()
        self.max_fix_attempts = max_fix_attempts
        self._consecutive_errors = 0

    async def detect_state(self, screenshot: bytes) -> Any:
        """Detect state with automatic error recovery."""
        for attempt in range(self.max_fix_attempts):
            try:
                state = await self.adapter.detect_state(screenshot)
                self._consecutive_errors = 0
                return state
            except Exception as e:
                self._consecutive_errors += 1
                error_id = self.fixer.record_error(
                    error_type=self._classify_error(e),
                    error_message=str(e),
                    adapter_name=getattr(self.adapter, "game_name", "unknown"),
                    context={"attempt": attempt + 1},
                    exception=e,
                )

                if attempt < self.max_fix_attempts - 1:
                    suggestions = self.fixer.analyze(error_id)
                    if suggestions:
                        self.fixer.apply_fix(error_id, suggestions[0], self.adapter)

        # All attempts failed
        raise Exception(f"Failed after {self.max_fix_attempts} attempts")

    @staticmethod
    def _classify_error(e: Exception) -> ErrorType:
        """Classify an exception into an ErrorType."""
        msg = str(e).lower()
        if "timeout" in msg or "timed out" in msg:
            return ErrorType.TIMEOUT
        if "detect" in msg or "recognize" in msg or "ocr" in msg:
            return ErrorType.DETECTION_FAILURE
        if "action" in msg or "execute" in msg or "tap" in msg or "click" in msg:
            return ErrorType.ACTION_FAILURE
        if "runtime" in msg or "adb" in msg or "playwright" in msg:
            return ErrorType.RUNTIME_ERROR
        return ErrorType.UNKNOWN
