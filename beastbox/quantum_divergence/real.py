from __future__ import annotations

"""Stable public aliases for the real IBM quantum-divergence path.

The implementation remains in :mod:`beastbox.quantum_divergence.ibm_live` so
existing callers are unchanged. This module only exposes clearer public names
for the hardware entropy circuit used by the Zeref A/B experiment.
"""

from .ibm_live import (
    build_entropy_circuit,
    retrieve_real_entropy,
    submit_real_entropy,
)


def build_hardware_entropy_circuit(width: int = 12):
    return build_entropy_circuit(width)


__all__ = [
    "build_hardware_entropy_circuit",
    "retrieve_real_entropy",
    "submit_real_entropy",
]
