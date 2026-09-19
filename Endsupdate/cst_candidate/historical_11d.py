"""Source-grounded raw 11D CST equation from The-theory-of-CST/cst_engine.py.

Preserves the algebra of CSTEntity.compute_psi (revision 306362e4), including
clipping. Does NOT reconstruct its upstream random state, neighbors, or
compute_lyapunov; caller supplies the intermediate values explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .model import C_LEGACY, PHI


@dataclass(frozen=True)
class Legacy11DInput:
    mass_kg: float
    chaos_energy_j: float
    lyapunov_s_inv: float
    path_length_m: float
    connectivity_m_s2: float
    gravitational_potential_j: float
    delta_t_s: float


def legacy_11d_psi(
    x: Legacy11DInput,
    *,
    volume_m11: float = 1e132,
    length_scale_m: float = 1e12,
    reference_acceleration_m_s2: float = 1.2e-10,
    clip_abs: float = 1e-10,
) -> dict[str, float | bool]:
    """Reproduce the historical five-term aggregate and its output clip.

    The original code writes '1e12' without a unit. The caller-supplied
    length_scale_m interpretation is necessary for a dimensional reading,
    not an independently verified model parameter.
    """
    nums = (x.mass_kg, x.chaos_energy_j, x.lyapunov_s_inv, x.path_length_m,
            x.connectivity_m_s2, x.gravitational_potential_j, x.delta_t_s,
            volume_m11, length_scale_m, reference_acceleration_m_s2, clip_abs)
    if not all(math.isfinite(v) for v in nums):
        raise ValueError("all historical inputs and scales must be finite")
    if x.mass_kg < 0 or x.path_length_m < 0 or x.delta_t_s < 0:
        raise ValueError("mass, path length, and time must be nonnegative")
    if min(volume_m11, length_scale_m, reference_acceleration_m_s2, clip_abs) <= 0:
        raise ValueError("historical normalization scales must be positive")
    ec = x.mass_kg * C_LEGACY**2 + x.chaos_energy_j
    terms = (
        PHI * ec,
        x.lyapunov_s_inv * ec * x.delta_t_s,
        x.path_length_m * x.mass_kg * C_LEGACY**2 / length_scale_m,
        x.connectivity_m_s2 * ec / reference_acceleration_m_s2,
        x.gravitational_potential_j,
    )
    raw = math.fsum(terms) / volume_m11
    if not math.isfinite(raw):
        raise ValueError("historical result overflow or nonfinite value")
    clipped = max(-clip_abs, min(clip_abs, raw))
    return {
        "unclipped_psi": raw,
        "clipped_psi": clipped,
        "clipped": raw != clipped,
        "term1_j": terms[0],
        "term2_j": terms[1],
        "term3_j": terms[2],
        "term4_j": terms[3],
        "term5_j": terms[4],
    }
