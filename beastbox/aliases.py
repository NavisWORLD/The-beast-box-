"""Technical public aliases for historical experiment names.

Historical identifiers (Zeref, Quantum Heart, Soul, Dad/Son) remain valid
experiment IDs. This module exposes descriptive names for the public API
without renaming immutable evidence or breaking existing imports.
"""
from __future__ import annotations

from .cns import CNS as StateController
from .evidence import EvidenceLedger as ProvenanceLedger
from .heartbeat import Heartbeat
from .memory import ReconciliationMemory as MemoryStore
from .quantum_heart import QuantumHeart as EntropyCoupler
from .runtime import CosmosRuntime as Runtime

# Historical experiment / lineage identifiers. Do not treat as scientific claims.
HISTORICAL_ALIASES = {
    "Zeref": "model_lineage / reference_model checkpoint family",
    "R12": "refractive retrieval / reality-memory routing expansion",
    "Quantum Heart": "optional entropy_source coupler (default OFF)",
    "Soul / QBT": "experimental token-bus loop kit; not a measured soul",
    "Dad/Son": "supervised teacher-student conversation experiment family",
    "CNS": "seven-role software state_controller",
}

__all__ = [
    "EntropyCoupler",
    "HISTORICAL_ALIASES",
    "Heartbeat",
    "MemoryStore",
    "ProvenanceLedger",
    "Runtime",
    "StateController",
]
