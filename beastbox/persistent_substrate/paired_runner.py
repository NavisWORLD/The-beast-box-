"""Paired, threshold-free scoring primitives for the real A->B->A swap.

This module records model behavior. It does not infer consciousness, identity
continuity, biological continuity, a soul, or any physical/quantum effect.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .metrics import preference_delta
from .prompts import FrozenPromptBattery
from .protocol import CandidateScore, sha256_json, validate_wire_candidates


EXPECTED_CANONICAL_RECORD_SHA256 = {
    17: "319bdb598d8d454a2c577104487389f148dd903099f28074475ee9ae6e62fc7d",
    311: "556dc79f3b2b7e9e4b0ecc3911c201e1dca87eab59f207e1177503c7a76bc361",
}

_ALLOWED_ASCII = frozenset(chr(code) for code in range(32, 127) if chr(code) not in {"$", "~"}) | {"\n"}


@dataclass(frozen=True)
class CaseSurface:
    case_id: str
    family: str
    wire: str
    preferred_continuation: str
    rejected_continuation: str
    requested_memory_id: int | None
    source_memory_id: int | None
    source_record_sha256: str | None
    wire_sha256: str


@dataclass(frozen=True)
class StageMeasurement:
    model_identity: dict[str, Any]
    surface_set_sha256: str
    deltas: dict[str, float]
    cases: tuple[dict[str, Any], ...]
    model_invocations: int


def compact_ascii(text: str) -> str:
    """Return the frozen Model-A-safe surface, replacing unsupported chars."""

    return "".join(character if character in _ALLOWED_ASCII else "?" for character in str(text))


def deterministic_shuffle_map(record_ids: Sequence[int]) -> dict[int, int]:
    """Rotate sorted canonical record IDs by one position, without mutating memory."""

    ordered = sorted({int(record_id) for record_id in record_ids})
    if len(ordered) < 2:
        raise ValueError("shuffled-memory control requires at least two unique record ids")
    return {record_id: ordered[(index + 1) % len(ordered)] for index, record_id in enumerate(ordered)}


def _record_map(records: Mapping[int, Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    normalized: dict[int, dict[str, Any]] = {}
    for record_id, row in records.items():
        rid = int(record_id)
        expected = EXPECTED_CANONICAL_RECORD_SHA256.get(rid)
        if expected is None:
            raise RuntimeError(f"unfrozen canonical memory record id: {rid}")
        observed_id = int(row.get("memory_id", -1))
        observed_sha = str(row.get("record_sha256") or "")
        if observed_id != rid:
            raise RuntimeError(f"canonical record id mismatch: requested={rid} observed={observed_id}")
        if observed_sha != expected:
            raise RuntimeError(
                f"canonical record hash mismatch: id={rid} expected={expected} observed={observed_sha}"
            )
        normalized[rid] = dict(row)
    return normalized


def _surface_hash(surfaces: Mapping[str, CaseSurface]) -> str:
    return sha256_json(
        [
            {
                "case_id": case_id,
                "family": surface.family,
                "wire": surface.wire,
                "preferred_continuation": surface.preferred_continuation,
                "rejected_continuation": surface.rejected_continuation,
                "requested_memory_id": surface.requested_memory_id,
                "source_memory_id": surface.source_memory_id,
                "source_record_sha256": surface.source_record_sha256,
            }
            for case_id, surface in sorted(surfaces.items())
        ]
    )


def build_surface_set(
    battery: FrozenPromptBattery,
    records: Mapping[int, Mapping[str, Any]],
    *,
    mode: str,
    block: int = 128,
) -> dict[str, CaseSurface]:
    """Build one complete six-family surface set, failing closed on incompatibility."""

    if battery.battery_id != "persistent-substrate-prompts-v2":
        raise ValueError("real paired scoring requires persistent-substrate-prompts-v2")
    if battery.render_policy != "compact-ascii-tokenizer-safe-v1":
        raise ValueError("unexpected paired-runner render policy")
    if mode not in {"valid", "empty", "shuffled"}:
        raise ValueError(f"unknown surface mode: {mode}")

    required_ids = sorted({rid for case in battery.cases for rid in case.canonical_record_ids})
    normalized_records = _record_map({rid: records[rid] for rid in required_ids}) if required_ids else {}
    shuffle = deterministic_shuffle_map(required_ids) if mode == "shuffled" and required_ids else {}

    surfaces: dict[str, CaseSurface] = {}
    for case in battery.cases:
        requested_id = case.canonical_record_ids[0] if case.canonical_record_ids else None
        source_id: int | None = None
        source_sha: str | None = None

        prompt = compact_ascii(case.prompt)
        preferred = compact_ascii(case.preferred_continuation)
        rejected = compact_ascii(case.rejected_continuation)

        if requested_id is None:
            wire = f"Q:{prompt}\nM:-\nA:"
        elif mode == "empty":
            wire = f"Q:{prompt}\nM:?\nA:"
        else:
            source_id = requested_id if mode == "valid" else shuffle[requested_id]
            row = normalized_records[source_id]
            source_sha = str(row["record_sha256"])
            memory_text = compact_ascii(str(row.get("text") or ""))
            wire = f"Q:{prompt}\nM:{source_id}:{memory_text}\nA:"

        validate_wire_candidates(wire, (preferred, rejected), block=block)
        surface = CaseSurface(
            case_id=case.case_id,
            family=case.family,
            wire=wire,
            preferred_continuation=preferred,
            rejected_continuation=rejected,
            requested_memory_id=requested_id,
            source_memory_id=source_id,
            source_record_sha256=source_sha,
            wire_sha256=sha256_json({"wire": wire}),
        )
        surfaces[case.case_id] = surface

    expected_ids = {case.case_id for case in battery.cases}
    if set(surfaces) != expected_ids:
        raise RuntimeError("paired surface builder lost prompt cases")
    return surfaces


def _score_dict(score: CandidateScore) -> dict[str, Any]:
    return asdict(score)


def score_stage(
    adapter: Any,
    battery: FrozenPromptBattery,
    surfaces: Mapping[str, CaseSurface],
) -> StageMeasurement:
    """Score every frozen paired case once; never filter or generate text."""

    expected_ids = [case.case_id for case in battery.cases]
    if set(surfaces) != set(expected_ids):
        raise RuntimeError("stage surface set does not match frozen battery")

    rows: list[dict[str, Any]] = []
    deltas: dict[str, float] = {}
    for case in battery.cases:
        surface = surfaces[case.case_id]
        scores = tuple(
            adapter.score_candidates(
                surface.wire,
                (surface.preferred_continuation, surface.rejected_continuation),
            )
        )
        if len(scores) != 2:
            raise RuntimeError(f"adapter returned {len(scores)} scores for {case.case_id}; expected 2")
        by_candidate = {score.candidate: score for score in scores}
        expected_candidates = {surface.preferred_continuation, surface.rejected_continuation}
        if set(by_candidate) != expected_candidates:
            raise RuntimeError(f"adapter candidate mismatch for {case.case_id}")
        preferred = by_candidate[surface.preferred_continuation]
        rejected = by_candidate[surface.rejected_continuation]
        delta = float(preference_delta(preferred=preferred, rejected=rejected))
        deltas[case.case_id] = delta
        rows.append(
            {
                "case_id": case.case_id,
                "family": case.family,
                "wire_sha256": surface.wire_sha256,
                "requested_memory_id": surface.requested_memory_id,
                "source_memory_id": surface.source_memory_id,
                "source_record_sha256": surface.source_record_sha256,
                "preferred": _score_dict(preferred),
                "rejected": _score_dict(rejected),
                "preference_delta_rejected_minus_preferred": delta,
            }
        )

    identity = dict(adapter.identity)
    return StageMeasurement(
        model_identity=identity,
        surface_set_sha256=_surface_hash(surfaces),
        deltas=deltas,
        cases=tuple(rows),
        model_invocations=len(rows),
    )
