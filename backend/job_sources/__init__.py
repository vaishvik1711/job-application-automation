"""
Job Sources package - All job source implementations.
"""
from typing import List
from job_sources.base import JobSource, RawJob
from job_sources.ats_base import ATSSource
from job_sources.jobbank import JobBankSource, create_jobbank_source
from job_sources.greenhouse import GreenhouseSource, create_greenhouse_source
from job_sources.lever import LeverSource, create_lever_source
from job_sources.workday import WorkdaySource, create_workday_source
from job_sources.icims import ICIMSSource, create_icims_source
from job_sources.smartrecruiters import SmartRecruitersSource, create_smartrecruiters_source
from job_sources.jobspy_source import JobSpySource, create_jobspy_source
from job_sources.linkedin import LinkedInSource, create_linkedin_source

__all__ = [
    "JobSource",
    "RawJob",
    "ATSSource",
    "JobBankSource",
    "create_jobbank_source",
    "GreenhouseSource",
    "create_greenhouse_source",
    "LeverSource",
    "create_lever_source",
    "WorkdaySource",
    "create_workday_source",
    "ICIMSSource",
    "create_icims_source",
    "SmartRecruitersSource",
    "create_smartrecruiters_source",
    "JobSpySource",
    "create_jobspy_source",
    "LinkedInSource",
    "create_linkedin_source",
]

# Source registry for dynamic loading
SOURCE_REGISTRY = {
    "jobbank": (JobBankSource, create_jobbank_source),
    "greenhouse": (GreenhouseSource, create_greenhouse_source),
    "lever": (LeverSource, create_lever_source),
    "workday": (WorkdaySource, create_workday_source),
    "icims": (ICIMSSource, create_icims_source),
    "smartrecruiters": (SmartRecruitersSource, create_smartrecruiters_source),
    "jobspy": (JobSpySource, create_jobspy_source),
    "linkedin": (LinkedInSource, create_linkedin_source),
}


def get_source_class(source_name: str):
    """Get source class by name."""
    if source_name in SOURCE_REGISTRY:
        return SOURCE_REGISTRY[source_name][0]
    raise ValueError(f"Unknown source: {source_name}")


def get_source_factory(source_name: str):
    """Get source factory function by name."""
    if source_name in SOURCE_REGISTRY:
        return SOURCE_REGISTRY[source_name][1]
    raise ValueError(f"Unknown source: {source_name}")


def list_sources() -> List[str]:
    """List available source names."""
    return list(SOURCE_REGISTRY.keys())