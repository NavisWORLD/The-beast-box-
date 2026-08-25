from __future__ import annotations

import hashlib
import math
import random
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe_003 import (
    compile_arm_parameters,
    sha256_json,
    validate_bridge_packet,
    wrap_phase,
)
from beastbox.cst12_physics_probe_004 import SCIENTIFIC_ARMS, binding_for_arm

PROBE_ID = "cst12-physics-probe-005"
EXPECTED_STATE_PACKET_SHA256 = "31b7bc1b4afbf05db49360776d52eafeda69830f36694f789951293338c47e21"
EXPECTED_CST_CONVERSION_LOCK_SHA256 = "78296ee91aaf72fbabf23366d0660a893ad7102d99b8ede47b762f742d17c8d1"
CANONICAL_RADIANS_DECIMALS = 12

PRE_BRACKET = (
    "PRE_REF_0",
    "PRE_REF_120",
    "PRE_REF_240",
    "PRE_REF_HOLDOUT",
    "PRE_MIRROR_PM",
    "PRE_MIRROR_MP",
)
POST_BRACKET = (
    "POST_MIRROR_MP",
    "POST_MIRROR_PM",
    "POST_REF_HOLDOUT",
    "POST_REF_240",
    "POST_REF_120",
    "POST_REF_0",
)
MID_HOLDOUT = "MID_REF_HOLDOUT"

REFERENCE_PHASES = {
    "PRE_REF_0": 0.0,
    "PRE_REF_120": 2.0 * math.pi / 3.0,
    "PRE_REF_240": 4.0 * math.pi / 3.0,
    "PRE_REF_HOLDOUT": math.pi / 3.0,
    "MID_REF_HOLDOUT": 5.0 * math.pi / 3.0,
    "POST_REF_HOLDOUT": math.pi / 3.0,
    "POST_REF_240": 4.0 * math.pi / 3.0,
    "POST_REF_120": 2.0 * math.pi / 3.0,
    "POST_REF_0": 0.0,
}

# Canonical order only. block_slot_plan shuffles the seven scientific arms while
# leaving every calibration anchor fixed.
LOGICAL_SLOTS = PRE_BRACKET + tuple(SCIENTIFIC_ARMS[:3]) + (MID_HOLDOUT,) + tuple(SCIENTIFIC_ARMS[3:]) + POST_BRACKET


def _domain_seed(seed: int, domain: str) -> int:
    return int(hashlib.sha256(f"cst12-probe005|{int(seed)}|{domain}".encode()).hexdigest()[:16], 16)


def basis_order_for_block(block_id: int) -> tuple[str, str]:
    block = int(block_id)
    if block < 0:
        raise ValueError("block_id must be nonnegative")
    return ("X", "Y") if block % 2 == 0 else ("Y", "X")


def block_slot_plan(block_id: int, seed: int) -> list[str]:
    block = int(block_id)
    if block < 0:
        raise ValueError("block_id must be nonnegative")
    science = list(SCIENTIFIC_ARMS)
    random.Random(_domain_seed(int(seed), f"block:{block}:science-order")).shuffle(science)
    plan = list(PRE_BRACKET) + science[:3] + [MID_HOLDOUT] + science[3:] + list(POST_BRACKET)
    if len(plan) != 20 or len(set(plan)) != 20:
        raise AssertionError("Probe 005 block must contain exactly twenty unique logical slots")
    if plan[:6] != list(PRE_BRACKET) or plan[-6:] != list(POST_BRACKET) or plan[9] != MID_HOLDOUT:
        raise AssertionError("Probe 005 calibration anchors moved")
    return plan


def slot_source_arm(slot: str) -> str:
    name = str(slot)
    if name in SCIENTIFIC_ARMS:
        return name
    if name.endswith("MIRROR_PM"):
        return "MIRROR_PM"
    if name.endswith("MIRROR_MP"):
        return "MIRROR_MP"
    if name in REFERENCE_PHASES:
        return "REF_HOLDOUT"
    raise ValueError(f"unknown Probe 005 logical slot: {name}")


def binding_for_slot(
    packet: Mapping[str, Sequence[float]], slot: str, seeds: Mapping[str, int]
) -> dict[str, Any]:
    source = slot_source_arm(slot)
    binding = dict(binding_for_arm(packet, source, seeds))
    if slot in REFERENCE_PHASES:
        binding["ancilla_phase"] = float(REFERENCE_PHASES[slot])
    return binding


def _as_matrix2(value: Sequence[Sequence[float]]) -> list[list[float]]:
    if len(value) != 2 or any(len(row) != 2 for row in value):
        raise ValueError("M must be 2x2")
    out = [[float(v) for v in row] for row in value]
    if not all(math.isfinite(v) for row in out for v in row):
        raise ValueError("M must be finite")
    return out


def _as_vector2(value: Sequence[float]) -> list[float]:
    if len(value) != 2:
        raise ValueError("c must contain two values")
    out = [float(v) for v in value]
    if not all(math.isfinite(v) for v in out):
        raise ValueError("c must be finite")
    return out


def fit_forward_affine(
    measured: Mapping[str, complex],
    ideal: Mapping[str, complex],
    *,
    condition_limit: float,
) -> dict[str, Any]:
    """Fit measured = M @ ideal + c from the frozen three-point Trinity reference."""
    import numpy as np

    keys = ("REF_0", "REF_120", "REF_240")
    if set(measured) != set(keys) or set(ideal) != set(keys):
        raise ValueError("forward affine fit requires exactly REF_0/REF_120/REF_240")
    limit = float(condition_limit)
    if not math.isfinite(limit) or limit <= 1.0:
        raise ValueError("condition_limit must be finite and greater than one")

    design = np.array(
        [[complex(ideal[k]).real, complex(ideal[k]).imag, 1.0] for k in keys],
        dtype=float,
    )
    target = np.array(
        [[complex(measured[k]).real, complex(measured[k]).imag] for k in keys],
        dtype=float,
    )
    coeff = np.linalg.solve(design, target)
    M = np.array(
        [[coeff[0, 0], coeff[1, 0]], [coeff[0, 1], coeff[1, 1]]],
        dtype=float,
    )
    c = np.array([coeff[2, 0], coeff[2, 1]], dtype=float)
    cond = float(np.linalg.cond(M))
    if not math.isfinite(cond) or cond > limit:
        raise ValueError(f"ill-conditioned Probe 005 forward map: condition={cond}")
    return {
        "M": [[float(M[0, 0]), float(M[0, 1])], [float(M[1, 0]), float(M[1, 1])]],
        "c": [float(c[0]), float(c[1])],
        "condition_number": cond,
        "condition_limit": limit,
    }


def interpolate_forward_affine(
    pre: Mapping[str, Any],
    post: Mapping[str, Any],
    t: float,
    *,
    condition_limit: float,
) -> dict[str, Any]:
    import numpy as np

    tau = float(t)
    if not math.isfinite(tau) or tau < 0.0 or tau > 1.0:
        raise ValueError("t must lie in [0,1]")
    pre_M = np.array(_as_matrix2(pre["M"]), dtype=float)
    post_M = np.array(_as_matrix2(post["M"]), dtype=float)
    pre_c = np.array(_as_vector2(pre["c"]), dtype=float)
    post_c = np.array(_as_vector2(post["c"]), dtype=float)
    M = (1.0 - tau) * pre_M + tau * post_M
    c = (1.0 - tau) * pre_c + tau * post_c
    cond = float(np.linalg.cond(M))
    limit = float(condition_limit)
    if not math.isfinite(cond) or cond > limit:
        raise ValueError(f"ill-conditioned interpolated Probe 005 map: condition={cond}")
    return {
        "M": [[float(M[0, 0]), float(M[0, 1])], [float(M[1, 0]), float(M[1, 1])]],
        "c": [float(c[0]), float(c[1])],
        "condition_number": cond,
        "condition_limit": limit,
        "t": tau,
    }


def apply_forward_reprojection(
    measured: complex,
    fit: Mapping[str, Any],
    *,
    condition_limit: float,
) -> complex:
    import numpy as np

    M = np.array(_as_matrix2(fit["M"]), dtype=float)
    c = np.array(_as_vector2(fit["c"]), dtype=float)
    cond = float(np.linalg.cond(M))
    limit = float(condition_limit)
    if not math.isfinite(cond) or cond > limit:
        raise ValueError(f"Probe 005 reprojection map is ill-conditioned: condition={cond}")
    z = complex(measured)
    if not math.isfinite(z.real) or not math.isfinite(z.imag):
        raise ValueError("measured vector must be finite")
    corrected = np.linalg.solve(M, np.array([z.real, z.imag], dtype=float) - c)
    return complex(float(corrected[0]), float(corrected[1]))


def reference_error(corrected: complex, ideal: complex) -> dict[str, float]:
    z = complex(corrected)
    target = complex(ideal)
    if abs(z) < 1e-15 or abs(target) < 1e-15:
        phase = math.pi
    else:
        phase = abs(
            wrap_phase(
                math.atan2(z.imag, z.real) - math.atan2(target.imag, target.real)
            )
        )
    return {
        "phase_error": float(phase),
        "radius_error": float(abs(abs(z) - abs(target))),
    }


def mirror_direction_diagnostics(pm: complex, mp: complex) -> dict[str, float]:
    p = complex(pm)
    m = complex(mp)
    if abs(p) < 1e-15 or abs(m) < 1e-15:
        raise ValueError("mirror diagnostic vectors must be nonzero")
    pp = wrap_phase(math.atan2(p.imag, p.real))
    mp_phase = wrap_phase(math.atan2(m.imag, m.real))
    s = math.sin(pp) + math.sin(mp_phase)
    c = math.cos(pp) + math.cos(mp_phase)
    common = 0.0 if abs(s) < 1e-18 and abs(c) < 1e-18 else wrap_phase(math.atan2(s, c))
    antisym = 0.5 * wrap_phase(pp - mp_phase)
    return {
        "pm_phase": float(pp),
        "mp_phase": float(mp_phase),
        "common_phase": float(common),
        "common_abs_phase": float(abs(common)),
        "antisymmetric_phase": float(antisym),
        "antisymmetric_abs_phase": float(abs(antisym)),
    }


def _canonical_radians(value: float) -> float:
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("conversion-lock radians must be finite")
    out = round(v, CANONICAL_RADIANS_DECIMALS)
    return 0.0 if out == 0.0 else out


def _canonical_nested(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_canonical_nested(v) for v in value]
    return _canonical_radians(float(value))


def cst_conversion_lock(
    packet: Mapping[str, Sequence[float]], seeds: Mapping[str, int]
) -> dict[str, Any]:
    """Reproduce the frozen Harmonic-v4 CST conversion identity without altering values."""
    validate_bridge_packet(packet)
    params = compile_arm_parameters(packet, "MIRROR_CAL", seeds)
    lock = {
        "schema": "cst12-probe003-harmonic-v4-conversion-lock-v1",
        "bridge_packet_sha256": sha256_json(dict(packet)),
        "canonical_radians_decimals": CANONICAL_RADIANS_DECIMALS,
        "alpha": _canonical_nested(params["alpha"]),
        "theta": _canonical_nested(params["theta"]),
        "chaos_xyz": _canonical_nested(params["chaos_xyz"]),
        "lambda_rzz": _canonical_nested(params["lambda_rzz"]),
        "readout_layer_1": _canonical_nested(params["readout_layer_1"]),
        "readout_layer_2": _canonical_nested(params["readout_layer_2"]),
        "conversion_statement": (
            "alpha_j=atan2(phase12[2j],phase12[2j+1]); "
            "theta_j=(pi/2)*(1+tanh(mean(dynamic pair))); "
            "chaos rotations=(pi/16)*tanh(chaos triplet); "
            "lambda_rzz=(pi/8)*tanh(phi-weighted Hebbian quartet); "
            "MIRROR_CAL readout layers are +alpha then -alpha"
        ),
    }
    lock["sha256"] = sha256_json(lock)
    return lock
