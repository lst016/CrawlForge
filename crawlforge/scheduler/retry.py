"""
Exponential Backoff Retry - robust retry logic with jitter.

Features:
- Exponential backoff with configurable base
- Jitter (randomization) to prevent thundering herd
- Max retries limit
- Timeout per attempt
- Budget tracking (total retry budget)
- Decorator and context manager APIs
"""

import asyncio
import random
import time
import functools
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional, Union, TypeVar, Any


T = TypeVar("T")


@dataclass
class RetryBudget:
    """Tracks retry budget (total time/attempts allowed)."""
    max_attempts: int = 5
    max_total_seconds: float = 60.0
    max_cost: float = 10.0  # Abstract cost per attempt

    attempts_used: int = 0
    total_seconds_used: float = 0.0
    total_cost: float = 0.0

    @property
    def attempts_remaining(self) -> int:
        return max(0, self.max_attempts - self.attempts_used)

    @property
    def time_remaining(self) -> float:
        return max(0, self.max_total_seconds - self.total_seconds_used)

    @property
    def is_exhausted(self) -> bool:
        return (
            self.attempts_remaining <= 0
            or self.time_remaining <= 0
        )

    def record(self, elapsed_seconds: float, cost: float = 1.0) -> None:
        self.attempts_used += 1
        self.total_seconds_used += elapsed_seconds
        self.total_cost += cost


@dataclass
class RetryResult:
    """Result of a retry operation."""
    success: bool
    value: Any = None
    error: Optional[Exception] = None
    attempts: int = 0
    total_elapsed: float = 0.0
    retry_history: list[dict] = field(default_factory=list)


@dataclass
class RetryPolicy:
    """
    Policy for retry behavior.

    Attributes:
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        exponential_base: Multiplier for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter (default: True)
        jitter_range: Fraction of delay to randomize (default: 0.3 = ±30%)
        max_attempts: Maximum number of attempts (default: 5)
        timeout: Timeout per attempt in seconds (default: 30.0)
        retriable_exceptions: Exception types to retry on (default: all)
        non_retriable: Exceptions that should never be retried
        on_retry: Callback function called before each retry
    """
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.3
    max_attempts: int = 5
    timeout: float = 30.0
    retriable_exceptions: tuple = ()  # Empty = all exceptions
    non_retriable: tuple = ()
    on_retry: Optional[Callable[[Exception, int], None]] = None

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.

        attempt: 1-based attempt number
        """
        # Exponential backoff: base * (exponential_base ^ (attempt - 1))
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter: ±jitter_range * delay
            half_range = self.jitter_range * delay
            delay = delay + random.uniform(-half_range, half_range)

        return max(0, delay)

    def should_retry(
        self,
        exception: Exception,
        attempt: int,
    ) -> bool:
        """Determine if an exception should be retried."""
        # Check max attempts
        if attempt >= self.max_attempts:
            return False

        # Check non-retriable
        for exc_type in self.non_retriable:
            if isinstance(exception, exc_type):
                return False

        # Check retriable list (if specified)
        if self.retriable_exceptions:
            return isinstance(exception, self.retriable_exceptions)

        # Default: retry all exceptions
        return True

    def describe(self) -> str:
        """Return human-readable description of the policy."""
        jitter_str = f"±{int(self.jitter_range * 100)}% jitter" if self.jitter else "no jitter"
        return (
            f"RetryPolicy(base={self.base_delay}s, max={self.max_delay}s, "
            f"exp={self.exponential_base}, {jitter_str}, max_attempts={self.max_attempts})"
        )


class RetryManager:
    """
    Manages retry operations with budget tracking.

    Usage:
        manager = RetryManager(RetryPolicy(max_attempts=3))

        result = await manager.execute(my_async_func, arg1, arg2)

        if not result.success:
            print(f"Failed after {result.attempts} attempts")
    """

    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or RetryPolicy()

    async def execute(
        self,
        func: Callable[..., T],
        *args,
        budget: Optional[RetryBudget] = None,
        **kwargs,
    ) -> RetryResult:
        """
        Execute a function with retry logic.

        Args:
            func: Async callable to execute
            *args: Positional args for func
            budget: Optional RetryBudget for tracking
            **kwargs: Keyword args for func

        Returns:
            RetryResult with success status and history
        """
        budget = budget or RetryBudget(max_attempts=self.policy.max_attempts)
        history: list[dict] = []
        start_time = time.monotonic()
        attempt = 0

        while not budget.is_exhausted:
            attempt_start = time.monotonic()
            attempt += 1

            try:
                if asyncio.iscoroutinefunction(func):
                    if self.policy.timeout > 0:
                        value = await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=self.policy.timeout,
                        )
                    else:
                        value = await func(*args, **kwargs)
                else:
                    if self.policy.timeout > 0:
                        value = await asyncio.wait_for(
                            asyncio.to_thread(func, *args, **kwargs),
                            timeout=self.policy.timeout,
                        )
                    else:
                        value = await asyncio.to_thread(func, *args, **kwargs)

                elapsed = time.monotonic() - start_time
                return RetryResult(
                    success=True,
                    value=value,
                    attempts=attempt,
                    total_elapsed=elapsed,
                    retry_history=history,
                )

            except asyncio.TimeoutError as e:
                elapsed = time.monotonic() - attempt_start
                history.append({
                    "attempt": attempt,
                    "elapsed": elapsed,
                    "error": "timeout",
                    "exception": str(e),
                })
                budget.record(elapsed)
                if not self.policy.should_retry(e, attempt):
                    break

            except Exception as e:
                elapsed = time.monotonic() - attempt_start
                history.append({
                    "attempt": attempt,
                    "elapsed": elapsed,
                    "error": type(e).__name__,
                    "exception": str(e),
                })
                budget.record(elapsed)

                if not self.policy.should_retry(e, attempt):
                    break

            # Wait before retry
            if not budget.is_exhausted:
                delay = self.policy.calculate_delay(attempt)
                if self.policy.on_retry:
                    self.policy.on_retry(
                        Exception(history[-1].get("exception", "")),
                        attempt,
                    )
                await asyncio.sleep(delay)

        elapsed = time.monotonic() - start_time
        return RetryResult(
            success=False,
            attempts=attempt,
            total_elapsed=elapsed,
            retry_history=history,
        )

    def execute_sync(
        self,
        func: Callable[..., T],
        *args,
        budget: Optional[RetryBudget] = None,
        **kwargs,
    ) -> RetryResult:
        """Synchronous version of execute."""
        budget = budget or RetryBudget(max_attempts=self.policy.max_attempts)
        history: list[dict] = []
        start_time = time.monotonic()
        attempt = 0

        while not budget.is_exhausted:
            attempt_start = time.monotonic()
            attempt += 1

            try:
                value = func(*args, **kwargs)
                elapsed = time.monotonic() - start_time
                return RetryResult(
                    success=True,
                    value=value,
                    attempts=attempt,
                    total_elapsed=elapsed,
                    retry_history=history,
                )

            except Exception as e:
                elapsed = time.monotonic() - attempt_start
                history.append({
                    "attempt": attempt,
                    "elapsed": elapsed,
                    "error": type(e).__name__,
                    "exception": str(e),
                })
                budget.record(elapsed)

                if not self.policy.should_retry(e, attempt):
                    break

            if not budget.is_exhausted:
                delay = self.policy.calculate_delay(attempt)
                if self.policy.on_retry:
                    self.policy.on_retry(e, attempt)
                time.sleep(delay)

        elapsed = time.monotonic() - start_time
        return RetryResult(
            success=False,
            attempts=attempt,
            total_elapsed=elapsed,
            retry_history=history,
        )


def retry(
    policy: Optional[RetryPolicy] = None,
    budget: Optional[RetryBudget] = None,
):
    """
    Decorator for automatic retry.

    Usage:
        @retry()
        async def my_function():
            await do_something()

        @retry(RetryPolicy(base_delay=2.0, max_attempts=3))
        async def my_function():
            await do_something()
    """
    policy = policy or RetryPolicy()
    budget = budget or RetryBudget(max_attempts=policy.max_attempts)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = RetryManager(policy)
            result = await manager.execute(func, *args, budget=budget, **kwargs)
            if not result.success:
                raise result.error or Exception("Retry failed")
            return result.value

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = RetryManager(policy)
            result = manager.execute_sync(func, *args, budget=budget, **kwargs)
            if not result.success:
                raise result.error or Exception("Retry failed")
            return result.value

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def retry_with_result(
    policy: Optional[RetryPolicy] = None,
):
    """
    Decorator that returns RetryResult instead of raising.
    """
    policy = policy or RetryPolicy()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = RetryManager(policy)
            return await manager.execute(func, *args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = RetryManager(policy)
            return manager.execute_sync(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
