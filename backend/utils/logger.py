"""
Structured logging configuration.
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/application.log",
    error_file: str = "logs/errors.log",
    browser_file: str = "logs/browser.log",
    llm_file: str = "logs/llm.log",
) -> None:
    """Configure structured logging with multiple handlers."""

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    structured_formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(console_handler)

    # Main application log (rotating)
    app_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(structured_formatter)
    root_logger.addHandler(app_handler)

    # Error log (only errors)
    error_handler = logging.handlers.RotatingFileHandler(
        error_file, maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(structured_formatter)
    root_logger.addHandler(error_handler)

    # Browser log
    browser_logger = logging.getLogger("browser")
    browser_handler = logging.handlers.RotatingFileHandler(
        browser_file, maxBytes=10_000_000, backupCount=3, encoding="utf-8"
    )
    browser_handler.setLevel(logging.DEBUG)
    browser_handler.setFormatter(structured_formatter)
    browser_logger.addHandler(browser_handler)
    browser_logger.propagate = False

    # LLM log
    llm_logger = logging.getLogger("llm")
    llm_handler = logging.handlers.RotatingFileHandler(
        llm_file, maxBytes=10_000_000, backupCount=3, encoding="utf-8"
    )
    llm_handler.setLevel(logging.DEBUG)
    llm_handler.setFormatter(structured_formatter)
    llm_logger.addHandler(llm_handler)
    llm_logger.propagate = False


class StructuredLogger:
    """Wrapper for structured logging with context."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(self, level: int, message: str, *args, **kwargs):
        # Support stdlib-style lazy formatting: logger.info("x %s", val).
        if args:
            try:
                message = message % args
            except (TypeError, ValueError):
                pass  # never let a bad format string crash the caller
        extra = {k: v for k, v in kwargs.items() if v is not None}
        self.logger.log(level, message, extra=extra)

    def info(self, message: str, *args, **kwargs):
        self._log(logging.INFO, message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        self._log(logging.DEBUG, message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._log(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self._log(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self._log(logging.CRITICAL, message, *args, **kwargs)

    def log_action(self, agent: str, job_id: Optional[int], action: str, status: str, **kwargs):
        """Log a structured action."""
        self.info(
            f"{agent} | {action} | {status}",
            agent=agent,
            job_id=job_id,
            action=action,
            status=status,
            **kwargs,
        )


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)