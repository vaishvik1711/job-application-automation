"""
Crash recovery for Phase 7.
Handles recovery from crashes during application submission.
"""
import asyncio
import json
import os
import signal
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from enum import Enum

from database.repositories import RepositoryFactory
from database import get_session
from database.models import Application, ApplicationStatus, Job, JobStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class RecoveryState(Enum):
    """States for crash recovery."""
    IDLE = "idle"
    RUNNING = "running"
    CRASHED = "crashed"
    RECOVERING = "recovering"
    RECOVERED = "recovered"


@dataclass
class CrashContext:
    """Context captured at crash time."""
    timestamp: datetime
    job_id: int
    application_id: Optional[int]
    step: str
    error: str
    browser_state: Optional[Dict[str, Any]] = None
    form_data: Optional[Dict[str, Any]] = None
    screenshots: List[str] = field(default_factory=list)


@dataclass
class RecoveryPlan:
    """Plan for recovering from a crash."""
    application_id: int
    action: str  # "retry", "manual_review", "skip", "restart"
    reason: str
    resume_from_step: Optional[str] = None


class CrashRecovery:
    """
    Handles crash recovery for application submissions.
    Saves state periodically and can resume from crashes.
    """

    def __init__(self, state_file: str = "data/recovery_state.json"):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_state = RecoveryState.IDLE
        self.crash_context: Optional[CrashContext] = None
        self._signal_handlers_installed = False

    def install_signal_handlers(self):
        """Install signal handlers for graceful shutdown."""
        if self._signal_handlers_installed:
            return

        def signal_handler(signum, frame):
            logger.warning(f"Received signal {signum}, initiating graceful shutdown")
            asyncio.create_task(self._handle_crash(signum))

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        self._signal_handlers_installed = True

    async def _handle_crash(self, signum: int):
        """Handle crash signal."""
        self.current_state = RecoveryState.CRASHED
        await self.save_state()
        logger.info("State saved, exiting")
        os._exit(1)

    async def start_session(self, job_id: int, application_id: Optional[int] = None):
        """Start a new application session."""
        self.current_state = RecoveryState.RUNNING
        self.crash_context = CrashContext(
            timestamp=datetime.utcnow(),
            job_id=job_id,
            application_id=application_id,
            step="started",
            error="",
        )
        await self.save_state()

    async def update_step(self, step: str, form_data: Optional[Dict] = None):
        """Update current step for recovery."""
        if self.crash_context:
            self.crash_context.step = step
            if form_data:
                self.crash_context.form_data = form_data
            await self.save_state()

    async def record_error(self, error: Exception, browser_state: Optional[Dict] = None):
        """Record an error for recovery analysis."""
        if self.crash_context:
            self.crash_context.error = str(error)
            self.crash_context.browser_state = browser_state
            self.current_state = RecoveryState.CRASHED
            await self.save_state()

    async def add_screenshot(self, path: str):
        """Add a screenshot to crash context."""
        if self.crash_context:
            self.crash_context.screenshots.append(path)
            await self.save_state()

    async def save_state(self):
        """Save current state to file."""
        if not self.crash_context:
            return

        state = {
            "state": self.current_state.value,
            "crash_context": {
                "timestamp": self.crash_context.timestamp.isoformat(),
                "job_id": self.crash_context.job_id,
                "application_id": self.crash_context.application_id,
                "step": self.crash_context.step,
                "error": self.crash_context.error,
                "browser_state": self.crash_context.browser_state,
                "form_data": self.crash_context.form_data,
                "screenshots": self.crash_context.screenshots,
            },
            "saved_at": datetime.utcnow().isoformat(),
        }

        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save recovery state: {e}")

    async def load_state(self) -> Optional[CrashContext]:
        """Load state from file."""
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)

            self.current_state = RecoveryState(state.get("state", "idle"))

            if "crash_context" in state:
                ctx = state["crash_context"]
                self.crash_context = CrashContext(
                    timestamp=datetime.fromisoformat(ctx["timestamp"]),
                    job_id=ctx["job_id"],
                    application_id=ctx.get("application_id"),
                    step=ctx["step"],
                    error=ctx["error"],
                    browser_state=ctx.get("browser_state"),
                    form_data=ctx.get("form_data"),
                    screenshots=ctx.get("screenshots", []),
                )
                return self.crash_context

        except Exception as e:
            logger.error(f"Failed to load recovery state: {e}")

        return None

    async def clear_state(self):
        """Clear recovery state after successful completion."""
        self.current_state = RecoveryState.IDLE
        self.crash_context = None
        if self.state_file.exists():
            self.state_file.unlink()

    async def analyze_crash(self) -> RecoveryPlan:
        """Analyze crash and create recovery plan."""
        if not self.crash_context:
            return RecoveryPlan(
                application_id=0,
                action="skip",
                reason="No crash context available",
            )

        ctx = self.crash_context
        self.current_state = RecoveryState.RECOVERING

        # Check application status in database
        async with get_session() as session:
            repos = RepositoryFactory(session)

            if ctx.application_id:
                app = await repos.applications.get_by_id(ctx.application_id)
                if app:
                    # Application exists, check its status
                    if app.status == ApplicationStatus.APPLIED:
                        return RecoveryPlan(
                            application_id=ctx.application_id,
                            action="skip",
                            reason="Application already submitted successfully",
                        )
                    elif app.status == ApplicationStatus.MANUAL_REVIEW:
                        return RecoveryPlan(
                            application_id=ctx.application_id,
                            action="manual_review",
                            reason="Application requires manual review",
                        )
                    elif app.attempts and app.attempts >= 3:
                        return RecoveryPlan(
                            application_id=ctx.application_id,
                            action="skip",
                            reason="Max retry attempts reached",
                        )
                    else:
                        # Can retry
                        return RecoveryPlan(
                            application_id=ctx.application_id,
                            action="retry",
                            reason=f"Crashed at step: {ctx.step}",
                            resume_from_step=ctx.step,
                        )

        # No application ID or not found - check if job exists
        async with get_session() as session:
            repos = RepositoryFactory(session)
            job = await repos.jobs.get_by_id(ctx.job_id)
            if job and job.status == JobStatus.APPLIED:
                return RecoveryPlan(
                    application_id=0,
                    action="skip",
                    reason="Job already marked as applied",
                )

        # Default: retry from beginning
        return RecoveryPlan(
            application_id=ctx.application_id or 0,
            action="retry",
            reason=f"Crashed at step: {ctx.step}, no prior application found",
            resume_from_step="started",
        )

    async def execute_recovery(self, plan: RecoveryPlan, submit_func: Callable) -> bool:
        """Execute recovery plan."""
        if plan.action == "skip":
            logger.info(f"Skipping application {plan.application_id}: {plan.reason}")
            return True

        elif plan.action == "manual_review":
            logger.info(f"Application {plan.application_id} requires manual review: {plan.reason}")
            # Update status in database
            async with get_session() as session:
                repos = RepositoryFactory(session)
                await repos.applications.update_status(
                    plan.application_id,
                    ApplicationStatus.MANUAL_REVIEW,
                    human_review_required=True,
                    human_review_reason=plan.reason,
                )
            return True

        elif plan.action == "retry":
            logger.info(f"Retrying application {plan.application_id} from step: {plan.resume_from_step}")
            self.current_state = RecoveryState.RUNNING

            try:
                # Call the submit function with resume info
                result = await submit_func(resume_from=plan.resume_from_step, crash_context=self.crash_context)

                if result.success:
                    await self.clear_state()
                    self.current_state = RecoveryState.RECOVERED
                    return True
                else:
                    self.current_state = RecoveryState.CRASHED
                    await self.save_state()
                    return False

            except Exception as e:
                logger.error(f"Recovery retry failed: {e}")
                self.current_state = RecoveryState.CRASHED
                await self.save_state()
                return False

        return False


class CheckpointManager:
    """Manages checkpoints during long-running operations."""

    def __init__(self, checkpoint_dir: str = "data/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints: Dict[str, Any] = {}

    async def save_checkpoint(self, name: str, data: Any):
        """Save a checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{name}.json"
        checkpoint_data = {
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }

        try:
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
            self.checkpoints[name] = checkpoint_data
            logger.debug(f"Checkpoint saved: {name}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint {name}: {e}")

    async def load_checkpoint(self, name: str) -> Optional[Any]:
        """Load a checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{name}.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, "r") as f:
                data = json.load(f)
            return data.get("data")
        except Exception as e:
            logger.error(f"Failed to load checkpoint {name}: {e}")
            return None

    async def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all checkpoints."""
        checkpoints = []
        for file in self.checkpoint_dir.glob("*.json"):
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                checkpoints.append({
                    "name": data.get("name"),
                    "timestamp": data.get("timestamp"),
                    "file": str(file),
                })
            except Exception:
                pass
        return checkpoints

    async def clear_checkpoints(self, pattern: str = "*"):
        """Clear checkpoints matching pattern."""
        for file in self.checkpoint_dir.glob(f"{pattern}.json"):
            file.unlink()
        self.checkpoints.clear()


async def with_crash_recovery(
    job_id: int,
    application_id: Optional[int],
    submit_func: Callable,
    recovery: Optional[CrashRecovery] = None,
) -> Any:
    """
    Wrapper that adds crash recovery to a submit function.
    """
    if recovery is None:
        recovery = CrashRecovery()

    recovery.install_signal_handlers()

    # Check for existing crash state
    await recovery.load_state()

    if recovery.current_state == RecoveryState.CRASHED:
        logger.info("Previous crash detected, analyzing...")
        plan = await recovery.analyze_crash()

        if plan.action == "retry":
            logger.info("Attempting recovery...")
            # Resume from crash point
            return await recovery.execute_recovery(plan, submit_func)
        else:
            return plan

    # Start new session
    await recovery.start_session(job_id, application_id)

    try:
        # Run the submit function with recovery context
        result = await submit_func(recovery=recovery)

        # Success - clear recovery state
        await recovery.clear_state()
        return result

    except Exception as e:
        # Record error and save state
        await recovery.record_error(e)
        raise