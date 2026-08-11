"""
Agents package - Core agents for job automation.
"""
from agents.profile_agent import ProfileAgent, CandidateProfile, JobFilterProfile
from agents.discovery_agent import DiscoveryAgent, DiscoveryResult, create_discovery_agent
from agents.matching_agent import MatchingAgent, MatchResult, create_matching_agent

__all__ = [
    "ProfileAgent",
    "CandidateProfile",
    "JobFilterProfile",
    "DiscoveryAgent",
    "DiscoveryResult",
    "create_discovery_agent",
    "MatchingAgent",
    "MatchResult",
    "create_matching_agent",
]