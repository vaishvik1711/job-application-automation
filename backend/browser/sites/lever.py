"""Lever-hosted job posting flow definition."""
from browser.sites import SiteFlow


def matches(host: str) -> bool:
    return host.endswith("lever.co") or host.endswith(".lever.co")


def flow() -> SiteFlow:
    return SiteFlow(
        key="lever",
        name="Lever",
        requires_login=False,
        submit_selectors=[
            "button:has-text('Submit Application')",
            "button:has-text('Submit application')",
            "input[value='Submit Application']",
            "button[type='submit']",
        ],
        success_indicators=[
            "application submitted",
            "thank you for applying",
            "we received your application",
        ],
    )
