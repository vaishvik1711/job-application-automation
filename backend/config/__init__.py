"""
Configuration loader for YAML settings with environment variable support.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict
from functools import lru_cache


@lru_cache(maxsize=1)
def load_settings(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """Load settings from YAML file and merge with environment variables."""
    path = Path(config_path)
    if not path.exists():
        return {}

    with open(path, "r") as f:
        settings = yaml.safe_load(f) or {}

    # Merge environment variables for ATS API keys
    settings = _merge_env_vars(settings)

    return settings


def _merge_env_vars(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Merge environment variables into settings for job sources."""
    import copy
    settings = copy.deepcopy(settings)

    job_sources = settings.get("job_sources", {})

    # Greenhouse
    if "greenhouse" in job_sources:
        greenhouse_key = os.getenv("GREENHOUSE_API_KEY")
        if greenhouse_key:
            job_sources["greenhouse"]["api_key"] = greenhouse_key

    # Lever
    if "lever" in job_sources:
        lever_key = os.getenv("LEVER_API_KEY")
        if lever_key:
            job_sources["lever"]["api_key"] = lever_key

    # Workday
    if "workday" in job_sources:
        workday_key = os.getenv("WORKDAY_API_KEY")
        if workday_key:
            job_sources["workday"]["api_key"] = workday_key

    # iCIMS
    if "icims" in job_sources:
        icims_key = os.getenv("ICIMS_API_KEY")
        if icims_key:
            job_sources["icims"]["api_key"] = icims_key

    # SmartRecruiters
    if "smartrecruiters" in job_sources:
        sr_key = os.getenv("SMARTRECRUITERS_API_KEY")
        if sr_key:
            job_sources["smartrecruiters"]["api_key"] = sr_key

    settings["job_sources"] = job_sources
    return settings


def get_setting(key: str, default: Any = None) -> Any:
    """Get a nested setting value using dot notation."""
    settings = load_settings()
    keys = key.split(".")
    value = settings
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
        if value is None:
            return default
    return value


def load_job_filters(config_path: str = "config/job_filters.yaml") -> Dict[str, Any]:
    """Load job filters from YAML file."""
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def load_application_rules(config_path: str = "config/application_rules.yaml") -> Dict[str, Any]:
    """Load application rules from YAML file."""
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}