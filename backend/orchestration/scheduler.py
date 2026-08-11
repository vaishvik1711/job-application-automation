"""
Job Scheduler for Phase 8.
Handles cron-like scheduling of pipeline phases.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class ScheduleType(Enum):
    """Types of scheduled tasks."""
    SEARCH = "search"
    ANALYZE = "analyze"
    RESUMES = "resumes"
    APPLY = "apply"
    EXPORT = "export"
    RETRY = "retry"
    CLEANUP = "cleanup"
    CUSTOM = "custom"


@dataclass
class ScheduleConfig:
    """Configuration for the scheduler."""
    search_interval_hours: int = 24
    analyze_interval_hours: int = 6
    apply_interval_hours: int = 12
    export_interval_hours: int = 24
    retry_interval_hours: int = 24
    cleanup_interval_hours: int = 168  # Weekly
    max_concurrent_tasks: int = 1
    timezone: str = "UTC"


@dataclass
class ScheduledTask:
    """A scheduled task."""
    name: str
    task_type: ScheduleType
    interval_hours: float
    handler: Callable
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class JobScheduler:
    """
    Cron-like scheduler for recurring pipeline tasks.
    Runs tasks at configured intervals.
    """

    def __init__(self, config: ScheduleConfig):
        self.config = config
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def add_task(
        self,
        name: str,
        task_type: ScheduleType,
        interval_hours: float,
        handler: Callable,
        enabled: bool = True,
        **metadata,
    ):
        """Add a scheduled task."""
        # Calculate next run time
        next_run = datetime.utcnow() + timedelta(hours=interval_hours)

        task = ScheduledTask(
            name=name,
            task_type=task_type,
            interval_hours=interval_hours,
            handler=handler,
            enabled=enabled,
            next_run=next_run,
            metadata=metadata,
        )

        self.tasks[name] = task
        logger.info(f"Added scheduled task: {name} (every {interval_hours}h)")

    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task."""
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Removed scheduled task: {name}")
            return True
        return False

    def enable_task(self, name: str) -> bool:
        """Enable a scheduled task."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            self.tasks[name].next_run = datetime.utcnow() + timedelta(hours=self.tasks[name].interval_hours)
            return True
        return False

    def disable_task(self, name: str) -> bool:
        """Disable a scheduled task."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            return True
        return False

    async def start(self):
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Scheduler started")

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")

    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_and_run_tasks()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            # Check every minute
            await asyncio.sleep(60)

    async def _check_and_run_tasks(self):
        """Check for tasks that need to run."""
        now = datetime.utcnow()

        for task in self.tasks.values():
            if not task.enabled:
                continue

            if task.next_run and now >= task.next_run:
                # Check concurrency limit
                running_count = sum(1 for t in self.tasks.values() if getattr(t, '_running', False))
                if running_count >= self.config.max_concurrent_tasks:
                    continue

                # Run task
                asyncio.create_task(self._run_task(task))

    async def _run_task(self, task: ScheduledTask):
        """Run a single scheduled task."""
        task._running = True
        start_time = datetime.utcnow()

        try:
            logger.info(f"Running scheduled task: {task.name}")

            if asyncio.iscoroutinefunction(task.handler):
                await task.handler(**task.metadata)
            else:
                task.handler(**task.metadata)

            task.last_run = start_time
            task.run_count += 1
            task.next_run = datetime.utcnow() + timedelta(hours=task.interval_hours)
            task.last_error = None

            logger.info(f"Task {task.name} completed successfully")

        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)
            task.next_run = datetime.utcnow() + timedelta(hours=task.interval_hours)
            logger.error(f"Task {task.name} failed: {e}")

        finally:
            task._running = False

    async def run_once(self, name: str, **kwargs) -> bool:
        """Run a task immediately once."""
        if name not in self.tasks:
            return False

        task = self.tasks[name]
        asyncio.create_task(self._run_task_with_override(task, kwargs))
        return True

    async def _run_task_with_override(self, task: ScheduledTask, override_kwargs: Dict):
        """Run task with override kwargs."""
        task._running = True
        start_time = datetime.utcnow()

        try:
            logger.info(f"Running task manually: {task.name}")

            # Merge metadata with overrides
            merged_kwargs = {**task.metadata, **override_kwargs}

            if asyncio.iscoroutinefunction(task.handler):
                await task.handler(**merged_kwargs)
            else:
                task.handler(**merged_kwargs)

            task.last_run = start_time
            task.run_count += 1
            task.last_error = None

        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)
            logger.error(f"Manual task {task.name} failed: {e}")

        finally:
            task._running = False

    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        if name not in self.tasks:
            return None

        task = self.tasks[name]
        return {
            "name": task.name,
            "type": task.task_type.value,
            "enabled": task.enabled,
            "interval_hours": task.interval_hours,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "run_count": task.run_count,
            "error_count": task.error_count,
            "last_error": task.last_error,
            "running": getattr(task, '_running', False),
        }

    def get_all_status(self) -> List[Dict[str, Any]]:
        """Get status of all tasks."""
        return [self.get_task_status(name) for name in self.tasks]

    def get_next_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get upcoming scheduled runs."""
        tasks_with_next = [
            (name, task) for name, task in self.tasks.items()
            if task.enabled and task.next_run
        ]

        tasks_with_next.sort(key=lambda x: x[1].next_run or datetime.max)

        return [
            {
                "name": name,
                "next_run": task.next_run.isoformat(),
                "interval_hours": task.interval_hours,
            }
            for name, task in tasks_with_next[:limit]
        ]


def create_default_scheduler(config: Optional[ScheduleConfig] = None) -> JobScheduler:
    """Create a scheduler with default tasks."""
    scheduler = JobScheduler(config or ScheduleConfig())

    # These will be set by the orchestrator
    # Placeholder handlers that will be replaced
    async def placeholder_handler(**kwargs):
        logger.info(f"Placeholder handler called with {kwargs}")

    scheduler.add_task("search", ScheduleType.SEARCH, config.search_interval_hours if config else 24, placeholder_handler)
    scheduler.add_task("analyze", ScheduleType.ANALYZE, config.analyze_interval_hours if config else 6, placeholder_handler)
    scheduler.add_task("resumes", ScheduleType.RESUMES, 6, placeholder_handler)  # After analyze
    scheduler.add_task("apply", ScheduleType.APPLY, config.apply_interval_hours if config else 12, placeholder_handler)
    scheduler.add_task("export", ScheduleType.EXPORT, config.export_interval_hours if config else 24, placeholder_handler)
    scheduler.add_task("retry", ScheduleType.RETRY, config.retry_interval_hours if config else 24, placeholder_handler)
    scheduler.add_task("cleanup", ScheduleType.CLEANUP, config.cleanup_interval_hours if config else 168, placeholder_handler)

    return scheduler