"""
Application tracker for Phase 7.
Tracks application status, handles retries, and manages submission history.

NOTE: persistence here uses ONLY the real Application columns (see
database/models.py). The ApplyService (application/service.py) is the
authoritative writer during browser runs — this module is a utility for
orchestration-level bookkeeping.
"""
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import select

from database.repositories import RepositoryFactory
from database import get_session
from database.models import Application, ApplicationStatus
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
    mode: str = "manual"
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
    ) -> Optional[ApplicationRecord]:
        """Mark an existing application as APPLYING. Returns None when there is
        no application row yet (ApplyService creates those with the required
        candidate/resume/application_url fields before driving the browser)."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            app = None
            if application_id:
                app = await repos.applications.get_application(application_id)
            if app is None:
                app = await repos.applications.get_application_by_job(job_id)
            if app is None:
                logger.warning(
                    f"No application row for job {job_id} — ApplyService owns creation"
                )
                return None

            app.status = ApplicationStatus.APPLYING
            await session.commit()
            return self._db_to_record(app)

    async def record_application_result(
        self, record: ApplicationRecord, success: bool, details: Dict[str, Any]
    ):
        """Record the result of an application attempt."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            app = await repos.applications.get_application(record.application_id)
            if not app:
                logger.error(f"Application {record.application_id} not found")
                return

            now = datetime.utcnow()
            if success:
                app.status = ApplicationStatus.APPLIED
                app.applied_at = app.applied_at or now
                app.submitted_at = now
                app.confirmation = details.get("confirmation_number")
                app.human_intervention_reason = None
            else:
                error = details.get("error", "Unknown error")
                requires_human = details.get("requires_human", False)

                if requires_human:
                    # Bot filled what it could; owner must review + confirm submit.
                    app.status = ApplicationStatus.NEEDS_HUMAN_INPUT
                    app.fields_remaining = details.get("fields_remaining", [])
                    app.human_intervention_reason = details.get(
                        "human_reason", "Human review required"
                    )
                else:
                    app.status = ApplicationStatus.FAILED
                    app.error_message = str(error)[:2000]

                # Audit trail lives in application_errors — never in error_message.
                try:
                    await repos.applications.add_error(
                        application_id=app.id,
                        source=details.get("source", "tracker"),
                        error_type=type(details.get("exception", Exception())).__name__,
                        error_message=str(error)[:2000],
                        current_url=details.get("current_url"),
                        resolution="retry" if not requires_human else "human_review",
                    )
                except Exception:
                    logger.exception("Failed to record application error audit row")

            await session.commit()

    async def get_pending_retries(self, max_attempts: int = 3) -> List[ApplicationRecord]:
        """Get failed applications that are candidates for retry."""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        async with get_session() as session:
            result = await session.execute(
                select(Application)
                .where(
                    Application.status == ApplicationStatus.FAILED,
                    Application.updated_at < cutoff,
                )
                .limit(max_attempts)
            )
            apps = list(result.scalars().all())
            return [self._db_to_record(app) for app in apps]

    async def get_manual_review_queue(self) -> List[ApplicationRecord]:
        """Get applications requiring manual review."""
        async with get_session() as session:
            result = await session.execute(
                select(Application).where(
                    Application.status == ApplicationStatus.NEEDS_HUMAN_INPUT
                )
            )
            apps = list(result.scalars().all())
            return [self._db_to_record(app) for app in apps]

    async def get_application_status(self, application_id: int) -> Optional[ApplicationRecord]:
        """Get current status of an application."""
        async with get_session() as session:
            repos = RepositoryFactory(session)
            app = await repos.applications.get_application(application_id)
            if app:
                return self._db_to_record(app)
            return None

    async def update_application_status(
        self,
        application_id: int,
        status: ApplicationStatus,
        **kwargs,
    ) -> bool:
        """Update application status."""
        async with get_session() as session:
            repos = RepositoryFactory(session)
            app = await repos.applications.update_application_status(application_id, status)
            return app is not None

    async def mark_human_review_complete(
        self,
        application_id: int,
        success: bool,
        notes: str = "",
    ) -> bool:
        """Mark human review as complete."""
        async with get_session() as session:
            repos = RepositoryFactory(session)

            app = await repos.applications.get_application(application_id)
            if not app:
                return False

            if success:
                app.status = ApplicationStatus.APPLIED
                now = datetime.utcnow()
                app.applied_at = app.applied_at or now
                app.submitted_at = now
            else:
                app.status = ApplicationStatus.FAILED

            app.notes = notes or app.notes
            await session.commit()
            return True

    async def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Simple per-status counts over all applications."""
        since = datetime.utcnow() - timedelta(days=days)
        counts: Dict[str, int] = {}
        total = 0
        async with get_session() as session:
            result = await session.execute(select(Application))
            for app in result.scalars().all():
                created = app.created_at
                if created and created < since:
                    continue
                key = app.status.value if hasattr(app.status, "value") else str(app.status)
                counts[key] = counts.get(key, 0) + 1
                total += 1
        return {"days": days, "total": total, "by_status": counts}

    def _calculate_next_retry(self, attempt: int) -> datetime:
        """Calculate next retry time using exponential backoff."""
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
            attempts=1,
            confirmation_number=app.confirmation,
            submitted_at=app.submitted_at,
            human_review_required=app.status == ApplicationStatus.NEEDS_HUMAN_INPUT,
            human_review_reason=app.human_intervention_reason,
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
    ) -> Optional[int]:
        """Add a job to the application queue (returns None when no row exists yet)."""
        record = await self.tracker.record_application_start(job_id, mode)
        return record.application_id if record else None

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
            pending = await self.tracker.get_pending_retries()
            if not pending:
                break

            batch = pending[:batch_size]
            for record in batch:
                if not self.processing:
                    break

                try:
                    result = await processor(record)
                    results["processed"] += 1

                    if result.success:
                        results["success"] += 1
                    elif getattr(result, "requires_human", False):
                        results["human_review"] += 1
                    else:
                        results["failed"] += 1

                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"Error processing application {record.application_id}: {e}")
                    results["failed"] += 1

        self.processing = False
        return results

    def stop(self):
        """Stop processing."""
        self.processing = False
