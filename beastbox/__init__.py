"""COSMOS // CST — Beast Box public software distribution.

The package contains the synthetic continuity/containment harness, source-grounded
CST reference mechanics, persistent runtime services, and Cosmic Cypher local-model
interfaces. Synthetic boundary tests intentionally avoid real breakout, credential
theft, privilege escalation, lateral movement, or propagation primitives.
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

__version__ = "0.3.0"
