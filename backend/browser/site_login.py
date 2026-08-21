"""
Login handling for auto-apply: check session state, sign in with stored
credentials when the site flow requires it.

Passwords come from the encrypted site_credentials store (security/crypto.py)
and are typed into the page but NEVER logged or included in errors.
"""
from enum import Enum
from typing import Optional

from browser.automation import BrowserAutomation
from browser.sites import SiteFlow
from utils.logger import get_logger

logger = get_logger(__name__)


class LoginOutcome(Enum):
    LOGGED_IN = "logged_in"
    LOGIN_REQUIRED_NO_CREDS = "login_required_no_creds"
    LOGIN_FAILED = "login_failed"
    CAPTCHA = "captcha"
    SKIPPED_NOT_NEEDED = "skipped_not_needed"


async def ensure_logged_in(
    automation: BrowserAutomation,
    flow: SiteFlow,
    username: Optional[str],
    password: Optional[str],
    base_url: Optional[str] = None,
) -> LoginOutcome:
    """Ensure the browser is logged in for `flow` before applying.

    Returns the outcome; callers map LOGIN_* / CAPTCHA outcomes to
    NEEDS_HUMAN_INPUT with an actionable reason.
    """
    if not flow.requires_login:
        return LoginOutcome.SKIPPED_NOT_NEEDED

    page = automation.page

    # Already signed in? (JobBank shows a sign-out link once authenticated.)
    try:
        content = await automation.get_page_content()
        content_lower = content.lower()
        if any(marker in content_lower for marker in flow.logged_in_markers):
            return LoginOutcome.LOGGED_IN
    except Exception as e:
        logger.debug("Could not read page for login-state check: %s", e)

    if not username or not password:
        logger.info("Site %s requires login but no credentials are stored", flow.key)
        return LoginOutcome.LOGIN_REQUIRED_NO_CREDS

    login_url = flow.login_url_hint
    if login_url and not login_url.startswith("http"):
        # Relative hint (mock target) — resolve against the application's
        # origin. The browser is still on about:blank here, so page.url is
        # useless as a base.
        from urllib.parse import urljoin
        base = base_url or page.url
        login_url = urljoin(base if base.startswith("http") else "https://example.com", login_url)

    if not await automation.navigate(login_url):
        return LoginOutcome.LOGIN_FAILED
    await automation.wait_random(800, 1600)

    if await automation.detect_captcha():
        logger.warning("CAPTCHA on %s login page — routing to human review", flow.key)
        return LoginOutcome.CAPTCHA

    selectors = flow.login_form_selectors
    try:
        await page.fill(selectors["username"], username, timeout=10000)
        await page.fill(selectors["password"], password, timeout=10000)
    except Exception as e:
        logger.warning("Login form fields not found on %s: %s", flow.key, e)
        return LoginOutcome.LOGIN_FAILED

    try:
        await page.click(selectors["submit"], timeout=10000)
    except Exception as e:
        logger.warning("Login submit not found on %s: %s", flow.key, e)
        return LoginOutcome.LOGIN_FAILED

    try:
        await page.wait_for_load_state(timeout=15000)
    except Exception:
        pass
    await automation.wait_random(1000, 2500)

    if await automation.detect_captcha():
        return LoginOutcome.CAPTCHA

    content = (await automation.get_page_content()).lower()
    if any(marker in content for marker in flow.logged_in_markers):
        logger.info("Logged in to %s as stored credential user", flow.key)
        return LoginOutcome.LOGGED_IN

    # Generic failure — wrong password, locked account, etc.
    logger.warning("Login to %s did not succeed after submit", flow.key)
    return LoginOutcome.LOGIN_FAILED
