"""
Application submission logic for Phase 7.
Handles the complete application flow with human intervention support.
"""
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from enum import Enum

from browser.automation import BrowserAutomation, BrowserConfig, ApplicationResult
from browser.form_filler import FormFiller, FormFillResult
from browser.screening import ScreeningHandler, ScreeningQuestion
from config import load_application_rules
from database.repositories import RepositoryFactory
from database import get_session
from utils.logger import get_logger
from utils.helpers import clean_text

logger = get_logger(__name__)


class SubmissionMode(Enum):
    """Application submission modes."""
    MANUAL = "manual"           # Stop before submit, human clicks
    AUTO = "auto"              # Auto-submit
    DRY_RUN = "dry_run"        # Fill form but don't submit


@dataclass
class ApplicationContext:
    """Context for an application attempt."""
    job_id: int
    application_id: Optional[int] = None
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    mode: SubmissionMode = SubmissionMode.MANUAL
    profile: Optional[Dict[str, Any]] = None
    company_name: str = ""
    job_title: str = ""
    apply_url: str = ""


@dataclass
class SubmissionResult:
    """Result of application submission."""
    success: bool
    job_id: int
    application_id: Optional[int] = None
    mode: SubmissionMode = SubmissionMode.MANUAL
    steps_completed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    fields_remaining: List[str] = field(default_factory=list)
    requires_human: bool = False
    human_intervention_reason: Optional[str] = None
    submitted_at: Optional[datetime] = None
    confirmation_number: Optional[str] = None


class ApplicationSubmission:
    """
    Handles the complete job application submission process.
    Supports manual, auto, and dry-run modes.
    """

    def __init__(
        self,
        automation: Optional[BrowserAutomation] = None,
        config: Optional[BrowserConfig] = None,
    ):
        self.automation = automation
        self.config = config or BrowserConfig()
        self.form_filler: Optional[FormFiller] = None
        self.screening_handler: Optional[ScreeningHandler] = None
        self._own_browser = automation is None

    async def __aenter__(self) -> "ApplicationSubmission":
        if self._own_browser:
            self.automation = BrowserAutomation(self.config)
            await self.automation.start()

        self.form_filler = FormFiller(self.automation)
        self.screening_handler = ScreeningHandler()  # Profile set per application
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._own_browser and self.automation:
            await self.automation.close()

    async def submit_application(self, context: ApplicationContext) -> SubmissionResult:
        """Submit a job application."""
        result = SubmissionResult(
            success=False,
            job_id=context.job_id,
            mode=context.mode,
        )

        try:
            # Navigate to application URL
            if not await self._navigate_to_application(context, result):
                return result

            # Update profile in screening handler
            if context.profile:
                self.screening_handler.profile = context.profile

            # Handle popups
            await self.automation.handle_popups()

            # Fill personal information
            if not await self._fill_personal_info(context, result):
                return result

            # Upload resume
            if not await self._upload_resume(context, result):
                return result

            # Handle screening questions
            if not await self._handle_screening_questions(context, result):
                return result

            # Review page (if applicable)
            await self._handle_review_page(context, result)

            # Submit or stop based on mode
            if context.mode == SubmissionMode.DRY_RUN:
                await self._take_screenshot(context, result, "review_parked")
                result.success = True
                result.steps_completed.append("dry_run_complete")
                result.requires_human = True
                result.human_intervention_reason = "Dry run mode - form filled but not submitted"
                return result

            elif context.mode == SubmissionMode.MANUAL:
                # Capture the parked form so the reviewer can see what the
                # bot filled before deciding to submit.
                await self._take_screenshot(context, result, "review_parked")
                result.success = True
                result.steps_completed.append("form_filled_ready_to_submit")
                result.requires_human = True
                result.human_intervention_reason = "Manual mode - review and click submit"
                return result

            else:  # AUTO mode
                return await self._submit_form(context, result)

        except Exception as e:
            logger.error(f"Application submission failed: {e}")
            result.errors.append(str(e))
            await self._take_error_screenshot(context, result)
            return result

    async def _navigate_to_application(self, context: ApplicationContext, result: SubmissionResult) -> bool:
        """Navigate to the application page."""
        if not context.apply_url:
            result.errors.append("No application URL provided")
            return False

        logger.info(f"Navigating to application: {context.apply_url}")
        success = await self.automation.navigate(context.apply_url)

        if not success:
            result.errors.append("Failed to navigate to application page")
            return False

        result.steps_completed.append("navigated")
        await self.automation.wait_random(1000, 3000)
        return True

    async def _fill_personal_info(self, context: ApplicationContext, result: SubmissionResult) -> bool:
        """Fill personal information form."""
        if not context.profile:
            result.errors.append("No profile data provided")
            return False

        logger.info("Filling personal information")
        fill_result = await self.form_filler.fill_form(
            profile=context.profile,
            resume_path=context.resume_path,
            cover_letter_path=context.cover_letter_path,
        )

        if fill_result.fields_filled == 0:
            # Try smart fill
            logger.info("Trying smart fill...")
            fill_result = await self.form_filler.smart_fill(
                profile=context.profile,
                resume_path=context.resume_path,
            )

        if fill_result.fields_filled > 0:
            result.steps_completed.append(f"filled_{fill_result.fields_filled}_fields")
        else:
            result.errors.append("No fields could be filled")
            return False

        if fill_result.errors:
            result.errors.extend(fill_result.errors)

        # Surface any fields the filler could not complete so the reviewer
        # knows what to check before confirming submit.
        if fill_result.fields_failed:
            result.fields_remaining.extend(
                f"field: {name}" for name in fill_result.fields_failed
            )

        return True

    async def _upload_resume(self, context: ApplicationContext, result: SubmissionResult) -> bool:
        """Upload resume if not already done."""
        if not context.resume_path:
            return True

        path = Path(context.resume_path)
        if not path.exists():
            result.errors.append(f"Resume not found: {context.resume_path}")
            return False

        # Check if resume was already uploaded
        if "resume_file" in [f for f in result.steps_completed if "field" in f]:
            return True

        # Try to find and upload
        logger.info("Uploading resume...")
        upload_result = FormFillResult(success=False, fields_filled=0)
        try:
            await self.form_filler._upload_file("resume_file", context.resume_path, upload_result)
        except Exception as e:
            upload_result.errors.append(f"resume upload failed: {e}")

        if upload_result.fields_filled > 0:
            result.steps_completed.append("resume_uploaded")
        else:
            # Missing resume upload is not fatal — many ATS forms are optional —
            # but it must surface to the human reviewer.
            result.errors.extend(upload_result.errors or ["resume upload field not found"])
            result.fields_remaining.append("resume_upload")
            result.steps_completed.append("resume_upload_skipped")
        return True

    async def _handle_screening_questions(self, context: ApplicationContext, result: SubmissionResult) -> bool:
        """Handle screening questions."""
        logger.info("Detecting screening questions...")

        # Get page content
        content = await self.automation.get_page_content()

        # Detect questions
        questions = self.screening_handler.detect_questions(content)

        if not questions:
            logger.info("No screening questions detected")
            return True

        logger.info(f"Found {len(questions)} screening questions")

        # Answer questions
        answers = await self.screening_handler.answer_questions(questions)

        # Enforce the configured auto-answer confidence threshold — answers
        # below it are parked for the human reviewer instead of submitted.
        try:
            threshold = float(
                load_application_rules()
                .get("application_rules", {})
                .get("screening", {})
                .get("auto_answer_threshold", 0.9)
            )
        except Exception:
            threshold = 0.9
        for ans in answers:
            if not ans.needs_human and getattr(ans, "confidence", 1.0) is not None:
                if float(ans.confidence) < threshold:
                    ans.needs_human = True

        # Check for human-required questions
        human_required = [a for a in answers if a.needs_human]
        if human_required:
            result.requires_human = True
            result.human_intervention_reason = f"{len(human_required)} questions need human review"
            result.fields_remaining.extend(
                f"question: {ans.question.question_text[:80]}" for ans in human_required
            )
            for ans in human_required:
                result.errors.append(f"Human needed: {ans.question.question_text[:100]}")

        # Fill answers
        fill_results = await self.screening_handler.fill_answers(self.automation, answers)

        filled_count = sum(1 for v in fill_results.values() if v)
        result.steps_completed.append(f"answered_{filled_count}_screening_questions")

        # Take screenshot after screening
        await self._take_screenshot(context, result, "after_screening")

        return True

    async def _handle_review_page(self, context: ApplicationContext, result: SubmissionResult) -> bool:
        """Handle review/confirmation page if present."""
        # Check for review page indicators
        review_indicators = [
            "review your application",
            "confirm your application",
            "check your details",
            "summary",
            "review and submit",
        ]

        content = await self.automation.get_page_content()
        content_lower = content.lower()

        for indicator in review_indicators:
            if indicator in content_lower:
                logger.info("Review page detected")
                result.steps_completed.append("review_page_detected")
                await self._take_screenshot(context, result, "review_page")
                await self.automation.wait_random(1000, 2000)
                return True

        return True

    async def _submit_form(self, context: ApplicationContext, result: SubmissionResult) -> SubmissionResult:
        """Submit the application form."""
        logger.info("Submitting application...")

        # Find submit button
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Apply')",
            "button:has-text('Send')",
            "button:has-text('Submit Application')",
            "button:has-text('Complete Application')",
            "[data-testid*='submit']",
            ".submit-button",
            "#submit",
        ]

        submitted = False
        for selector in submit_selectors:
            try:
                element = await self.automation.page.query_selector(selector)
                if element and await element.is_visible():
                    # Check if it's a real submit button (not a "next" button)
                    text = await element.text_content()
                    text_lower = text.lower() if text else ""

                    skip_texts = ["next", "continue", "save", "draft", "back", "previous"]
                    if any(skip in text_lower for skip in skip_texts):
                        continue

                    await element.click()
                    submitted = True
                    result.steps_completed.append(f"clicked_submit_{selector}")
                    break
            except Exception as e:
                logger.debug(f"Submit selector {selector} failed: {e}")
                continue

        if not submitted:
            result.errors.append("Could not find submit button")
            result.requires_human = True
            result.human_intervention_reason = "Submit button not found"
            return result

        # Wait for submission to complete
        await self.automation.wait_for_navigation(30000)

        # Check for success indicators
        success = await self._verify_submission(result)

        if success:
            result.success = True
            result.submitted_at = datetime.utcnow()
            result.steps_completed.append("submitted_successfully")

            # Try to get confirmation number
            result.confirmation_number = await self._extract_confirmation_number()
        else:
            result.errors.append("Submission verification failed")
            result.requires_human = True
            result.human_intervention_reason = "Could not verify submission"

        await self._take_screenshot(context, result, "after_submit")
        return result

    async def _verify_submission(self, result: SubmissionResult) -> bool:
        """Verify that submission was successful."""
        await self.automation.wait_random(2000, 5000)

        success_indicators = [
            "application submitted",
            "thank you for applying",
            "application received",
            "successfully submitted",
            "confirmation",
            "your application has been",
            "we have received",
            "submitted successfully",
        ]

        error_indicators = [
            "error",
            "failed",
            "try again",
            "something went wrong",
            "unable to submit",
        ]

        content = await self.automation.get_page_content()
        content_lower = content.lower()

        for error in error_indicators:
            if error in content_lower:
                return False

        for success in success_indicators:
            if success in content_lower:
                return True

        # Check URL for success
        url = self.automation.page.url
        if any(s in url.lower() for s in ["success", "confirm", "thank", "complete"]):
            return True

        return False

    async def _extract_confirmation_number(self) -> Optional[str]:
        """Extract confirmation number from page."""
        import re
        patterns = [
            r"confirmation[:\s#]+([A-Za-z0-9\-]+)",
            r"reference[:\s#]+([A-Za-z0-9\-]+)",
            r"application[:\s#]+([A-Za-z0-9\-]+)",
            r"id[:\s#]+([A-Za-z0-9\-]+)",
        ]

        content = await self.automation.get_page_content()
        # Strip tags first — pages wrap the number in <strong>/<span> etc.
        text = re.sub(r"<[^>]+>", " ", content)
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    async def _take_screenshot(self, context: ApplicationContext, result: SubmissionResult, suffix: str):
        """Take a screenshot for documentation."""
        try:
            screenshots_dir = Path("output/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            filename = f"job_{context.job_id}_{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path = screenshots_dir / filename

            if await self.automation.take_screenshot(str(path)):
                result.screenshots.append(str(path))
        except Exception as e:
            logger.debug(f"Screenshot failed: {e}")

    async def _take_error_screenshot(self, context: ApplicationContext, result: SubmissionResult):
        """Take screenshot on error."""
        await self._take_screenshot(context, result, "error")


async def submit_application(
    job_id: int,
    apply_url: str,
    profile: Dict[str, Any],
    resume_path: str,
    cover_letter_path: Optional[str] = None,
    mode: SubmissionMode = SubmissionMode.MANUAL,
    config: Optional[BrowserConfig] = None,
) -> SubmissionResult:
    """Convenience function to submit a single application."""
    context = ApplicationContext(
        job_id=job_id,
        apply_url=apply_url,
        profile=profile,
        resume_path=resume_path,
        cover_letter_path=cover_letter_path,
        mode=mode,
    )

    async with ApplicationSubmission(config=config) as submission:
        return await submission.submit_application(context)