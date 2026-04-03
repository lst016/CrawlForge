"""
Priority Task Queue - thread-safe priority queue for game tasks.

Features:
- Priority-based ordering (lower number = higher priority)
- FIFO within same priority
- Size limits
- Task deduplication
- Task timeout support
"""

import asyncio
import time
import uuid
import heapq
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Callable, Union
from enum import Enum
from contextlib import contextmanager


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


@dataclass
class Task:
    """A task in the queue."""
    task_id: str
    priority: int          # Lower = higher priority
    func: Callable         # Async function to execute
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict = field(default_factory=dict)

    def __lt__(self, other: "Task") -> bool:
        # Heapq is a min-heap, so lower priority number = higher priority
        if self.priority != other.priority:
            return self.priority < other.priority
        # FIFO within same priority
        return self.created_at < other.created_at

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries


class PriorityQueue:
    """
    Thread-safe priority queue for async game tasks.

    Usage:
        queue = PriorityQueue(max_size=1000)

        # Add tasks
        queue.push(my_async_func, priority=1, args=(...), kwargs={...})
        queue.push(another_func, priority=5)  # Lower priority

        # Process tasks
        async for task in queue.pop_all():
            result = await task.func(*task.args, **task.kwargs)
            queue.complete(task.task_id, result)
    """

    def __init__(
        self,
        max_size: int = 0,  # 0 = unlimited
        name: str = "PriorityQueue",
    ):
        self.max_size = max_size
        self.name = name
        self._heap: list[Task] = []
        self._tasks: dict[str, Task] = {}  # task_id -> Task (for dedup/lookup)
        self._lock = threading.RLock()
        self._closed = False

    def push(
        self,
        func: Callable,
        priority: int = 5,
        task_id: Optional[str] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        scheduled_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        max_retries: int = 3,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Add a task to the queue.

        Args:
            func: Async callable to execute
            priority: Task priority (lower = higher priority, 1-10)
            task_id: Optional custom task ID (auto-generated if None)
            args: Positional args for func
            kwargs: Keyword args for func
            scheduled_at: Optional future scheduled time
            expires_at: Optional expiration time
            max_retries: Max retry attempts
            metadata: Optional metadata dict

        Returns:
            task_id
        """
        with self._lock:
            if self._closed:
                raise RuntimeError("Queue is closed")

            task_id = task_id or str(uuid.uuid4())[:12]

            # Check for duplicate
            if task_id in self._tasks:
                raise ValueError(f"Task with ID {task_id} already exists")

            # Check size limit
            if self.max_size > 0 and len(self._tasks) >= self.max_size:
                raise RuntimeError(f"Queue is full (max_size={self.max_size})")

            task = Task(
                task_id=task_id,
                priority=priority,
                func=func,
                args=args or (),
                kwargs=kwargs or {},
                scheduled_at=scheduled_at,
                expires_at=expires_at,
                max_retries=max_retries,
                metadata=metadata or {},
            )

            heapq.heappush(self._heap, task)
            self._tasks[task_id] = task

            return task_id

    def pop(self, timeout: float = 0) -> Optional[Task]:
        """
        Pop the highest priority task (blocking if timeout > 0).

        Args:
            timeout: Seconds to wait (0 = non-blocking)

        Returns:
            Task or None
        """
        if timeout <= 0:
            return self._pop_one()

        start = time.monotonic()
        while True:
            task = self._pop_one()
            if task is not None:
                return task
            if time.monotonic() - start >= timeout:
                return None
            time.sleep(0.01)

    def _pop_one(self) -> Optional[Task]:
        """Non-blocking pop."""
        with self._lock:
            now = datetime.now()

            # Remove expired tasks first
            while self._heap and self._heap[0].is_expired:
                task = heapq.heappop(self._heap)
                task.status = TaskStatus.TIMED_OUT
                del self._tasks[task.task_id]

            # Check if queue is empty
            if not self._heap:
                return None

            task = heapq.heappop(self._heap)
            del self._tasks[task.task_id]
            return task

    def pop_all(self, max_count: int = 10) -> list[Task]:
        """
        Pop up to max_count tasks.

        Returns up to max_count tasks in priority order.
        """
        tasks = []
        with self._lock:
            for _ in range(min(max_count, len(self._heap))):
                task = self._pop_one()
                if task is None:
                    break
                tasks.append(task)
        return tasks

    def peek(self) -> Optional[Task]:
        """Peek at the highest priority task without removing it."""
        with self._lock:
            if not self._heap:
                return None
            return self._heap[0]

    def get(self, task_id: str) -> Optional[Task]:
        """Get a task by ID without removing it."""
        with self._lock:
            return self._tasks.get(task_id)

    def complete(self, task_id: str, result: Any = None) -> bool:
        """Mark a task as completed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = TaskStatus.COMPLETED
            task.result = result
            return True

    def fail(self, task_id: str, error: str) -> bool:
        """Mark a task as failed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = TaskStatus.FAILED
            task.error = error
            task.retry_count += 1
            return True

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status != TaskStatus.PENDING:
                return False
            task.status = TaskStatus.CANCELLED
            del self._tasks[task_id]
            # Also remove from heap
            self._heap = [t for t in self._heap if t.task_id != task_id]
            heapq.heapify(self._heap)
            return True

    def requeue(self, task_id: str, new_priority: Optional[int] = None) -> bool:
        """
        Requeue a failed task for retry.

        Returns True if requeued, False if max_retries exceeded or not failed.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.status not in (TaskStatus.FAILED, TaskStatus.TIMED_OUT):
                return False
            if not task.can_retry:
                return False

            task.retry_count += 1
            task.status = TaskStatus.PENDING
            if new_priority is not None:
                task.priority = new_priority

            heapq.heappush(self._heap, task)
            return True

    def remove(self, task_id: str) -> bool:
        """Remove a task entirely."""
        return self.cancel(task_id)

    def size(self) -> int:
        """Return number of pending tasks."""
        with self._lock:
            return len(self._tasks)

    def is_empty(self) -> bool:
        """Return True if queue is empty."""
        return self.size() == 0

    def clear(self) -> int:
        """Clear all tasks. Returns count of cleared tasks."""
        with self._lock:
            count = len(self._tasks)
            self._heap.clear()
            self._tasks.clear()
            return count

    def close(self) -> None:
        """Close the queue (no more pushes allowed)."""
        with self._lock:
            self._closed = True

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
    ) -> list[Task]:
        """List tasks, optionally filtered by status."""
        with self._lock:
            tasks = list(self._tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            return sorted(tasks, key=lambda t: (t.priority, t.created_at))[:limit]

    def get_stats(self) -> dict:
        """Return queue statistics."""
        with self._lock:
            tasks = list(self._tasks.values())
            return {
                "name": self.name,
                "total_pending": len(tasks),
                "by_status": {
                    s.value: sum(1 for t in tasks if t.status == s)
                    for s in TaskStatus
                },
                "max_size": self.max_size,
                "closed": self._closed,
            }


class TaskRunner:
    """
    Async task runner that processes tasks from a PriorityQueue.

    Usage:
        queue = PriorityQueue()
        runner = TaskRunner(queue)

        async with runner:
            await runner.run_until_complete()
    """

    def __init__(
        self,
        queue: PriorityQueue,
        max_concurrent: int = 5,
        default_timeout: float = 60.0,
    ):
        self.queue = queue
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._running = False
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def __aenter__(self):
        self._running = True
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self

    async def __aexit__(self, *args):
        self._running = False
        await asyncio.gather(*[
            t for t in asyncio.all_tasks()
            if not t.done() and t != asyncio.current_task()
        ], return_exceptions=True)

    async def run_until_complete(self) -> dict:
        """Run until queue is empty."""
        results = {}

        while self._running and not self.queue.is_empty():
            task = self.queue.pop(timeout=1.0)
            if task is None:
                continue

            asyncio.create_task(self._run_task(task, results))

        # Wait for all running tasks
        while True:
            pending = [t for t in asyncio.all_tasks() if not t.done()]
            if len(pending) <= 1:  # Only current task
                break
            await asyncio.sleep(0.1)

        return results

    async def _run_task(self, task: Task, results: dict) -> None:
        """Run a single task with semaphore control."""
        async with self._semaphore:
            try:
                task.status = TaskStatus.RUNNING
                if asyncio.iscoroutinefunction(task.func):
                    result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs),
                        timeout=self.default_timeout,
                    )
                else:
                    result = task.func(*task.args, **task.kwargs)

                task.status = TaskStatus.COMPLETED
                task.result = result
                results[task.task_id] = result

            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMED_OUT
                task.error = "Task timed out"
                results[task.task_id] = None

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.retry_count += 1
                results[task.task_id] = None

                if task.can_retry:
                    self.queue.requeue(task.task_id)
