"""Generic ATS flow — unknown hosts and the local mock apply target."""
from browser.sites import SiteFlow


def matches(host: str) -> bool:
    return False  # only reached explicitly from detect_site


def flow() -> SiteFlow:
    return SiteFlow(
        key="generic",
        name="Generic ATS",
        requires_login=False,
        submit_selectors=[
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Apply')",
        ],
        success_indicators=[
            "application submitted",
            "thank you for applying",
            "application received",
            "successfully submitted",
        ],
    )


def mock_flow() -> SiteFlow:
    """The env-gated local mock apply target (ENABLE_MOCK_APPLY_TARGET=1).
    Includes a login form so credential storage can be E2E-tested."""
    f = flow()
    f.key = "mock"
    f.name = "Mock Apply Target"
    f.requires_login = True
    f.login_url_hint = "/mock-apply/login"
    f.login_form_selectors = {
        "username": "input[name='username']",
        "password": "input[name='password']",
        "submit": "button#login-submit",
    }
    f.logged_in_markers = ["logged in as"]
    return f
