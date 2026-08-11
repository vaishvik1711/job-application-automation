"""
Helper utilities for common operations.
"""
import re
from datetime import datetime
from typing import Optional
from decimal import Decimal


def format_currency(amount: Optional[int], currency: str = "CAD") -> str:
    """Format currency amount."""
    if amount is None:
        return ""
    if amount >= 1000000:
        return f"${amount/1000000:.1f}M {currency}"
    elif amount >= 1000:
        return f"${amount/1000:.0f}K {currency}"
    return f"${amount:,} {currency}"


def parse_date_flexible(date_str: str) -> Optional[datetime]:
    """Parse date from various formats."""
    if not date_str:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    # Try to extract year-month-day with regex
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", date_str)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    return None


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace and normalizing."""
    if not text:
        return ""
    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def extract_years_experience(text: str) -> Optional[int]:
    """Extract years of experience from text."""
    if not text:
        return None

    patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s*)?experience",
        r"(\d+)\+?\s*yrs?\s*(?:of\s*)?experience",
        r"experience\s*(?:of\s*)?(\d+)\+?\s*years?",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def normalize_skill_name(skill: str) -> str:
    """Normalize skill name for comparison."""
    if not skill:
        return ""
    # Lowercase and remove special chars except +, #, .
    skill = skill.lower().strip()
    skill = re.sub(r"[^a-z0-9+#.\-\s]", "", skill)
    # Collapse whitespace
    skill = re.sub(r"\s+", " ", skill)
    return skill.strip()


def skill_match(skill1: str, skill2: str, threshold: float = 0.8) -> bool:
    """Check if two skills match using simple string comparison."""
    s1 = normalize_skill_name(skill1)
    s2 = normalize_skill_name(skill2)

    if s1 == s2:
        return True

    # Check if one contains the other
    if s1 in s2 or s2 in s1:
        return True

    return False