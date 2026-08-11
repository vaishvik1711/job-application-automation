"""
Browser automation package for job application submission.
"""
from browser.automation import BrowserAutomation
from browser.form_filler import FormFiller
from browser.screening import ScreeningHandler

__all__ = [
    "BrowserAutomation",
    "FormFiller",
    "ScreeningHandler",
]