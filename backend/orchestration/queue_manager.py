"""
Queue Manager for Phase 8.
Manages job processing queues with priorities, batching, and concurrency control.
"""
import asyncio
import heapq
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable, Set
from enum import Enum
from collections import deque

from utils.logger import get_logger

logger = get_logger(__name__)


class QueuePriority(Enum):
    """Queue priority levels."""
    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


class QueueItemStatus(Enum):
    """Status of a queue item."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    DEAD = "dead"


@dataclass
class QueueItem:
    """An item in the processing queue."""
    id: str
    job_id: int
    task_type: str
    priority: QueuePriority = QueuePriority.NORMAL
    status: QueueItemStatus = QueueItemStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)  # Other item IDs this depends on

    def __lt__(self, other: "QueueItem"):
        """For priority queue ordering (higher priority first, then earlier created)."""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at


@dataclass
class QueueStats:
    """Queue statistics."""
    total_items: int = 0
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    dead: int = 0
    avg_processing_time: float = 0.0


class QueueManager:
    """
    Manages job processing queues with priorities, batching, and concurrency control.
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        max_queue_size: int = 1000,
        default_max_attempts: int = 3,
    ):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.default_max_attempts = default_max_attempts

        # Priority queue for pending items
        self._pending_queue: List[QueueItem] = []

        # Currently processing items
        self._processing: Dict[str, QueueItem] = {}

        # Completed items (for history)
        self._completed: deque = deque(maxlen=1000)

        # Failed items (for retry)
        self._failed: Dict[str, QueueItem] = {}

        # Dead items (exhausted retries)
        self._dead: Dict[str, QueueItem] = {}

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Running state
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None

        # Handlers for different task types
        self._handlers: Dict[str, Callable] = {}

        # Statistics
        self._stats = QueueStats()
        self._processing_times: List[float] = []

        # Item counter for IDs
        self._item_counter = 0

    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler for a task type."""
        self._handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    def unregister_handler(self, task_type: str):
        """Unregister a handler."""
        if task_type in self._handlers:
            del self._handlers[task_type]

    async def enqueue(
        self,
        job_id: int,
        task_type: str,
        priority: QueuePriority = QueuePriority.NORMAL,
        payload: Optional[Dict[str, Any]] = None,
        max_attempts: Optional[int] = None,
        depends_on: Optional[List[str]] = None,
    ) -> str:
        """Add an item to the queue."""
        if len(self._pending_queue) >= self.max_queue_size:
            raise RuntimeError("Queue is full")

        self._item_counter += 1
        item_id = f"{task_type}_{job_id}_{self._item_counter}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        item = QueueItem(
            id=item_id,
            job_id=job_id,
            task_type=task_type,
            priority=priority,
            payload=payload or {},
            max_attempts=max_attempts or self.default_max_attempts,
            depends_on=depends_on or [],
        )

        # Check dependencies
        for dep_id in item.depends_on:
            if dep_id in self._pending_queue or dep_id in self._processing:
                # Dependency not yet completed, will wait
                pass

        heapq.heappush(self._pending_queue, item)
        self._update_stats()

        logger.debug(f"Enqueued item: {item_id} (priority: {priority.name})")
        return item_id

    async def enqueue_batch(
        self,
        items: List[Dict[str, Any]],
    ) -> List[str]:
        """Enqueue multiple items at once."""
        ids = []
        for item_data in items:
            item_id = await self.enqueue(**item_data)
            ids.append(item_id)
        return ids

    def _update_stats(self):
        """Update queue statistics."""
        self._stats.total_items = (
            len(self._pending_queue)
            + len(self._processing)
            + len(self._completed)
            + len(self._failed)
            + len(self._dead)
        )
        self._stats.pending = len(self._pending_queue)
        self._stats.processing = len(self._processing)
        self._stats.completed = len(self._completed)
        self._stats.failed = len(self._failed)
        self._stats.dead = len(self._dead)

        if self._processing_times:
            self._stats.avg_processing_time = sum(self._processing_times) / len(self._processing_times)

    def get_next_item(self) -> Optional[QueueItem]:
        """Get the next item to process (respects dependencies)."""
        # Find first item whose dependencies are met
        for i, item in enumerate(self._pending_queue):
            deps_met = True
            for dep_id in item.depends_on:
                # Check if dependency is completed
                dep_completed = any(c.id == dep_id for c in self._completed)
                if not dep_completed:
                    deps_met = False
                    break

            if deps_met:
                return heapq.heappop(self._pending_queue)

        return None

    async def process_queue(
        self,
        batch_size: int = 10,
        timeout: Optional[float] = None,
    ) -> Dict[str, int]:
        """Process items from the queue."""
        if self._running:
            logger.warning("Queue processor already running")
            return {"processed": 0}

        self._running = True
        results = {"processed": 0, "success": 0, "failed": 0, "retried": 0}

        start_time = datetime.utcnow()
        timeout_time = start_time + timedelta(seconds=timeout) if timeout else None

        try:
            while self._running:
                # Check timeout
                if timeout_time and datetime.utcnow() >= timeout_time:
                    break

                # Check if we can process more
                if len(self._processing) >= self.max_concurrent:
                    await asyncio.sleep(0.5)
                    continue

                # Get next item
                item = self.get_next_item()
                if not item:
                    # No items ready, wait a bit
                    await asyncio.sleep(1)
                    continue

                # Process item
                asyncio.create_task(self._process_item(item))
                results["processed"] += 1

                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)

        finally:
            self._running = False
            self._update_stats()

        return results

    async def _process_item(self, item: QueueItem):
        """Process a single queue item."""
        item.status = QueueItemStatus.PROCESSING
        item.started_at = datetime.utcnow()
        item.attempts += 1

        self._processing[item.id] = item
        self._update_stats()

        handler = self._handlers.get(item.task_type)
        if not handler:
            error = f"No handler registered for task type: {item.task_type}"
            await self._handle_failure(item, error)
            return

        try:
            # Acquire semaphore for concurrency control
            async with self._semaphore:
                # Check if still running (not shutdown)
                if not self._running:
                    return

                # Call handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(item)
                else:
                    result = handler(item)

                item.result = result if isinstance(result, dict) else {"result": result}
                item.status = QueueItemStatus.COMPLETED
                item.completed_at = datetime.utcnow()

                # Record processing time
                if item.started_at:
                    proc_time = (item.completed_at - item.started_at).total_seconds()
                    self._processing_times.append(proc_time)
                    if len(self._processing_times) > 1000:
                        self._processing_times = self._processing_times[-1000:]

                logger.info(f"Item {item.id} completed successfully")

        except Exception as e:
            await self._handle_failure(item, str(e))
            return

        finally:
            # Move to completed
            self._processing.pop(item.id, None)
            self._completed.append(item)
            self._update_stats()

    async def _handle_failure(self, item: QueueItem, error: str):
        """Handle item failure."""
        item.error = error
        logger.error(f"Item {item.id} failed (attempt {item.attempts}/{item.max_attempts}): {error}")

        if item.attempts >= item.max_attempts:
            # Max attempts reached, move to dead
            item.status = QueueItemStatus.DEAD
            self._dead[item.id] = item
            logger.warning(f"Item {item.id} moved to dead queue")
        else:
            # Schedule retry
            item.status = QueueItemStatus.RETRY
            self._failed[item.id] = item
            logger.info(f"Item {item.id} scheduled for retry")

        self._processing.pop(item.id, None)
        self._update_stats()

    async def retry_failed(self, max_items: int = 100) -> int:
        """Retry failed items."""
        retried = 0
        failed_items = list(self._failed.values())[:max_items]

        for item in failed_items:
            if not self._running:
                break

            # Reset for retry
            item.status = QueueItemStatus.PENDING
            item.error = None
            item.started_at = None
            item.completed_at = None

            heapq.heappush(self._pending_queue, item)
            self._failed.pop(item.id, None)
            retried += 1

        self._update_stats()
        logger.info(f"Retried {retried} failed items")
        return retried

    async def requeue_dead(self, max_items: int = 100) -> int:
        """Requeue dead items (reset attempts)."""
        requeued = 0
        dead_items = list(self._dead.values())[:max_items]

        for item in dead_items:
            item.status = QueueItemStatus.PENDING
            item.attempts = 0
            item.error = None
            item.started_at = None
            item.completed_at = None

            heapq.heappush(self._pending_queue, item)
            self._dead.pop(item.id, None)
            requeued += 1

        self._update_stats()
        logger.info(f"Requeued {requeued} dead items")
        return requeued

    def get_item_status(self, item_id: str) -> Optional[QueueItem]:
        """Get status of a specific item."""
        # Check all queues
        for item in self._pending_queue:
            if item.id == item_id:
                return item

        if item_id in self._processing:
            return self._processing[item_id]

        for item in self._completed:
            if item.id == item_id:
                return item

        if item_id in self._failed:
            return self._failed[item_id]

        if item_id in self._dead:
            return self._dead[item_id]

        return None

    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        self._update_stats()
        return self._stats

    def get_all_items(
        self,
        status: Optional[QueueItemStatus] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[QueueItem]:
        """Get all items, optionally filtered."""
        all_items = []

        # Add from all queues
        all_items.extend(self._pending_queue)
        all_items.extend(self._processing.values())
        all_items.extend(self._completed)
        all_items.extend(self._failed.values())
        all_items.extend(self._dead.values())

        # Filter
        if status:
            all_items = [i for i in all_items if i.status == status]

        if task_type:
            all_items = [i for i in all_items if i.task_type == task_type]

        # Sort by created_at descending
        all_items.sort(key=lambda x: x.created_at, reverse=True)

        return all_items[:limit]

    async def clear_completed(self, older_than_hours: int = 24):
        """Clear old completed items."""
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
        self._completed = deque(
            [i for i in self._completed if i.completed_at and i.completed_at > cutoff],
            maxlen=1000
        )
        self._update_stats()

    async def clear_failed(self, older_than_hours: int = 168):  # 1 week
        """Clear old failed items."""
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
        to_remove = [
            item_id for item_id, item in self._failed.items()
            if item.created_at < cutoff
        ]
        for item_id in to_remove:
            del self._failed[item_id]
        self._update_stats()

    async def clear_dead(self, older_than_hours: int = 168):
        """Clear old dead items."""
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
        to_remove = [
            item_id for item_id, item in self._dead.items()
            if item.created_at < cutoff
        ]
        for item_id in to_remove:
            del self._dead[item_id]
        self._update_stats()

    async def pause(self):
        """Pause queue processing."""
        self._running = False
        logger.info("Queue processing paused")

    async def resume(self):
        """Resume queue processing."""
        if not self._running:
            self._running = True
            logger.info("Queue processing resumed")

    async def shutdown(self):
        """Shutdown queue manager."""
        self._running = False

        # Wait for processing items to complete (with timeout)
        if self._processing:
            logger.info(f"Waiting for {len(self._processing)} items to complete...")
            try:
                await asyncio.wait_for(
                    self._wait_for_processing(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for processing items")

        self._update_stats()
        logger.info("Queue manager shutdown complete")

    async def _wait_for_processing(self):
        """Wait for all processing items to complete."""
        while self._processing:
            await asyncio.sleep(0.5)

    def get_pending_count(self) -> int:
        """Get count of pending items."""
        return len(self._pending_queue)

    def get_processing_count(self) -> int:
        """Get count of currently processing items."""
        return len(self._processing)