"""
Hashing utilities for deduplication and content identification.
"""
import hashlib
import json
from typing import Any


def content_hash(data: Any) -> str:
    """Generate a deterministic SHA256 hash of content."""
    if isinstance(data, (dict, list)):
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=True)
    else:
        serialized = str(data)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def short_hash(data: Any, length: int = 16) -> str:
    """Generate a short hash for display."""
    return content_hash(data)[:length]


def job_fingerprint(company: str, title: str, location: str, description: str = "") -> str:
    """Generate a fingerprint for job deduplication."""
    normalized = f"{company.lower().strip()}|{title.lower().strip()}|{location.lower().strip()}"
    if description:
        # Use first 500 chars of description for similarity
        normalized += f"|{description.lower().strip()[:500]}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def similarity_hash(text: str) -> str:
    """Generate a hash for text similarity comparison."""
    # Normalize: lowercase, remove extra whitespace, remove punctuation
    import re
    normalized = re.sub(r"[^\w\s]", "", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()