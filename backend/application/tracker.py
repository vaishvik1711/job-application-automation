"""
Application tracker for Phase 7.
Tracks application status, handles retries, and manages submission history.
"""
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path

from database.repositories import RepositoryFactory
from database import get_session
from database.models import Application, ApplicationStatus, ApplicationError
from utils.logger import get_logger

logger = get_logger(__name__)


class RetryStrategy(Enum):
    """Retry strategies for failed applications."""
    IMMEDIATE = "immediate"
    EXPONENTIAL = "exponential"
    DAILY = "daily"
    MANUAL = "manual"


@dataclass
class ApplicationRecord:
    """Application tracking record."""
    application_id: int
    job_id: int
    status: ApplicationStatus
    mode: str
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    next_retry: Optional[datetime] = None
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    confirmation_number: Optional[str] = None
    submitted_at: Optional[datetime] = None
    human_review_required: bool = False
    human_review_reason: Optional[str] = None


class ApplicationTracker:
    """
    Tracks application submissions, handles retries, and manages submission history.
    """

    def __init__(self):
        self.retry_strategies = {
            RetryStrategy.IMMEDIATE: self._immediate_retry,
            RetryStrategy.EXPONENTIAL: self._exponential_retry,
            RetryStrategy.DAILY: self._daily_retry,
            RetryStrategy.MANUAL: self._manual_retry,
        }

    async def record_application_start(
        self,
        job_id: int,
        mode: str,
        application_id: Optional[int] = None,
    ) -> ApplicationRecord:
        """Record the start of an application attempt."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            if application_id:
                app = await repos.applications.get_by_id(application_id)
                if app:
                    app.status = ApplicationStatus.IN_PROGRESS
                    app.attempts = (app.attempts or 0) + 1
                    app.last_attempt_at = datetime.utcnow()
                    await session.commit()
                    return self._db_to_record(app)

            # Create new application record
            app = await repos.applications.create_application(
                job_id=job_id,
                status=ApplicationStatus.IN_PROGRESS,
                mode=mode,
                attempts=1,
                last_attempt_at=datetime.utcnow(),
            )
            await session.commit()
            return self._db_to_record(app)

    async def record_application_result(self, record: ApplicationRecord, success: bool, details: Dict[str, Any]):
        """Record the result of an application attempt."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            app = await repos.applications.get_by_id(record.application_id)
            if not app:
                logger.error(f"Application {record.application_id} not found")
                return

            if success:
                app.status = ApplicationStatus.APPLIED
                app.submitted_at = datetime.utcnow()
                app.confirmation_number = details.get("confirmation_number")
            else:
                # Determine if we should retry
                error = details.get("error", "Unknown error")
                requires_human = details.get("requires_human", False)

                if requires_human:
                    app.status = ApplicationStatus.MANUAL_REVIEW
                    app.human_review_required = True
                    app.human_review_reason = details.get("human_reason", "Human review required")
                else:
                    app.status = ApplicationStatus.FAILED
                    # Calculate next retry
                    app.next_retry_at = self._calculate_next_retry(app.attempts or 1)

                # Record error
                await repos.applications.add_error(
                    application_id=app.id,
                    error_type=type(details.get("exception", Exception())).__name__,
                    error_message=error,
                    error_details=json.dumps(details),
                    is_retryable=not requires_human,
                )

            await session.commit()

    async def get_pending_retries(self, max_attempts: int = 3) -> List[ApplicationRecord]:
        """Get applications that are ready for retry."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            apps = await repos.applications.get_ready_for_retry(max_attempts=max_attempts)
            return [self._db_to_record(app) for app in apps]

    async def get_manual_review_queue(self) -> List[ApplicationRecord]:
        """Get applications requiring manual review."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            apps = await repos.applications.get_by_status(ApplicationStatus.MANUAL_REVIEW)
            return [self._db_to_record(app) for app in apps]

    async def get_application_status(self, application_id: int) -> Optional[ApplicationRecord]:
        """Get current status of an application."""
        async with get_session() as session:
            repos = RepositoryFactory(session)
            app = await repos.applications.get_by_id(application_id)
            if app:
                return self._db_to_record(app)
            return None

    async def update_application_status(
        self,
        application_id: int,
        status: ApplicationStatus,
        **kwargs
    ) -> bool:
        """Update application status."""
        async with get_session() as session:
            repos = RepositoryFactory(session)
            return await repos.applications.update_status(application_id, status, **kwargs)

    async def mark_human_review_complete(
        self,
        application_id: int,
        success: bool,
        notes: str = "",
    ) -> bool:
        """Mark human review as complete."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            app = await repos.applications.get_by_id(application_id)
            if not app:
                return False

            if success:
                app.status = ApplicationStatus.APPLIED
                app.submitted_at = datetime.utcnow()
            else:
                app.status = ApplicationStatus.FAILED
                app.human_review_required = False

            app.human_review_notes = notes
            app.human_review_completed_at = datetime.utcnow()

            await session.commit()
            return True

    async def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get application statistics."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            stats = await repos.applications.get_statistics(days=days)
            return stats

    def _calculate_next_retry(self, attempt: int) -> datetime:
        """Calculate next retry time using exponential backoff."""
        # Exponential backoff: 1hr, 4hr, 12hr, 24hr, 48hr...
        base_hours = 1
        max_hours = 72
        hours = min(base_hours * (2 ** (attempt - 1)), max_hours)
        return datetime.utcnow() + timedelta(hours=hours)

    def _immediate_retry(self, attempt: int) -> datetime:
        return datetime.utcnow() + timedelta(minutes=5)

    def _exponential_retry(self, attempt: int) -> datetime:
        return self._calculate_next_retry(attempt)

    def _daily_retry(self, attempt: int) -> datetime:
        return datetime.utcnow() + timedelta(days=1)

    def _manual_retry(self, attempt: int) -> datetime:
        # Never auto-retry
        return datetime.utcnow() + timedelta(days=365)

    def _db_to_record(self, app: Application) -> ApplicationRecord:
        """Convert database model to record."""
        return ApplicationRecord(
            application_id=app.id,
            job_id=app.job_id,
            status=app.status,
            mode=app.mode,
            attempts=app.attempts or 0,
            last_attempt=app.last_attempt_at,
            next_retry=app.next_retry_at,
            error_history=[],  # Would load from errors table
            confirmation_number=app.confirmation_number,
            submitted_at=app.submitted_at,
            human_review_required=app.human_review_required,
            human_review_reason=app.human_review_reason,
        )


class ApplicationQueue:
    """Manages the queue of applications to process."""

    def __init__(self, tracker: ApplicationTracker):
        self.tracker = tracker
        self.processing = False

    async def add_to_queue(
        self,
        job_id: int,
        mode: str = "manual",
        priority: int = 0,
    ) -> int:
        """Add a job to the application queue."""
        record = await self.tracker.record_application_start(job_id, mode)
        return record.application_id

    async def process_queue(
        self,
        processor: callable,
        batch_size: int = 10,
        max_concurrent: int = 1,
    ) -> Dict[str, int]:
        """Process queued applications."""
        self.processing = True
        results = {"processed": 0, "success": 0, "failed": 0, "human_review": 0}

        while self.processing:
            # Get pending applications
            pending = await self.tracker.get_pending_retries()

            if not pending:
                break

            # Process batch
            batch = pending[:batch_size]
            for record in batch:
                if not self.processing:
                    break

                try:
                    result = await processor(record)
                    results["processed"] += 1

                    if result.success:
                        results["success"] += 1
                    elif result.requires_human:
                        results["human_review"] += 1
                    else:
                        results["failed"] += 1

                    # Small delay between applications
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"Error processing application {record.application_id}: {e}")
                    results["failed"] += 1

        self.processing = False
        return results

    def stop(self):
        """Stop processing."""
        self.processing = False