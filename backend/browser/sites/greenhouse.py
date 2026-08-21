"""Greenhouse-hosted job board flow definition."""
from browser.sites import SiteFlow


def matches(host: str) -> bool:
    return host.endswith("greenhouse.io") or host.endswith(".greenhouse.io")


def flow() -> SiteFlow:
    return SiteFlow(
        key="greenhouse",
        name="Greenhouse",
        # Public Greenhouse boards rarely require login; the application form
        # is inline on the job page.
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
            "your application has been received",
        ],
    )
