"""
Cron Expression Parser - parses and schedules tasks using cron expressions.

Supports:
- Standard 5-field cron (minute, hour, day, month, weekday)
- Common patterns (hourly, daily, weekly)
- Next-run calculation
- Schedule validation
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Union


@dataclass
class CronField:
    """A single cron field."""
    name: str
    min_val: int
    max_val: int


CRON_FIELDS = [
    CronField("minute", 0, 59),
    CronField("hour", 0, 23),
    CronField("day", 1, 31),
    CronField("month", 1, 12),
    CronField("weekday", 0, 6),  # 0=Monday, 6=Sunday
]


@dataclass
class CronExpression:
    """Parsed cron expression."""
    raw: str
    minute: str
    hour: str
    day: str
    month: str
    weekday: str
    second: str = "0"  # Optional seconds field

    def __str__(self) -> str:
        return f"{self.second} {self.minute} {self.hour} {self.day} {self.month} {self.weekday}"


@dataclass
class ScheduleEntry:
    """A scheduled task entry."""
    name: str
    cron_expr: CronExpression
    func: any  # Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    description: str = ""


class CronParser:
    """
    Parse and evaluate cron expressions.

    Usage:
        parser = CronParser()

        # Parse a cron expression
        expr = parser.parse("*/5 * * * *")  # Every 5 minutes

        # Get next run time
        next_time = parser.next_run(expr, from_time=datetime.now())
        print(f"Next run: {next_time}")
    """

    # Common named patterns
    NAMED_PATTERNS = {
        "hourly": "0 * * * *",
        "daily": "0 0 * * *",
        "midnight": "0 0 * * *",
        "noon": "0 12 * * *",
        "weekly": "0 0 * * 0",
        "monthly": "0 0 1 * *",
        "yearly": "0 0 1 1 *",
        "annually": "0 0 1 1 *",
        "every_minute": "* * * * *",
        "every_5_minutes": "*/5 * * * *",
        "every_10_minutes": "*/10 * * * *",
        "every_15_minutes": "*/15 * * * *",
        "every_30_minutes": "*/30 * * * *",
        "weekdays": "0 9 * * 1-5",
        "weekends": "0 9 * * 0,6",
    }

    def __init__(self):
        self._compiled: dict[str, list[tuple[int, int]]] = {}

    def parse(self, expr: str) -> CronExpression:
        """
        Parse a cron expression string.

        Args:
            expr: Cron expression (5 or 6 fields)

        Returns:
            CronExpression object

        Supported formats:
            *         - any value
            */n       - every n units (e.g., */5)
            n,m       - specific values (e.g., 1,3,5)
            n-m       - range (e.g., 1-5)
            n-m/s     - range with step
        """
        expr = expr.strip()

        # Check named patterns
        if expr in self.NAMED_PATTERNS:
            expr = self.NAMED_PATTERNS[expr]

        parts = expr.split()
        if len(parts) == 5:
            second = "0"
            minute, hour, day, month, weekday = parts
        elif len(parts) == 6:
            second, minute, hour, day, month, weekday = parts
        elif len(parts) == 4:
            # Some cron variants use 4 fields (minute, hour, day, month)
            minute, hour, day, month = parts
            weekday = "*"
            second = "0"
        else:
            raise ValueError(f"Invalid cron expression: {expr}")

        return CronExpression(
            raw=expr,
            second=second,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            weekday=weekday,
        )

    def parse_field(self, field_str: str, min_val: int, max_val: int) -> list[tuple[int, int]]:
        """
        Parse a single cron field into a list of (start, end) ranges.

        Returns list of ranges for efficient matching.
        """
        if field_str == "*":
            return [(min_val, max_val)]

        key = f"{field_str}:{min_val}:{max_val}"
        if key in self._compiled:
            return self._compiled[key]

        ranges: list[tuple[int, int]] = []
        parts = field_str.split(",")

        for part in parts:
            part = part.strip()
            if "/" in part:
                # Step: */n or n-m/s
                base, step_str = part.split("/", 1)
                step = int(step_str)

                if base == "*":
                    base_min, base_max = min_val, max_val
                elif "-" in base:
                    base_min, base_max = map(int, base.split("-"))
                else:
                    base_min = int(base)
                    base_max = max_val

                for v in range(base_min, base_max + 1, step):
                    ranges.append((v, v))

            elif "-" in part:
                # Range: n-m
                start, end = map(int, part.split("-"))
                ranges.append((start, end))

            else:
                # Single value
                val = int(part)
                if val < min_val or val > max_val:
                    raise ValueError(
                        f"Value {val} out of range [{min_val}, {max_val}]"
                    )
                ranges.append((val, val))

        # Sort and merge overlapping ranges
        ranges.sort()
        merged = []
        for start, end in ranges:
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        self._compiled[key] = merged
        return merged

    def matches(self, expr: CronExpression, dt: datetime) -> bool:
        """Check if a datetime matches a cron expression."""
        try:
            if not self._match_field(expr.second, dt.second, 0, 59):
                return False
            if not self._match_field(expr.minute, dt.minute, 0, 59):
                return False
            if not self._match_field(expr.hour, dt.hour, 0, 23):
                return False
            if not self._match_field(expr.day, dt.day, 1, 31):
                return False
            if not self._match_field(expr.month, dt.month, 1, 12):
                return False
            # Cron weekday: 0=Sunday, Python weekday: 0=Monday
            cron_weekday = (dt.weekday() + 1) % 7
            if not self._match_field(expr.weekday, cron_weekday, 0, 6):
                return False
            return True
        except ValueError:
            return False

    def _match_field(
        self,
        field_str: str,
        value: int,
        min_val: int,
        max_val: int,
    ) -> bool:
        """Check if a value matches a field."""
        if field_str == "*":
            return True

        ranges = self.parse_field(field_str, min_val, max_val)
        for start, end in ranges:
            if start <= value <= end:
                return True
        return False

    def next_run(
        self,
        expr: Union[CronExpression, str],
        from_time: Optional[datetime] = None,
    ) -> datetime:
        """
        Calculate the next run time after from_time.

        Args:
            expr: CronExpression or string
            from_time: Starting datetime (default: now)

        Returns:
            Next matching datetime
        """
        if isinstance(expr, str):
            expr = self.parse(expr)

        from_time = from_time or datetime.now()

        # Start from the next second
        current = from_time.replace(microsecond=0) + timedelta(seconds=1)

        max_iterations = 60 * 60 * 24 * 32  # Max 32 days of seconds
        for _ in range(max_iterations):
            if self._is_match(expr, current):
                return current
            current += timedelta(seconds=1)

        # Fallback: advance to next minute and iterate faster
        current = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        for _ in range(60 * 24 * 366):  # 1 year of minutes
            if self._is_match(expr, current):
                return current
            current += timedelta(minutes=1)

        raise RuntimeError("Could not find next run time within 1 year")

    def _is_match(self, expr: CronExpression, dt: datetime) -> bool:
        """Check if dt matches the cron expression."""
        try:
            # Second
            if not self._match_field(expr.second, dt.second, 0, 59):
                return False
            # Minute
            if not self._match_field(expr.minute, dt.minute, 0, 59):
                return False
            # Hour
            if not self._match_field(expr.hour, dt.hour, 0, 23):
                return False
            # Day of month
            if not self._match_field(expr.day, dt.day, 1, 31):
                return False
            # Month
            if not self._match_field(expr.month, dt.month, 1, 12):
                return False
            # Day of week: cron uses 0=Sunday, Python weekday() uses 0=Monday
            # Convert Python weekday to cron weekday
            cron_weekday = (dt.weekday() + 1) % 7
            if not self._match_field(expr.weekday, cron_weekday, 0, 6):
                return False
            return True
        except ValueError:
            return False

    def upcoming_runs(
        self,
        expr: Union[CronExpression, str],
        count: int = 10,
        from_time: Optional[datetime] = None,
    ) -> list[datetime]:
        """Get the next N run times."""
        results = []
        next_time = from_time or datetime.now()
        for _ in range(count):
            next_time = self.next_run(expr, from_time=next_time)
            results.append(next_time)
            next_time += timedelta(minutes=1)
        return results

    def validate(self, expr: Union[CronExpression, str]) -> tuple[bool, str]:
        """Validate a cron expression. Returns (is_valid, error_message)."""
        try:
            if isinstance(expr, str):
                parsed = self.parse(expr)
            else:
                parsed = expr

            # Validate each field range
            self.parse_field(parsed.minute, 0, 59)
            self.parse_field(parsed.hour, 0, 23)
            self.parse_field(parsed.day, 1, 31)
            self.parse_field(parsed.month, 1, 12)
            self.parse_field(parsed.weekday, 0, 6)

            return True, ""

        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Validation error: {e}"


class CronScheduler:
    """
    Scheduler that runs tasks based on cron expressions.

    Usage:
        scheduler = CronScheduler()

        async def my_task():
            print("Running scheduled task")

        scheduler.schedule("my_task", "*/5 * * * *", my_task)

        async with scheduler:
            await scheduler.run_forever()
    """

    def __init__(self, timezone: str = "UTC"):
        self.timezone = timezone
        self.parser = CronParser()
        self._entries: dict[str, ScheduleEntry] = {}
        self._running = False

    def schedule(
        self,
        name: str,
        cron_expr: Union[str, CronExpression],
        func,
        args: tuple = (),
        kwargs: dict = None,
        description: str = "",
    ) -> ScheduleEntry:
        """Register a scheduled task."""
        if isinstance(cron_expr, str):
            cron_expr = self.parser.parse(cron_expr)

        entry = ScheduleEntry(
            name=name,
            cron_expr=cron_expr,
            func=func,
            args=args or (),
            kwargs=kwargs or {},
            description=description,
        )
        entry.next_run = self.parser.next_run(cron_expr)
        self._entries[name] = entry
        return entry

    def unschedule(self, name: str) -> bool:
        """Remove a scheduled task."""
        if name in self._entries:
            del self._entries[name]
            return True
        return False

    def get_next_run(self, name: str) -> Optional[datetime]:
        """Get next scheduled run time for a task."""
        entry = self._entries.get(name)
        return entry.next_run if entry else None

    def get_due_tasks(self, as_of: Optional[datetime] = None) -> list[ScheduleEntry]:
        """Get all tasks that are due to run."""
        as_of = as_of or datetime.now()
        due = []
        for entry in self._entries.values():
            if not entry.enabled:
                continue
            if entry.next_run and entry.next_run <= as_of:
                due.append(entry)
        return due

    def update_next_run(self, entry: ScheduleEntry) -> None:
        """Update the next run time for an entry."""
        entry.next_run = self.parser.next_run(entry.cron_expr, from_time=datetime.now())

    def list_schedules(self) -> list[ScheduleEntry]:
        """List all registered schedules."""
        return list(self._entries.values())

    async def run_forever(self, interval: float = 60.0) -> None:
        """Run the scheduler loop."""
        import asyncio

        self._running = True
        while self._running:
            now = datetime.now()
            due = self.get_due_tasks(now)

            for entry in due:
                entry.last_run = now
                self.update_next_run(entry)

                # Run the task (fire and forget)
                asyncio.create_task(self._run_entry(entry))

            await asyncio.sleep(interval)

    async def _run_entry(self, entry: ScheduleEntry) -> None:
        """Run a single scheduled entry."""
        try:
            if asyncio.iscoroutinefunction(entry.func):
                await entry.func(*entry.args, **entry.kwargs)
            else:
                entry.func(*entry.args, **entry.kwargs)
        except Exception as e:
            print(f"Scheduled task {entry.name} failed: {e}")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
