"""JobBank Canada (Job Bank) flow definition."""
from typing import Optional

from browser.sites import SiteFlow


def matches(host: str) -> bool:
    return host in ("jobbank.gc.ca", "www.jobbank.gc.ca")


def flow() -> SiteFlow:
    return SiteFlow(
        key="jobbank",
        name="JobBank Canada",
        login_url_hint="https://www.jobbank.gc.ca/login",
        login_form_selectors={
            "username": "input[name='username'], input#username, input[type='email']",
            "password": "input[name='password'], input#password, input[type='password']",
            "submit": "button[type='submit'], input[type='submit']",
        },
        logged_in_markers=["sign out", "log out", "my account", "déconnexion"],
        submit_selectors=[
            "button:has-text('Submit application')",
            "button:has-text('Submit')",
            "input[value='Submit']",
            "button[type='submit']",
        ],
        success_indicators=[
            "application has been submitted",
            "thank you for applying",
            "successfully submitted",
        ],
        requires_login=True,
    )
