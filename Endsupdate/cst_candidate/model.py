"""Historical raw CST transcription and a separately labeled research candidate.

The source equation and mathematical classification are specified in
CORRECTED_CST_SPEC.md. Never import this module into the host policy path.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

G = 6.67430e-11  # m^3 kg^-1 s^-2
C = 299_792_458.0  # m s^-1; historical source rounds this to 3e8
C_LEGACY = 3.0e8
KB = 1.380649e-23  # J K^-1
HBAR = 1.0545718e-34  # J s
PHI = (1 + math.sqrt(5)) / 2
T_CMB = 2.725  # K, historical assumed value, not a universal environment


@dataclass(frozen=True)
class Entity:
    mass_kg: float
    position_m: tuple[float, float, float]
    velocity12_m_s: tuple[float, ...]
    radius_m: float
    chaos_j: float = 0.0
    lyapunov_s_inv: float = 0.0
    information_bits: float = 0.0  # measured/assumed Shannon bits, NOT horizon entropy


@dataclass(frozen=True)
class Parameters:
    r0_m: float = 1.0e11
    softening_m: float = 1.0e7
    tau_s: float = 1.0
    reference_energy_j: float = 1.0e41
    beta: float = 1.0  # research interaction coefficient, not measured
    eta: float = 1.0  # research information coefficient, not measured
    temperature_k: float = T_CMB
    legacy_volume_m12: float = 1.0e144  # historical hypothetical, not observed


def _validate(entities: Sequence[Entity], p: Parameters) -> None:
    for v in (p.r0_m, p.softening_m, p.tau_s, p.reference_energy_j,
              p.temperature_k, p.legacy_volume_m12):
        if not math.isfinite(v) or v <= 0:
            raise ValueError("scales, temperature and volume must be finite and positive")
    if not all(math.isfinite(v) for v in (p.beta, p.eta)):
        raise ValueError("coefficients must be finite")
    for e in entities:
        nums = (e.mass_kg, *e.position_m, *e.velocity12_m_s, e.radius_m,
                e.chaos_j, e.lyapunov_s_inv, e.information_bits)
        if len(e.position_m) != 3 or len(e.velocity12_m_s) != 12 or not all(map(math.isfinite, nums)):
            raise ValueError("expected finite 3D positions and 12-component velocities")
        if e.mass_kg < 0 or e.radius_m < 0 or e.information_bits < 0:
            raise ValueError("mass, radius, and information must be nonnegative")


def _distance(a: Entity, b: Entity) -> float:
    return math.dist(a.position_m, b.position_m)


def legacy_raw(entities: Sequence[Entity], p: Parameters = Parameters()) -> list[float]:
    """Numerical transcription of 2025 CST_Formula_Explanation.markdown, not physical law.

    Deliberately retains + c*lambda + 1, G*m_i*m_j/(r*c^2), and the
    horizon-area information expression. No softening or retroactive fixes.
    Raises on coincident positions and zero (m*c^2 + chaos) denominator.
    """
    _validate(entities, p)
    values: list[float] = []
    for i, e in enumerate(entities):
        total = e.mass_kg * C_LEGACY**2 + e.chaos_j
        if total == 0:
            raise ValueError("historical formula has a zero energy denominator")
        kinetic = 0.5 * e.mass_kg * math.fsum(v*v for v in e.velocity12_m_s)
        first = (PHI * total + C_LEGACY * e.lyapunov_s_inv + 1.0) * kinetic / total
        coupling = gravity = information = 0.0
        bits_i = C_LEGACY**3 * (4 * math.pi * e.radius_m**2) / (4 * HBAR * G * math.log(2))
        for j, other in enumerate(entities):
            if i == j:
                continue
            r = _distance(e, other)
            if r == 0:
                raise ValueError("historical formula is singular at coincident positions")
            bits_j = C_LEGACY**3 * (4 * math.pi * other.radius_m**2) / (4 * HBAR * G * math.log(2))
            coupling += math.exp(-r/p.r0_m) * G * e.mass_kg * other.mass_kg / (r * C_LEGACY**2)
            gravity += G * e.mass_kg * other.mass_kg / r
            information += (KB * p.temperature_k / C_LEGACY) * bits_i * bits_j / r
        val = (first + coupling * total - gravity - information) / p.legacy_volume_m12
        if not math.isfinite(val):
            raise ValueError("historical formula overflow or nonfinite result")
        values.append(val)
    return values


def evaluate(entities: Sequence[Entity], p: Parameters = Parameters(),
             mode: str = "corrected") -> list[dict[str, float]]:
    """Dimensionless research score, with separate J-valued term telemetry.

    corrected: information term enabled; ablated: eta=0;
    control: classical K+U; legacy is *not* routed through this interface.
    """
    if mode not in ("corrected", "ablated", "control"):
        raise ValueError("unknown candidate mode")
    _validate(entities, p)
    outputs: list[dict[str, float]] = []
    for i, e in enumerate(entities):
        kinetic = 0.5 * e.mass_kg * math.fsum(v*v for v in e.velocity12_m_s)
        chaos_kinetic = (PHI + p.tau_s * e.lyapunov_s_inv) * kinetic if mode != "control" else kinetic
        gravity_terms, coupling_terms, info_terms = [], [], []
        for j, other in enumerate(entities):
            if i == j:
                continue
            r = math.hypot(_distance(e, other), p.softening_m)
            pair_energy = G * e.mass_kg * other.mass_kg / r
            gravity_terms.append(-pair_energy)
            decay = math.exp(-_distance(e, other) / p.r0_m)
            if mode != "control":
                coupling_terms.append(p.beta * decay * pair_energy)
                # Bounded information fractions are proxies; no horizon assumed.
                frac_i = e.information_bits / (1.0 + e.information_bits)
                frac_j = other.information_bits / (1.0 + other.information_bits)
                info_terms.append(-p.eta * KB * p.temperature_k * frac_i * frac_j * decay * p.r0_m / r)
        gravity_j = math.fsum(gravity_terms)
        coupling_j = math.fsum(coupling_terms) if mode != "control" else 0.0
        info_j = math.fsum(info_terms) if mode == "corrected" else 0.0
        total_j = math.fsum([chaos_kinetic, gravity_j, coupling_j, info_j])
        score = total_j / p.reference_energy_j
        if not all(map(math.isfinite, (chaos_kinetic, gravity_j, coupling_j, info_j, score))):
            raise ValueError("corrected computation overflowed; no silent clipping")
        outputs.append({"score": score, "kinetic_j": chaos_kinetic, "gravity_j": gravity_j,
                        "coupling_j": coupling_j, "information_j": info_j})
    return outputs
