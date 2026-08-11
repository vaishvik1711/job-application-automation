"""
Retry utilities with exponential backoff.
"""
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)
import logging

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 60,
    exceptions: tuple = (Exception,),
):
    """Decorator for async retry with exponential backoff."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
    )


def sync_retry(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 60,
    exceptions: tuple = (Exception,),
):
    """Decorator for sync retry with exponential backoff."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
    )


class RetryConfig:
    """Predefined retry configurations."""

    NETWORK = {"max_attempts": 3, "min_wait": 2, "max_wait": 30, "exceptions": (ConnectionError, TimeoutError, IOError)}
    LLM = {"max_attempts": 3, "min_wait": 2, "max_wait": 60, "exceptions": (ConnectionError, TimeoutError)}
    BROWSER = {"max_attempts": 3, "min_wait": 1, "max_wait": 10, "exceptions": (Exception,)}
    DATABASE = {"max_attempts": 3, "min_wait": 0.5, "max_wait": 5, "exceptions": (Exception,)}