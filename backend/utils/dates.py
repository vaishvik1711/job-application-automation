"""
Date utilities for parsing and formatting.
"""
from datetime import datetime, date, timedelta
from dateutil import parser as dateutil_parser
from typing import Optional, Union
import re


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats."""
    if not date_str:
        return None
    try:
        return dateutil_parser.parse(date_str)
    except (ValueError, TypeError):
        return None


def parse_date_flexible(date_str: str) -> Optional[date]:
    """Parse date string to date object."""
    dt = parse_date(date_str)
    return dt.date() if dt else None


def format_date(dt: Union[datetime, date], fmt: str = "%Y-%m-%d") -> str:
    """Format date/datetime to string."""
    if isinstance(dt, datetime):
        return dt.strftime(fmt)
    return dt.strftime(fmt)


def days_ago(dt: Union[datetime, date]) -> int:
    """Calculate days between date and today."""
    if isinstance(dt, datetime):
        dt = dt.date()
    return (date.today() - dt).days


def is_recent(dt: Union[datetime, date], days: int = 30) -> bool:
    """Check if date is within recent days."""
    return days_ago(dt) <= days


def parse_relative_date(text: str) -> Optional[date]:
    """Parse relative dates like '2 days ago', '1 week ago', 'Posted 3 days ago'."""
    text = text.lower().strip()

    patterns = [
        (r"(\d+)\s*day", 1),
        (r"(\d+)\s*week", 7),
        (r"(\d+)\s*month", 30),
        (r"(\d+)\s*hour", 1/24),
        (r"just posted", 0),
        (r"today", 0),
        (r"yesterday", 1),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, text)
        if match:
            if pattern in ("just posted", "today"):
                return date.today()
            if pattern == "yesterday":
                return date.today() - timedelta(days=1)
            try:
                value = int(match.group(1))
                days = value * multiplier
                return date.today() - timedelta(days=int(days))
            except (ValueError, IndexError):
                continue

    return None


def get_date_range(days_back: int = 30) -> tuple[date, date]:
    """Get date range for queries."""
    end = date.today()
    start = end - timedelta(days=days_back)
    return start, end