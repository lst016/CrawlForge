"""
Tests for Scheduler module.
"""

import asyncio
import tempfile
import time
from datetime import datetime, timedelta
import unittest

from crawlforge.scheduler import (
    PriorityQueue, TaskRunner, Task, TaskStatus,
    CronParser, CronScheduler, CronExpression, ScheduleEntry,
    RetryPolicy, RetryBudget, RetryManager, RetryResult,
)


# ── Queue Tests ────────────────────────────────────────────────────────────────

class TestPriorityQueue(unittest.TestCase):
    """Test PriorityQueue."""

    def test_push_pop_fifo(self):
        q = PriorityQueue()

        async def make_tasks():
            q.push(lambda: None, priority=1, task_id="t1")
            q.push(lambda: None, priority=1, task_id="t2")
            q.push(lambda: None, priority=1, task_id="t3")

            t1 = q.pop()
            t2 = q.pop()
            t3 = q.pop()

            self.assertEqual(t1.task_id, "t1")
            self.assertEqual(t2.task_id, "t2")
            self.assertEqual(t3.task_id, "t3")
            self.assertTrue(q.is_empty())

        asyncio.run(make_tasks())

    def test_priority_ordering(self):
        q = PriorityQueue()

        async def make_tasks():
            q.push(lambda: None, priority=5, task_id="low")
            q.push(lambda: None, priority=1, task_id="high")
            q.push(lambda: None, priority=3, task_id="medium")

            t1 = q.pop()
            t2 = q.pop()
            t3 = q.pop()

            self.assertEqual(t1.task_id, "high")
            self.assertEqual(t2.task_id, "medium")
            self.assertEqual(t3.task_id, "low")

        asyncio.run(make_tasks())

    def test_pop_all(self):
        q = PriorityQueue()

        async def make_tasks():
            # Add 10 tasks
            for i in range(10):
                q.push(lambda i=i: None, priority=5, task_id=f"task{i}")

            # Pop 5 at a time
            batch = q.pop_all(max_count=5)
            self.assertEqual(len(batch), 5)

            batch2 = q.pop_all(max_count=10)
            self.assertEqual(len(batch2), 5)

            self.assertTrue(q.is_empty())

        asyncio.run(make_tasks())

    def test_size_and_clear(self):
        q = PriorityQueue()

        async def make_tasks():
            for i in range(10):
                q.push(lambda: None, priority=5)

            self.assertEqual(q.size(), 10)
            self.assertFalse(q.is_empty())

            cleared = q.clear()
            self.assertEqual(cleared, 10)
            self.assertTrue(q.is_empty())

        asyncio.run(make_tasks())

    def test_get_stats(self):
        q = PriorityQueue(max_size=5)

        async def make_tasks():
            q.push(lambda: None, priority=1, task_id="t1")
            q.push(lambda: None, priority=2, task_id="t2")

            stats = q.get_stats()
            self.assertEqual(stats["total_pending"], 2)
            self.assertEqual(stats["max_size"], 5)

        asyncio.run(make_tasks())


# ── Cron Parser Tests ────────────────────────────────────────────────────────

class TestCronParser(unittest.TestCase):
    """Test CronParser."""

    def test_parse_standard(self):
        parser = CronParser()
        expr = parser.parse("*/5 * * * *")

        self.assertEqual(expr.minute, "*/5")
        self.assertEqual(expr.hour, "*")
        self.assertEqual(expr.day, "*")
        self.assertEqual(expr.month, "*")
        self.assertEqual(expr.weekday, "*")

    def test_parse_named_pattern(self):
        parser = CronParser()
        expr = parser.parse("hourly")

        self.assertEqual(expr.minute, "0")
        self.assertEqual(expr.hour, "*")

    def test_parse_field_ranges(self):
        parser = CronParser()

        ranges = parser.parse_field("1-5", 0, 23)
        self.assertEqual(ranges, [(1, 5)])

        ranges = parser.parse_field("*/2", 0, 59)
        self.assertIn((0, 0), ranges)

        ranges = parser.parse_field("1,3,5", 0, 59)
        self.assertEqual(ranges, [(1, 1), (3, 3), (5, 5)])

    def test_matches(self):
        parser = CronParser()
        expr = parser.parse("*/5 * * * *")  # Every 5 minutes

        # 12:00 - matches
        dt = datetime(2024, 6, 15, 12, 0, 0)
        self.assertTrue(parser.matches(expr, dt))

        # 12:05 - matches
        dt = datetime(2024, 6, 15, 12, 5, 0)
        self.assertTrue(parser.matches(expr, dt))

        # 12:03 - does not match
        dt = datetime(2024, 6, 15, 12, 3, 0)
        self.assertFalse(parser.matches(expr, dt))

    def test_matches_hour_field(self):
        parser = CronParser()
        expr = parser.parse("0 9 * * 1-5")  # 9 AM on weekdays

        # Monday at 9 AM - matches
        dt = datetime(2024, 6, 17, 9, 0, 0)  # Monday
        self.assertTrue(parser.matches(expr, dt))

        # Saturday at 9 AM - does not match
        dt = datetime(2024, 6, 15, 9, 0, 0)  # Saturday
        self.assertFalse(parser.matches(expr, dt))

    def test_next_run(self):
        parser = CronParser()

        expr = parser.parse("*/5 * * * *")  # Every 5 minutes
        base = datetime(2024, 6, 15, 12, 3, 0)
        next_time = parser.next_run(expr, from_time=base)

        self.assertEqual(next_time.minute % 5, 0)
        self.assertGreaterEqual(next_time, base)

    def test_validate_valid(self):
        parser = CronParser()
        valid, msg = parser.validate("*/10 * * * *")
        self.assertTrue(valid)
        self.assertEqual(msg, "")

    def test_validate_invalid(self):
        parser = CronParser()
        valid, msg = parser.validate("60 * * * *")  # 60 invalid for minute
        self.assertFalse(valid)
        self.assertIn("60", msg)


class TestCronScheduler(unittest.TestCase):
    """Test CronScheduler."""

    def test_schedule_and_list(self):
        scheduler = CronScheduler()

        def dummy_task():
            pass

        scheduler.schedule("test", "*/5 * * * *", dummy_task)
        entries = scheduler.list_schedules()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "test")

    def test_unschedule(self):
        scheduler = CronScheduler()

        def dummy_task():
            pass

        scheduler.schedule("test", "* * * * *", dummy_task)
        self.assertTrue(scheduler.unschedule("test"))
        self.assertFalse(scheduler.unschedule("nonexistent"))

    def test_get_next_run(self):
        scheduler = CronScheduler()

        def dummy_task():
            pass

        scheduler.schedule("test", "*/5 * * * *", dummy_task)
        next_run = scheduler.get_next_run("test")

        self.assertIsNotNone(next_run)
        self.assertIsInstance(next_run, datetime)


# ── Retry Tests ──────────────────────────────────────────────────────────────

class TestRetryPolicy(unittest.TestCase):
    """Test RetryPolicy."""

    def test_calculate_delay_exponential(self):
        policy = RetryPolicy(base_delay=1.0, exponential_base=2.0, jitter=False)

        self.assertEqual(policy.calculate_delay(1), 1.0)
        self.assertEqual(policy.calculate_delay(2), 2.0)
        self.assertEqual(policy.calculate_delay(3), 4.0)
        self.assertEqual(policy.calculate_delay(4), 8.0)

    def test_calculate_delay_capped(self):
        policy = RetryPolicy(base_delay=10.0, max_delay=30.0, jitter=False)

        self.assertEqual(policy.calculate_delay(1), 10.0)
        self.assertEqual(policy.calculate_delay(2), 20.0)
        self.assertEqual(policy.calculate_delay(3), 30.0)
        self.assertEqual(policy.calculate_delay(4), 30.0)

    def test_should_retry(self):
        policy = RetryPolicy(max_attempts=3)

        # Under max attempts
        self.assertTrue(policy.should_retry(ValueError("test"), 1))
        self.assertTrue(policy.should_retry(ValueError("test"), 2))

        # At max attempts
        self.assertFalse(policy.should_retry(ValueError("test"), 3))

    def test_non_retriable(self):
        policy = RetryPolicy(
            non_retriable=(ValueError,),
            max_attempts=5,
        )

        self.assertFalse(policy.should_retry(ValueError("test"), 1))
        self.assertTrue(policy.should_retry(KeyError("test"), 1))


class TestRetryBudget(unittest.TestCase):
    """Test RetryBudget."""

    def test_exhaustion(self):
        budget = RetryBudget(max_attempts=3, max_total_seconds=5.0)

        self.assertFalse(budget.is_exhausted)
        self.assertEqual(budget.attempts_remaining, 3)

        budget.record(1.0)
        self.assertEqual(budget.attempts_used, 1)
        self.assertEqual(budget.attempts_remaining, 2)
        self.assertFalse(budget.is_exhausted)

        budget.record(2.0)
        budget.record(3.0)  # Now at max attempts
        self.assertTrue(budget.is_exhausted)

    def test_time_exhaustion(self):
        budget = RetryBudget(max_attempts=10, max_total_seconds=2.0)

        budget.record(1.0)
        budget.record(2.0)  # Exceeds time limit
        self.assertTrue(budget.is_exhausted)


class TestRetryManager(unittest.TestCase):
    """Test RetryManager."""

    def test_successful_execution(self):
        async def succeed():
            return 42

        policy = RetryPolicy(max_attempts=3)
        manager = RetryManager(policy)

        async def run():
            result = await manager.execute(succeed)
            self.assertTrue(result.success)
            self.assertEqual(result.value, 42)
            self.assertEqual(result.attempts, 1)

        asyncio.run(run())

    def test_failed_execution_no_retry(self):
        async def fail():
            raise ValueError("test error")

        policy = RetryPolicy(max_attempts=3)
        manager = RetryManager(policy)

        async def run():
            result = await manager.execute(fail)
            self.assertFalse(result.success)
            self.assertEqual(result.attempts, 3)  # Exhausted all retries
            self.assertEqual(len(result.retry_history), 3)

        asyncio.run(run())

    def test_exponential_backoff(self):
        call_times = []

        async def fail_once_then_succeed():
            call_times.append(time.monotonic())
            if len(call_times) == 1:
                raise ValueError("first fail")
            return 42

        policy = RetryPolicy(base_delay=0.1, max_attempts=5, jitter=False)
        manager = RetryManager(policy)

        async def run():
            result = await manager.execute(fail_once_then_succeed)
            self.assertTrue(result.success)
            self.assertEqual(result.attempts, 2)

            # Check delay between attempts
            delay = call_times[1] - call_times[0]
            self.assertGreaterEqual(delay, 0.09)  # At least base_delay

        asyncio.run(run())

    def test_timeout(self):
        async def slow():
            await asyncio.sleep(10)

        policy = RetryPolicy(max_attempts=2, timeout=0.1)
        manager = RetryManager(policy)

        async def run():
            result = await manager.execute(slow)
            self.assertFalse(result.success)
            self.assertGreaterEqual(result.attempts, 1)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
