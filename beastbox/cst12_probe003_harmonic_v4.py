from __future__ import annotations

import hashlib
import math
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe_003 import compile_arm_parameters, sha256_json, validate_bridge_packet

CANONICAL_RADIANS_DECIMALS = 12
CANONICAL_RADIANS_SCALE = 10**CANONICAL_RADIANS_DECIMALS


def canonical_radians(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("harmonic v4 radians must be finite")
    out = round(value, CANONICAL_RADIANS_DECIMALS)
    return 0.0 if out == 0.0 else out


def _canonical_nested(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_canonical_nested(v) for v in value]
    return canonical_radians(float(value))


def quantized_metric_digest(values: Sequence[Sequence[float]]) -> str:
    rows = [list(row) for row in values]
    if not rows:
        raise ValueError("metric matrix must not be empty")
    width = len(rows[0])
    if width < 1 or any(len(row) != width for row in rows):
        raise ValueError("metric matrix must be rectangular")
    payload = bytearray()
    payload.extend(len(rows).to_bytes(8, "big", signed=False))
    payload.extend(width.to_bytes(8, "big", signed=False))
    for row in rows:
        for value in row:
            q = int(round(canonical_radians(float(value)) * CANONICAL_RADIANS_SCALE))
            payload.extend(q.to_bytes(8, "big", signed=True))
    return hashlib.sha256(bytes(payload)).hexdigest()


def cst_conversion_lock(
    packet: Mapping[str, Sequence[float]], seeds: Mapping[str, int]
) -> dict[str, Any]:
    """Lock harmonic calibration to the exact frozen CST -> circuit conversion map.

    The lock is diagnostic identity only.  It does not rescale, tune, or otherwise
    alter the scientific arm parameters used by Probe 003.
    """

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
