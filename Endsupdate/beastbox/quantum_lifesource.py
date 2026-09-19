from __future__ import annotations

import copy
import hashlib
import json
import math
import random
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

HISTORICAL_LABELS = frozenset({"NULL_COMPATIBLE", "INCONCLUSIVE", "FAILED", "UNRESOLVED"})
OUTCOMES = ("00", "01", "10", "11")
Z95 = 1.959963984540054
_SECRET_NAMES = frozenset(
    {
        "token",
        "secret",
        "password",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "ibm_quantum_token",
        "github_token",
    }
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _finite_vector(values: Sequence[float], *, n: int, name: str) -> list[float]:
    if len(values) != n:
        raise ValueError(f"{name} must contain exactly {n} values")
    out = [float(value) for value in values]
    if not all(math.isfinite(value) for value in out):
        raise ValueError(f"{name} must contain only finite values")
    return out


def _unit(values: Sequence[float]) -> list[float]:
    vec = [float(value) for value in values]
    norm = math.sqrt(sum(value * value for value in vec))
    if norm <= 1e-15:
        return [0.0] * len(vec)
    return [float(f"{(value / norm):.15g}") for value in vec]


def _probabilities(packet: Mapping[str, Any] | Sequence[float]) -> list[float]:
    if isinstance(packet, Mapping):
        counts_raw = packet.get("counts")
        if not isinstance(counts_raw, Mapping):
            raise ValueError("packet counts must be a mapping")
        counts = [int(counts_raw.get(outcome, 0)) for outcome in OUTCOMES]
        if any(value < 0 for value in counts):
            raise ValueError("measurement counts cannot be negative")
        declared_shots = int(packet.get("shots", sum(counts)))
        if declared_shots != sum(counts) or declared_shots <= 0:
            raise ValueError("measurement packet shot count is invalid")
        return [float(f"{(value / declared_shots):.15g}") for value in counts]

    values = _finite_vector(packet, n=4, name="probability packet")
    if all(abs(value) <= 1e-15 for value in values):
        return [0.0] * 4
    if any(value < 0.0 or value > 1.0 for value in values):
        raise ValueError("probability packet values must be in [0,1]")
    if not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("probability packet must sum to one")
    return [float(f"{value:.15g}") for value in values]


def packets_to_dyn12(packets: Sequence[Mapping[str, Any] | Sequence[float]]) -> list[float]:
    """Frozen source adapter: three 4-outcome packets -> exactly twelve values."""
    if len(packets) != 3:
        raise ValueError("dyn12 source adapter requires exactly three measurement packets")
    out: list[float] = []
    for packet in packets:
        out.extend(_probabilities(packet))
    return _finite_vector(out, n=12, name="quantum/control dyn12 drive")


@dataclass(frozen=True)
class BlindPacket:
    """The only source object allowed across the semantic blinding boundary."""

    blind_id: str
    dyn12: Sequence[float]
    packet_sha256: str

    def __post_init__(self) -> None:
        if not str(self.blind_id).startswith("SOURCE_"):
            raise ValueError("blind_id must be an opaque SOURCE_* identifier")
        _finite_vector(self.dyn12, n=12, name="dyn12")
        digest = str(self.packet_sha256).lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("packet_sha256 must be SHA-256")

    def as_downstream_dict(self) -> dict[str, Any]:
        return {
            "blind_id": str(self.blind_id),
            "dyn12": _finite_vector(self.dyn12, n=12, name="dyn12"),
            "packet_sha256": str(self.packet_sha256).lower(),
        }


def replay_packets(packets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return copy.deepcopy([dict(packet) for packet in packets])


def shuffled_packets(packets: Sequence[Mapping[str, Any]], *, seed: int) -> list[dict[str, Any]]:
    rows = replay_packets(packets)
    if len(rows) <= 1:
        return rows
    rng = random.Random(int(seed))
    order = list(range(len(rows)))
    rng.shuffle(order)
    # Deterministically prevent the identity permutation because condition F is
    # explicitly required to break temporal ordering while preserving values.
    if order == list(range(len(rows))):
        order = order[1:] + order[:1]
    return [rows[index] for index in order]


def classical_matched_packets(
    packets: Sequence[Mapping[str, Any]],
    *,
    seed: int,
) -> list[dict[str, Any]]:
    """Sample classical packets from A's frozen empirical joint distribution."""
    if not packets:
        raise ValueError("matched classical control requires at least one source packet")
    totals = {outcome: 0 for outcome in OUTCOMES}
    packet_shots: list[int] = []
    for packet in packets:
        counts = packet.get("counts")
        if not isinstance(counts, Mapping):
            raise ValueError("packet counts must be a mapping")
        shots = int(packet.get("shots", 0))
        values = [int(counts.get(outcome, 0)) for outcome in OUTCOMES]
        if shots <= 0 or sum(values) != shots or any(value < 0 for value in values):
            raise ValueError("source packet has invalid counts/shots")
        packet_shots.append(shots)
        for outcome, value in zip(OUTCOMES, values, strict=True):
            totals[outcome] += value
    grand = sum(totals.values())
    probabilities = [totals[outcome] / grand for outcome in OUTCOMES]
    cumulative: list[float] = []
    running = 0.0
    for value in probabilities:
        running += value
        cumulative.append(running)
    cumulative[-1] = 1.0

    rng = random.Random(int(seed))
    out: list[dict[str, Any]] = []
    for shots in packet_shots:
        counts = {outcome: 0 for outcome in OUTCOMES}
        for _ in range(shots):
            value = rng.random()
            for outcome, edge in zip(OUTCOMES, cumulative, strict=True):
                if value < edge:
                    counts[outcome] += 1
                    break
        out.append({"counts": counts, "shots": shots})
    return out


def zero_packets(count: int = 3) -> list[list[float]]:
    if int(count) <= 0:
        raise ValueError("zero packet count must be positive")
    return [[0.0] * 4 for _ in range(int(count))]


def mirror_step(state1: Sequence[float], source_drive: Sequence[float]) -> dict[str, list[float]]:
    """Frozen deterministic software mirror transform.

    This is not a quantum operation. It is a source-blind state transform that
    lets the experiment measure whether source condition changes the same
    downstream software loop.
    """
    s1 = _finite_vector(state1, n=12, name="state1")
    drive = _finite_vector(source_drive, n=12, name="source_drive")
    observer = _unit([(left + right) / 2.0 for left, right in zip(s1, drive, strict=True)])
    feedback = _unit([obs - left for obs, left in zip(observer, s1, strict=True)])
    coupled = [
        float(f"{math.tanh(0.70 * left + 0.20 * obs + 0.10 * fb):.15g}")
        for left, obs, fb in zip(drive, observer, feedback, strict=True)
    ]
    return {"observer": observer, "feedback": feedback, "coupled_drive": coupled}


def expand_drive54(drive12: Sequence[float], *, packet_sha256: str) -> list[float]:
    """Source-blind deterministic expansion used only to enter existing StateFamily."""
    source = _finite_vector(drive12, n=12, name="drive12")
    digest = str(packet_sha256).lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("packet_sha256 must be SHA-256")
    out = list(source)
    for index in range(12, 54):
        h = hashlib.sha256(f"lifesource-drive:{digest}:{index}".encode("ascii")).digest()
        unit = int.from_bytes(h[:8], "big") / float((1 << 64) - 1)
        source_value = source[index % 12]
        out.append(float(f"{math.tanh(source_value + 0.05 * (2.0 * unit - 1.0)):.15g}"))
    return out


def chsh_statistic(settings: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Compute frozen CHSH witness and conservative normal-approximation SE."""
    required = ("a0b0", "a0b1", "a1b0", "a1b1")
    if set(settings) != set(required):
        raise ValueError("CHSH settings must contain exactly a0b0,a0b1,a1b0,a1b1")
    correlations: dict[str, float] = {}
    variances: dict[str, float] = {}
    for name in required:
        row = settings[name]
        correlation = float(row["correlation"])
        shots = int(row["shots"])
        if not math.isfinite(correlation) or correlation < -1.0 or correlation > 1.0:
            raise ValueError("CHSH correlations must be finite in [-1,1]")
        if shots <= 0:
            raise ValueError("CHSH shots must be positive")
        correlations[name] = correlation
        variances[name] = max(0.0, (1.0 - correlation * correlation) / shots)
    s_value = correlations["a0b0"] + correlations["a0b1"] + correlations["a1b0"] - correlations["a1b1"]
    se = math.sqrt(sum(variances.values()))
    lower = abs(s_value) - Z95 * se
    return {
        "schema": "zeref-chsh-witness-v1",
        "S": float(s_value),
        "SE": float(se),
        "lower_95": float(lower),
        "criterion": "abs(S)-1.959963984540054*SE>2.0",
        "entanglement_witness_pass": bool(lower > 2.0),
        "settings": correlations,
    }


def correlation_from_counts(counts: Mapping[str, int]) -> float:
    values = {outcome: int(counts.get(outcome, 0)) for outcome in OUTCOMES}
    if any(value < 0 for value in values.values()):
        raise ValueError("counts cannot be negative")
    shots = sum(values.values())
    if shots <= 0:
        raise ValueError("counts must contain at least one shot")
    same = values["00"] + values["11"]
    different = values["01"] + values["10"]
    return (same - different) / shots


def _reject_secrets(value: object, *, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in _SECRET_NAMES or normalized.endswith("_token") or normalized.endswith("_secret"):
                raise ValueError(f"secret field is forbidden in evidence snapshot: {path}.{key}")
            _reject_secrets(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_secrets(child, path=f"{path}[{index}]")


def seal_snapshot(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical hash-addressed snapshot without modifying input."""
    body = copy.deepcopy(dict(payload))
    _reject_secrets(body)
    body.pop("snapshot_sha256", None)
    sealed = dict(body)
    sealed["snapshot_sha256"] = sha256_json(body)
    return sealed


def verify_snapshot(snapshot: Mapping[str, Any]) -> bool:
    row = dict(snapshot)
    expected = str(row.pop("snapshot_sha256", "")).lower()
    if len(expected) != 64:
        return False
    try:
        _reject_secrets(row)
    except ValueError:
        return False
    return sha256_json(row) == expected


def require_historical_label(label: str) -> str:
    normalized = str(label).strip().upper()
    if normalized not in HISTORICAL_LABELS:
        raise ValueError(f"unsupported inherited historical evidence label: {label}")
    return normalized
