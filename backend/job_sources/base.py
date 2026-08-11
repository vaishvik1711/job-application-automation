"""
Abstract base class for job sources.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class RawJob:
    """Raw job data from a source before normalization."""
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    source_job_id: Optional[str] = None
    date_posted: Optional[datetime] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "CAD"
    remote_type: str = "on_site"
    employment_type: str = "full_time"
    requirements: Optional[str] = None
    preferred_qualifications: Optional[str] = None
    skills: List[str] = None
    tools: List[str] = None
    raw_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.tools is None:
            self.tools = []
        if self.raw_data is None:
            self.raw_data = {}


class JobSource(ABC):
    """Abstract base class for job sources."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    async def search(self, filters: Dict[str, Any], limit: int = 50) -> List[RawJob]:
        """
        Search for jobs matching the given filters.

        Args:
            filters: Search filters (titles, skills, locations, etc.)
            limit: Maximum number of jobs to return

        Returns:
            List of RawJob objects
        """
        pass

    @abstractmethod
    async def get_job_details(self, job_url: str) -> Optional[RawJob]:
        """
        Get detailed job information from a job URL.

        Args:
            job_url: URL of the job posting

        Returns:
            RawJob with full details or None if not found
        """
        pass

    def normalize_location(self, location: str) -> str:
        """Normalize location string."""
        if not location:
            return "Unknown"
        # Basic normalization
        location = location.strip()
        # Add more normalization logic here
        return location

    def normalize_remote_type(self, remote_str: str) -> str:
        """Normalize remote type string."""
        if not remote_str:
            return "on_site"
        remote_lower = remote_str.lower()
        if "remote" in remote_lower:
            return "remote"
        elif "hybrid" in remote_lower:
            return "hybrid"
        else:
            return "on_site"

    def normalize_employment_type(self, emp_type: str) -> str:
        """Normalize employment type string."""
        if not emp_type:
            return "full_time"
        emp_lower = emp_type.lower()
        if "contract" in emp_lower:
            return "contract"
        elif "part" in emp_lower:
            return "part_time"
        elif "intern" in emp_lower:
            return "internship"
        elif "temp" in emp_lower:
            return "temporary"
        else:
            return "full_time"