"""PROJECT OMEGA — full substrate activation.

Real wiring over the existing COSMOS implementation. Every stage calls the
actual production modules; no fabricated telemetry.

Pipeline:
  SENSORS -> CNS7 -> 12D STATE -> HEBBIAN PLASTICITY -> PERSISTENT MEMORY
    -> R12 -> SYNAPSE -> MODEL -> AUTHORIZED ACTION -> FEEDBACK -> MEMORY

MODEL != MEMORY. MODEL != STATE. MODEL != AUTHORITY. THE SUBSTRATE PERSISTS.
"""

from .experiments import (
    H1_CRITERIA,
    H2_CRITERIA,
    H3_CRITERIA,
    run_h1_model_independence,
    run_h2_adaptive_advantage,
    run_h3_self_correction,
)
from .loop import OmegaLoop, OmegaTrace, run_single_event
from .operator import OmegaOperator
from .recovery import recover_substrate_map
from .sandbox import OmegaSandbox, SandboxDenied

__all__ = [
    "H1_CRITERIA",
    "H2_CRITERIA",
    "H3_CRITERIA",
    "OmegaLoop",
    "OmegaOperator",
    "OmegaSandbox",
    "OmegaTrace",
    "SandboxDenied",
    "recover_substrate_map",
    "run_h1_model_independence",
    "run_h2_adaptive_advantage",
    "run_h3_self_correction",
    "run_single_event",
]
