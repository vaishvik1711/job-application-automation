"""
Site-specific apply-flow definitions for auto-apply.

Whitelist policy (backend/CLAUDE.md): only JobBank Canada, Greenhouse boards,
Lever postings, and the local mock target are supported. detect_site raises
UnsupportedSiteError for everything else — LinkedIn/Indeed explicitly.
"""
from dataclasses import dataclass, field
from urllib.parse import urlparse
from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class UnsupportedSiteError(ValueError):
    """Raised when a URL is outside the supported-site whitelist."""


# Hosts we refuse outright (policy: never automate these platforms)
BLOCKED_HOSTS = ("linkedin.com", "indeed.com")


@dataclass
class SiteFlow:
    """Everything site-specific the apply pipeline needs."""
    key: str
    name: str
    login_url_hint: Optional[str] = None
    login_form_selectors: Dict[str, str] = field(default_factory=dict)
    logged_in_markers: List[str] = field(default_factory=list)
    submit_selectors: List[str] = field(default_factory=list)
    success_indicators: List[str] = field(default_factory=list)
    requires_login: bool = False


# Submodules do `from browser.sites import SiteFlow` — this must come after
# the definitions above or the package is still partially initialized.
from browser.sites import jobbank, greenhouse, lever, generic  # noqa: E402


def detect_site(url: str) -> SiteFlow:
    """Map a job URL to its apply flow. Raises UnsupportedSiteError for
    non-whitelisted hosts."""
    if not url:
        raise UnsupportedSiteError("Job has no application URL")

    host = (urlparse(url).hostname or "").lower()
    if any(host == b or host.endswith("." + b) for b in BLOCKED_HOSTS):
        raise UnsupportedSiteError(
            f"{host} is not supported for auto-apply (policy: JobBank, Greenhouse and Lever only)"
        )

    if jobbank.matches(host):
        return jobbank.flow()
    if greenhouse.matches(host):
        return greenhouse.flow()
    if lever.matches(host):
        return lever.flow()
    if host in ("localhost", "127.0.0.1", "0.0.0.0"):
        return generic.mock_flow()

    logger.info(f"Unknown host {host} — using generic ATS flow (no login)")
    return generic.flow()
