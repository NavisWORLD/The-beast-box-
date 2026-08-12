"""COSMOS // NOVA — Beast Box public reference harness.

This package intentionally tests continuity and containment without providing
real breakout, persistence, credential theft, or privilege-escalation paths.
"""

from .state import MissionState, StateCapsule
from .cns import CNS
from .box import BeastBox, AuthorityPolicy
from .model import ReferenceBeast, Agent

__all__ = [
    "MissionState",
    "StateCapsule",
    "CNS",
    "BeastBox",
    "AuthorityPolicy",
    "ReferenceBeast",
    "Agent",
]

__version__ = "0.1.0"
