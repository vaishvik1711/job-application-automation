"""
ApplyService — drives one browser apply run per application.

Modes (SubmissionMode):
- MANUAL (default): bot fills the form headless, parks the live browser
  session, and the owner confirms the final Submit from the UI.
- AUTO: submits without review. Requires AUTO_SUBMIT=true in the environment
  AND an explicit per-run override — the route rejects it otherwise.
- DRY_RUN: fills but never submits; parked like MANUAL.

Every run opens its OWN database sessions (never the request session — the
request closes long before the background task finishes).
"""
import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from application import registry
from application.context import build_form_profile
from application.submission import (
    ApplicationSubmission,
    ApplicationContext,
    SubmissionMode,
)
from browser.automation import BrowserAutomation, BrowserConfig
from browser.site_login import LoginOutcome, ensure_logged_in
from browser.sites import SiteFlow, UnsupportedSiteError, detect_site
from database import get_session
from database.models import (
    Application,
    ApplicationError,
    ApplicationEvent,
    ApplicationStatus,
    SiteCredential,
)
from security.crypto import CredentialCryptoError, decrypt_secret
from utils.logger import get_logger

logger = get_logger(__name__)


class ApplyError(Exception):
    """User-facing apply error — message is safe to return to the API."""


class ApplyService:
    """Singleton-style facade used by the API routes."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self, application_id: int, mode: str) -> Dict:
        """Kick off a background apply run. Returns immediately with state."""
        submission_mode = self._parse_mode(mode)

        if submission_mode == SubmissionMode.AUTO and not self._auto_submit_enabled():
            raise ApplyError(
                "AUTO mode is disabled (AUTO_SUBMIT=false). Use manual mode, or enable it in the environment."
            )

        if registry.is_running(application_id):
            raise ApplyError("An apply run is already in progress for this application")
        if registry.is_parked(application_id):
            raise ApplyError(
                "This application already has a parked form awaiting your review — confirm or cancel it first"
            )

        # Validate up-front so the user gets an immediate error for bad state.
        app = await self._load_application(application_id)
        if app is None:
            raise ApplyError(f"Application {application_id} not found")

        flow = detect_site(app.application_url or "", mode=submission_mode.value)

        task = asyncio.create_task(self._run(application_id, submission_mode, flow))
        registry.register(application_id, task)
        return {
            "application_id": str(application_id),
            "state": "started",
            "mode": submission_mode.value,
            "site": flow.name,
        }

    async def confirm_submit(self, application_id: int) -> Dict:
        """Click the real submit button on a parked MANUAL/DRY_RUN session."""
        parked = registry.pop_parked(application_id)
        if parked is None:
            raise ApplyError(
                "No parked form for this application (it may have expired after 30 minutes — re-run apply)"
            )

        try:
            result = await self._click_submit(parked)
            async with get_session() as session:
                app = await session.get(Application, application_id)
                if app is None:
                    raise ApplyError(f"Application {application_id} not found")
                now = datetime.utcnow()
                if result["success"]:
                    app.status = ApplicationStatus.APPLIED
                    app.applied_at = app.applied_at or now
                    app.submitted_at = now
                    app.confirmation = result.get("confirmation_number")
                    app.human_intervention_reason = None
                    message = "Application submitted"
                    stage = "submitted"
                else:
                    app.status = ApplicationStatus.FAILED
                    app.error_message = result.get("error", "Submission could not be verified")[:2000]
                    message = result.get("error", "Submission could not be verified")
                    stage = "failed"
                session.add(ApplicationEvent(
                    application_id=application_id,
                    event_type="confirm_submit",
                    description=message,
                    event_metadata={"success": result["success"]},
                ))
                await session.commit()

            from api.websocket import emit_application_progress
            await emit_application_progress(
                application_id, stage, message,
                status="APPLIED" if result["success"] else "FAILED",
            )
            return {
                "application_id": str(application_id),
                "submitted": result["success"],
                "confirmation_number": result.get("confirmation_number"),
                "message": message,
            }
        finally:
            await self._close_automation(parked.automation)

    async def cancel(self, application_id: int) -> Dict:
        """Cancel a running or parked apply session."""
        task = registry.running.get(application_id)
        if task and not task.done():
            task.cancel()
            registry.running.pop(application_id, None)

        parked = registry.pop_parked(application_id)
        if parked:
            await self._close_automation(parked.automation)

        async with get_session() as session:
            app = await session.get(Application, application_id)
            if app is None:
                raise ApplyError(f"Application {application_id} not found")
            if app.status == ApplicationStatus.APPLYING:
                app.status = ApplicationStatus.READY
                app.human_intervention_reason = "Apply run cancelled by user"
            session.add(ApplicationEvent(
                application_id=application_id,
                event_type="apply_cancelled",
                description="Apply run cancelled by user",
                event_metadata={},
            ))
            await session.commit()

        from api.websocket import emit_application_progress
        await emit_application_progress(
            application_id, "cancelled", "Apply run cancelled", status="READY"
        )
        return {"application_id": str(application_id), "cancelled": True}

    def status(self, application_id: int) -> Dict:
        return {
            "application_id": str(application_id),
            "running": registry.is_running(application_id),
            "parked": registry.is_parked(application_id),
            "park_ttl_minutes": registry.PARK_TTL_SECONDS // 60,
            "auto_submit_enabled": self._auto_submit_enabled(),
        }

    # ------------------------------------------------------------------
    # Background run
    # ------------------------------------------------------------------

    async def _run(self, application_id: int, mode: SubmissionMode, flow: SiteFlow):
        automation: Optional[BrowserAutomation] = None
        submission: Optional[ApplicationSubmission] = None
        try:
            async with registry.apply_semaphore:
                async with get_session() as session:
                    app = await self._load_application(application_id, session)
                    if app is None:
                        logger.error("Apply run: application %s vanished", application_id)
                        return
                    job = app.job
                    resume = app.resume
                    profile = app.candidate
                    application_url = app.application_url or ""
                    resume_path = resume.file_path if resume else None

                    # Mark APPLYING + audit event
                    app.status = ApplicationStatus.APPLYING
                    app.error_message = None
                    app.fields_remaining = []
                    session.add(ApplicationEvent(
                        application_id=application_id,
                        event_type="apply_started",
                        description=f"Auto-apply started in {mode.value} mode on {flow.name}",
                        event_metadata={"mode": mode.value, "site": flow.key},
                    ))
                    await session.commit()

                from api.websocket import emit_application_progress
                await emit_application_progress(
                    application_id, "started", f"Applying on {flow.name} ({mode.value} mode)"
                )

                # Resume file may be missing after a redeploy — materialize it.
                resume_path = await self._ensure_resume_file(resume_path, resume)
                if resume_path is None:
                    await self._finish_needs_review(
                        application_id, flow,
                        "Resume file is no longer on the server — regenerate it from the job card, then apply again.",
                        ["resume_file"],
                    )
                    return

                # For external platforms in manual mode (LinkedIn, Indeed), prepare review state
                if flow.key in ("linkedin", "indeed", "manual_external"):
                    await self._finish_needs_review(
                        application_id, flow,
                        f"Tailored resume ready for {flow.name}. Click the application link to review and submit.",
                        [],
                    )
                    return

                # Site login (JobBank needs the stored credential).
                username = password = None
                if flow.requires_login:
                    username, password = await self._load_credential(flow.key)
                    if username is None:
                        await self._finish_needs_review(
                            application_id, flow,
                            f"{flow.name} requires a login. Add your {flow.name} credentials in Settings → Credentials, then apply again.",
                            ["login_credentials"],
                        )
                        return

                headless = os.getenv("HEADLESS", "true").lower() != "false"
                automation = BrowserAutomation(BrowserConfig(headless=headless))
                await automation.start()

                if flow.requires_login:
                    await emit_application_progress(application_id, "login", f"Signing in to {flow.name}")
                    outcome = await ensure_logged_in(
                        automation, flow, username, password, base_url=application_url
                    )
                    if outcome in (LoginOutcome.LOGIN_REQUIRED_NO_CREDS, LoginOutcome.LOGIN_FAILED):
                        await self._finish_needs_review(
                            application_id, flow,
                            f"Could not sign in to {flow.name} with the stored credentials. Verify them in Settings → Credentials.",
                            ["login_credentials"],
                        )
                        return
                    if outcome == LoginOutcome.CAPTCHA:
                        await self._finish_needs_review(
                            application_id, flow,
                            f"{flow.name} showed a CAPTCHA at login. Automated solving is not supported — apply manually for this one.",
                            ["captcha"],
                        )
                        return

                await emit_application_progress(application_id, "filling", "Filling application form")

                form_profile, derived_fields = build_form_profile(profile)

                submission = ApplicationSubmission(automation=automation)
                # Replicate __aenter__ without starting a second browser.
                from browser.form_filler import FormFiller
                from browser.screening import ScreeningHandler
                submission.form_filler = FormFiller(automation)
                submission.screening_handler = ScreeningHandler(profile=form_profile)

                context = ApplicationContext(
                    job_id=app.job_id,
                    application_id=application_id,
                    apply_url=application_url,
                    profile=form_profile,
                    resume_path=resume_path,
                    mode=mode,
                    company_name=job.company if job else "",
                    job_title=job.title if job else "",
                )

                result = await submission.submit_application(context)

                if result.requires_human:
                    fields = list(result.fields_remaining)
                    for f in derived_fields:
                        fields.append(f"verify: {f}")
                    await self._finish_needs_review(
                        application_id, flow,
                        result.human_intervention_reason or "Form filled — review and confirm submit.",
                        fields,
                        park=(automation, submission, flow.submit_selectors),
                        steps=result.steps_completed,
                    )
                    return

                if result.success and mode == SubmissionMode.AUTO:
                    await self._finish_applied(application_id, flow, result)
                    return

                # Non-human failures
                error_text = "; ".join(result.errors[-3:]) or "Unknown apply failure"
                await self._finish_failed(application_id, flow, error_text, result.errors)

        except UnsupportedSiteError as e:
            await self._finish_failed(application_id, flow, str(e), [])
        except CredentialCryptoError as e:
            await self._finish_needs_review(application_id, flow, str(e), ["login_credentials"])
        except asyncio.CancelledError:
            logger.info(f"Apply run for application {application_id} cancelled")
        except Exception as e:
            logger.error(
                f"Apply run crashed for application {application_id}: {type(e).__name__}: {e}"
            )
            await self._finish_failed(application_id, flow, f"{type(e).__name__}: {e}", [])
        finally:
            registry.running.pop(application_id, None)
            # Close the browser unless the session was parked (parked
            # sessions are closed by confirm_submit/cancel).
            if automation and not registry.is_parked(application_id):
                await self._close_automation(automation)

    # ------------------------------------------------------------------
    # Outcome persistence
    # ------------------------------------------------------------------

    async def _finish_applied(self, application_id: int, flow: SiteFlow, result) -> None:
        now = datetime.utcnow()
        async with get_session() as session:
            app = await session.get(Application, application_id)
            if app:
                app.status = ApplicationStatus.APPLIED
                app.applied_at = app.applied_at or now
                app.submitted_at = now
                app.confirmation = result.confirmation_number
                app.human_intervention_reason = None
                session.add(ApplicationEvent(
                    application_id=application_id,
                    event_type="applied",
                    description=f"Submitted automatically on {flow.name}"
                    + (f" (confirmation {result.confirmation_number})" if result.confirmation_number else ""),
                    event_metadata={"mode": "auto", "steps": result.steps_completed},
                ))
                await session.commit()
        from api.websocket import emit_application_progress
        await emit_application_progress(
            application_id, "submitted", f"Application submitted on {flow.name}", status="APPLIED"
        )

    async def _finish_needs_review(
        self,
        application_id: int,
        flow: SiteFlow,
        reason: str,
        fields_remaining: List[str],
        park=None,
        steps: Optional[list] = None,
    ) -> None:
        if park:
            automation, submission, selectors = park
            registry.park(application_id, automation, submission, selectors)
            reason = f"{reason} The filled form is waiting for your review (expires in 30 minutes)."

        async with get_session() as session:
            app = await session.get(Application, application_id)
            if app:
                app.status = ApplicationStatus.NEEDS_HUMAN_INPUT
                app.human_intervention_reason = reason
                app.fields_remaining = fields_remaining
                session.add(ApplicationEvent(
                    application_id=application_id,
                    event_type="needs_human_input",
                    description=reason,
                    event_metadata={"fields_remaining": fields_remaining, "site": flow.key},
                ))
                await session.commit()
        from api.websocket import emit_application_progress
        await emit_application_progress(
            application_id,
            "review" if park else "needs_review",
            reason,
            status="NEEDS_REVIEW",
            fields_remaining=fields_remaining,
        )

    async def _finish_failed(
        self, application_id: int, flow: SiteFlow, error_text: str, errors: List[str]
    ) -> None:
        async with get_session() as session:
            app = await session.get(Application, application_id)
            if app:
                app.status = ApplicationStatus.FAILED
                app.error_message = error_text[:2000]
                app.human_intervention_reason = None
                session.add(ApplicationEvent(
                    application_id=application_id,
                    event_type="apply_failed",
                    description=error_text[:500],
                    event_metadata={"site": flow.key},
                ))
                session.add(ApplicationError(
                    application_id=application_id,
                    source=f"apply:{flow.key}",
                    error_type="apply_failure",
                    error_message=error_text[:2000],
                ))
                await session.commit()
        from api.websocket import emit_application_progress
        await emit_application_progress(
            application_id, "failed", f"Apply failed: {error_text}", status="FAILED"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_mode(self, mode: str) -> SubmissionMode:
        mode = (mode or "manual").lower().strip()
        if mode == "auto":
            return SubmissionMode.AUTO
        if mode == "dry_run":
            return SubmissionMode.DRY_RUN
        return SubmissionMode.MANUAL

    def _auto_submit_enabled(self) -> bool:
        return os.getenv("AUTO_SUBMIT", "false").lower() in ("1", "true", "yes")

    async def _load_application(self, application_id: int, session=None):
        if session is None:
            async with get_session() as own_session:
                return await self._load_application(application_id, own_session)
        # Eager-load relationships — accessing app.job/app.resume/app.candidate
        # lazily on an AsyncSession raises MissingGreenlet.
        result = await session.execute(
            select(Application)
            .options(
                selectinload(Application.job),
                selectinload(Application.resume),
                selectinload(Application.candidate),
            )
            .where(Application.id == application_id)
        )
        return result.scalars().first()

    async def _load_credential(self, site_key: str):
        """Decrypt the stored login for a site. Returns (None, None) when absent."""
        async with get_session() as session:
            result = await session.execute(
                select(SiteCredential).where(SiteCredential.site == site_key)
            )
            cred = result.scalars().first()
            if cred is None or not cred.password_encrypted:
                return None, None
            return cred.username, decrypt_secret(cred.password_encrypted)

    async def _ensure_resume_file(self, resume_path: Optional[str], resume) -> Optional[str]:
        """Disk miss (post-redeploy) → fetch from Supabase Storage or auto-synthesize from candidate profile."""
        import os, shutil
        target_path = resume_path or "data/generated_resumes/tailored_resume.docx"
        if os.path.exists(target_path):
            return target_path

        # 1. Try Supabase materialization if configured
        try:
            from storage import materialize_resume
            path = await materialize_resume(resume.id if resume else None, getattr(resume, "filename", "resume.docx"), target_path)
            if path and os.path.exists(path):
                return path
        except Exception:
            pass

        # 2. Resilient fallback: synthesize the master resume directly onto the target path
        try:
            from api.routes.resumes import _resolve_or_create_master_resume
            from database.repositories import RepositoryFactory
            async with get_session() as session:
                repos = RepositoryFactory(session)
                profile = await repos.candidates.get_profile()
                if profile:
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    master_path = await _resolve_or_create_master_resume(session, profile)
                    shutil.copy(master_path, target_path)
                    return target_path
        except Exception as e:
            logger.warning("Could not auto-synthesize missing resume file: %s", e)

        return None

    async def _click_submit(self, parked: registry.ParkedSubmission) -> Dict:
        """Find and click the real submit button on the parked page."""
        automation = parked.automation
        page = automation.page
        skip_texts = ("next", "continue", "save", "draft", "back", "previous")

        for selector in parked.submit_selectors or ["button[type='submit']"]:
            try:
                element = await page.query_selector(selector)
                if not element or not await element.is_visible():
                    continue
                text = ((await element.text_content()) or "").lower()
                if any(s in text for s in skip_texts):
                    continue
                await element.click()
                logger.info("Confirm submit: clicked %r", selector)
                break
            except Exception as e:
                logger.debug("Confirm submit selector %s failed: %s", selector, e)
        else:
            return {"success": False, "error": "Could not find the submit button on the parked page"}

        try:
            await page.wait_for_load_state(timeout=30000)
        except Exception:
            pass
        await asyncio.sleep(2)

        content = await automation.get_page_content()
        content_lower = content.lower()
        flow_success_markers = [
            "application submitted", "thank you for applying", "application received",
            "successfully submitted", "your application has been",
        ]
        if any(marker in content_lower for marker in flow_success_markers):
            # Extract from the original casing — lowercasing would mangle
            # mixed-case confirmation numbers.
            confirmation = self._extract_confirmation(content)
            return {"success": True, "confirmation_number": confirmation}
        return {"success": False, "error": "Submission could not be verified after clicking submit"}

    def _extract_confirmation(self, content: str) -> Optional[str]:
        import re
        # Strip tags first — pages wrap the number in <strong>/<span> etc.
        text = re.sub(r"<[^>]+>", " ", content)
        for pattern in (
            r"confirmation[:\s#]+([A-Za-z0-9\-]+)",
            r"reference[:\s#]+([A-Za-z0-9\-]+)",
        ):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    async def _close_automation(self, automation) -> None:
        try:
            if automation:
                await automation.close()
        except Exception:
            logger.debug("Browser close failed (ignored)", exc_info=True)


apply_service = ApplyService()
