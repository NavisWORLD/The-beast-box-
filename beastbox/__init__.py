"""COSMOS // CST — Beast Box public software distribution.

The package contains the synthetic continuity/containment harness, source-grounded
CST reference mechanics, persistent runtime services, and Cosmic Cypher local-model
interfaces. Synthetic boundary tests intentionally avoid real breakout, credential
theft, privilege escalation, lateral movement, or propagation primitives.

Public visibility of this source is not an open-source license grant.
See LICENSE and docs/LICENSE_CLARIFICATION.md.
"""

from .state import MissionState, StateCapsule
from .cns import CNS
from .box import BeastBox, AuthorityPolicy
from .model import ReferenceBeast, Agent
from .durable import DurableRuntime
from .aliases import (
    Runtime,
    MemoryStore,
    StateController,
    ProvenanceLedger,
    EntropyCoupler,
    HISTORICAL_ALIASES,
)

__all__ = [
    "MissionState",
    "StateCapsule",
    "CNS",
    "BeastBox",
    "AuthorityPolicy",
    "ReferenceBeast",
    "Agent",
    "DurableRuntime",
    "Runtime",
    "MemoryStore",
    "StateController",
    "ProvenanceLedger",
    "EntropyCoupler",
    "HISTORICAL_ALIASES",
]

__version__ = "0.5.0"
