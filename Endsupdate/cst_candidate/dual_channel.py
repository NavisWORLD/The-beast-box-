"""Research-only CST dual-channel representation (not a new physical law).

This independent channel preserves dimensionless information geometry instead of
adding a k_B*T-scale contribution to a stellar-energy-scale floating-point sum.
There is deliberately no dyn12, model, memory, or host-policy integration.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from .model import Entity, Parameters, KB, _validate


@dataclass(frozen=True)
class InformationChannel:
    """One per entity; telemetry, not an external software-state interface."""

    geometric_potential: float
    signed_log_signal: float
    reconstructed_information_j: float


def information_channels(
    entities: Sequence[Entity], p: Parameters = Parameters()
) -> list[InformationChannel]:
    """Evaluate the Q interaction on its natural dimensionless thermal scale.

    Let h_i = sum_(j != i) f(I_i) f(I_j) exp(-r_ij/r0) r0 / d_ij.
    Then Q_i = -eta (k_B T) h_i, and signal_i = -log1p(eta*h_i).

    No learned coefficient, adaptive data normalization, or change of the source
    physical equation is introduced. log1p compresses the dynamic range; it is
    NOT equivalent to a direct energy sum or a validated AI-state variable.

    eta must be nonnegative for this preregistered monotone channel. The
    original research candidate itself retains its broader coefficient range.
    """
    _validate(entities, p)
    if p.eta < 0:
        raise ValueError("v1 monotone information channel requires eta >= 0")
    out: list[InformationChannel] = []
    for i, e in enumerate(entities):
        fraction_i = e.information_bits / (1.0 + e.information_bits)
        terms: list[float] = []
        for j, other in enumerate(entities):
            if i == j:
                continue
            distance = math.dist(e.position_m, other.position_m)
            softened = math.hypot(distance, p.softening_m)
            decay = math.exp(-distance / p.r0_m)
            fraction_j = other.information_bits / (1.0 + other.information_bits)
            terms.append(fraction_i * fraction_j * decay * (p.r0_m / softened))
        potential = math.fsum(terms)
        eta_potential = p.eta * potential
        q = -(p.eta * KB * p.temperature_k) * potential
        signal = -math.log1p(eta_potential)
        if not all(math.isfinite(x) for x in (potential, eta_potential, q, signal)):
            raise ValueError("information channel overflow; no silent clipping")
        if potential < 0:
            raise ValueError("negative information potential violates nonnegative inputs")
        out.append(InformationChannel(
            geometric_potential=potential,
            signed_log_signal=signal,
            reconstructed_information_j=q,
        ))
    return out
