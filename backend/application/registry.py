"""
In-memory state for in-flight apply runs.

Everything here lives in the dyno's memory: a Railway restart loses parked
browser sessions (the application row stays NEEDS_HUMAN_INPUT with a
"re-run" hint, so nothing is silently lost). Strong references to asyncio
tasks are mandatory — bare create_task() results get garbage-collected
mid-flight.
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

# application_id -> running asyncio.Task (strong ref prevents GC)
running: Dict[int, asyncio.Task] = {}


@dataclass
class ParkedSubmission:
    """A MANUAL-mode run that filled its form and is waiting for the owner
    to confirm the final Submit from the UI."""
    application_id: int
    automation: object          # browser.automation.BrowserAutomation (live session)
    submission: object          # application.submission.ApplicationSubmission
    submit_selectors: list      # candidate submit-button selectors from the site flow
    created_at: float = field(default_factory=time.time)


# application_id -> parked browser session
parked: Dict[int, ParkedSubmission] = {}

# Serialize browser runs — one chromium at a time keeps Railway memory sane.
apply_semaphore = asyncio.Semaphore(1)

PARK_TTL_SECONDS = 30 * 60  # parked review sessions expire after 30 minutes


def is_running(application_id: int) -> bool:
    _reap_dead()
    task = running.get(application_id)
    return task is not None and not task.done()


def is_parked(application_id: int) -> bool:
    p = parked.get(application_id)
    if p and time.time() - p.created_at > PARK_TTL_SECONDS:
        # Expired — drop it; confirm_submit will report it as gone.
        _drop_parked(application_id)
        return False
    return application_id in parked


def register(application_id: int, task: asyncio.Task):
    running[application_id] = task


def park(application_id: int, automation, submission, submit_selectors):
    parked[application_id] = ParkedSubmission(
        application_id=application_id,
        automation=automation,
        submission=submission,
        submit_selectors=submit_selectors,
    )


def pop_parked(application_id: int) -> Optional[ParkedSubmission]:
    p = parked.pop(application_id, None)
    if p and time.time() - p.created_at > PARK_TTL_SECONDS:
        _close_automation(p)
        return None
    return p


def _drop_parked(application_id: int):
    p = parked.pop(application_id, None)
    if p:
        _close_parked(p)


async def close_all():
    """Best-effort teardown of everything in memory (process shutdown)."""
    for app_id, task in list(running.items()):
        if not task.done():
            task.cancel()
    running.clear()
    for app_id in list(parked.keys()):
        p = parked.pop(app_id, None)
        if p:
            await _close_parked_async(p)


def _close_parked(p: ParkedSubmission):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_close_parked_async(p))
            return
        loop.run_until_complete(_close_parked_async(p))
    except Exception:
        pass


async def _close_parked_async(p: ParkedSubmission):
    for obj in (p.submission, p.automation):
        closer = getattr(obj, "close", None) or getattr(obj, "automation", None)
        try:
            if callable(closer):
                await closer()
        except Exception:
            pass


def _reap_dead():
    """Forget tasks that already finished so is_running() stays truthful."""
    for app_id in [aid for aid, t in running.items() if t.done()]:
        running.pop(app_id, None)
