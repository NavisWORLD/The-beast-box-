from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

ZERO_SHA256 = "0" * 64
PROVENANCE_CLASSES = {"measured", "derived", "synthetic"}
PHYSICAL_SOURCE_TYPES = {"ibm_quantum_hardware_measurement"}
FORMULA_VERSION = "zeref-r12-formula-v1"
CLAIM_BOUNDARY = (
    "Persistent computational memory over instrument evidence; not biological life, "
    "consciousness, deceased-person identity, resurrection, communication with the dead, "
    "or quantum advantage."
)

R12_NAMES = (
    "source_integrity",
    "temporal_novelty",
    "measurement_confidence",
    "distribution_energy",
    "cross_condition_agreement",
    "distribution_entropy",
    "surprise",
    "memory_relevance",
    "retention_pressure",
    "contradiction_pressure",
    "adaptation_stability",
    "reality_coupling",
)

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_float_sum(values) -> float:
    """Version-stable Neumaier compensated sum matching Python 3.12 float sum semantics."""
    total = 0.0
    compensation = 0.0
    for raw in values:
        value = float(raw)
        updated = total + value
        if abs(total) >= abs(value):
            compensation += (total - updated) + value
        else:
            compensation += (value - updated) + total
        total = updated
    if compensation and math.isfinite(compensation):
        total += compensation
    return total


def _validate_sha(value: str, field: str) -> str:
    value = str(value).lower()
    if not _SHA_RE.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _validate_event_body(event: Mapping[str, Any]) -> None:
    provenance = str(event.get("provenance_class") or "")
    if provenance not in PROVENANCE_CLASSES:
        raise ValueError("provenance_class must be measured, derived, or synthetic")
    source_type = str(event.get("source_type") or "")
    if source_type in PHYSICAL_SOURCE_TYPES and provenance != "measured":
        raise ValueError("fresh physical measurement source_type requires measured provenance")
    if not str(event.get("created_at_utc") or "").endswith("Z"):
        raise ValueError("created_at_utc must be an explicit UTC timestamp ending in Z")
    confidence = float(event.get("confidence", -1.0))
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be finite and in [0,1]")
    _validate_sha(str(event.get("source_sha256") or ""), "source_sha256")
    _validate_sha(str(event.get("payload_sha256") or ""), "payload_sha256")
    _validate_sha(str(event.get("parent_event_sha256") or ""), "parent_event_sha256")
    if sha256_json(event.get("payload")) != event.get("payload_sha256"):
        raise ValueError("payload SHA-256 mismatch")


class RealityLedger:
    """Append-only, hash-chained JSONL ledger for reality/provenance events."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for lineno, raw in enumerate(handle, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid reality ledger JSON at line {lineno}") from exc
                if not isinstance(row, dict):
                    raise ValueError(f"reality ledger line {lineno} is not an object")
                rows.append(row)
        return rows

    @staticmethod
    def _dedupe_sha(
        *, source_type: str, source_id: str, source_sha256: str, payload_sha256: str
    ) -> str:
        return sha256_json(
            {
                "source_type": source_type,
                "source_id": source_id,
                "source_sha256": source_sha256,
                "payload_sha256": payload_sha256,
            }
        )

    def verify(self) -> dict[str, Any]:
        parent = ZERO_SHA256
        seen_ids: set[str] = set()
        for index, event in enumerate(self.events(), 1):
            _validate_event_body(event)
            if event.get("parent_event_sha256") != parent:
                raise ValueError(f"reality ledger parent mismatch at event {index}")
            event_id = str(event.get("event_id") or "")
            if not event_id or event_id in seen_ids:
                raise ValueError(f"duplicate or missing event_id at event {index}")
            seen_ids.add(event_id)
            body = dict(event)
            claimed = str(body.pop("event_sha256", ""))
            _validate_sha(claimed, "event_sha256")
            actual = sha256_json(body)
            if actual != claimed:
                raise ValueError(f"reality ledger event SHA-256 mismatch at event {index}")
            parent = claimed
        return {
            "schema": "zeref-reality-ledger-verification-v1",
            "chain_valid": True,
            "event_count": len(seen_ids),
            "tip_sha256": parent,
        }

    def append_event(
        self,
        *,
        provenance_class: str,
        source_type: str,
        source_id: str,
        source_sha256: str,
        payload: Mapping[str, Any] | Sequence[Any] | str | int | float | bool | None,
        transform: str,
        confidence: float,
        created_at_utc: str,
        claim_boundary: str = CLAIM_BOUNDARY,
    ) -> dict[str, Any]:
        provenance_class = str(provenance_class)
        source_type = str(source_type)
        source_id = str(source_id)
        source_sha256 = _validate_sha(source_sha256, "source_sha256")
        payload_sha256 = sha256_json(payload)
        if provenance_class not in PROVENANCE_CLASSES:
            raise ValueError("provenance_class must be measured, derived, or synthetic")
        if source_type in PHYSICAL_SOURCE_TYPES and provenance_class != "measured":
            raise ValueError("fresh physical measurement source_type requires measured provenance")
        if not source_id:
            raise ValueError("source_id is required")
        if not str(created_at_utc).endswith("Z"):
            raise ValueError("created_at_utc must end in Z")
        confidence = float(confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be finite and in [0,1]")

        existing = self.events()
        if existing:
            self.verify()
        dedupe = self._dedupe_sha(
            source_type=source_type,
            source_id=source_id,
            source_sha256=source_sha256,
            payload_sha256=payload_sha256,
        )
        for event in existing:
            prior = self._dedupe_sha(
                source_type=str(event["source_type"]),
                source_id=str(event["source_id"]),
                source_sha256=str(event["source_sha256"]),
                payload_sha256=str(event["payload_sha256"]),
            )
            if prior == dedupe:
                return {"appended": False, "event": event}

        body: dict[str, Any] = {
            "schema": "zeref-reality-event-v1",
            "event_id": f"reality-{len(existing) + 1:08d}",
            "created_at_utc": str(created_at_utc),
            "provenance_class": provenance_class,
            "source_type": source_type,
            "source_id": source_id,
            "source_sha256": source_sha256,
            "payload_sha256": payload_sha256,
            "payload": payload,
            "parent_event_sha256": existing[-1]["event_sha256"] if existing else ZERO_SHA256,
            "transform": str(transform),
            "confidence": confidence,
            "claim_boundary": str(claim_boundary),
        }
        _validate_event_body(body)
        event = dict(body)
        event["event_sha256"] = sha256_json(body)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(canonical_json(event) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.verify()
        return {"appended": True, "event": event}


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(str(text).lower().replace("_", " ")))


def _counts_distribution(event: Mapping[str, Any]) -> dict[str, float]:
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        return {}
    counts = payload.get("counts")
    if not isinstance(counts, Mapping):
        return {}
    normalized: dict[str, int] = {}
    for key, value in counts.items():
        try:
            ivalue = int(value)
        except (TypeError, ValueError):
            return {}
        if ivalue < 0:
            return {}
        normalized[str(key)] = normalized.get(str(key), 0) + ivalue
    total = sum(normalized.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in normalized.items() if value > 0}


def _tvd(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = sorted(set(left) | set(right))
    return _clamp(
        0.5
        * _stable_float_sum(
            abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0)))
            for key in keys
        )
    )


def _entropy32(distribution: Mapping[str, float]) -> float:
    if not distribution:
        return 0.0
    entropy = _stable_float_sum(
        -distribution[key] * math.log2(distribution[key])
        for key in sorted(distribution)
        if distribution[key] > 0.0
    )
    return _clamp(entropy / 5.0)


def _event_integrity(event: Mapping[str, Any]) -> float:
    try:
        body = dict(event)
        claimed = str(body.pop("event_sha256"))
        if sha256_json(body) != claimed:
            return 0.0
        if sha256_json(event.get("payload")) != event.get("payload_sha256"):
            return 0.0
        _validate_event_body(event)
        return 1.0
    except Exception:
        return 0.0


def _event_descriptor(event: Mapping[str, Any]) -> str:
    payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
    fields = [
        event.get("source_type", ""),
        event.get("source_id", ""),
        payload.get("backend", ""),
        payload.get("job_id", ""),
        payload.get("condition", ""),
        payload.get("packet_sha256", ""),
    ]
    return " ".join(str(value) for value in fields if value)


def initial_r12_state() -> dict[str, Any]:
    vector = {
        "source_integrity": 0.0,
        "temporal_novelty": 0.0,
        "measurement_confidence": 0.0,
        "distribution_energy": 0.0,
        "cross_condition_agreement": 0.0,
        "distribution_entropy": 0.0,
        "surprise": 0.0,
        "memory_relevance": 0.0,
        "retention_pressure": 1.0,
        "contradiction_pressure": 0.0,
        "adaptation_stability": 1.0,
        "reality_coupling": 0.0,
    }
    body = {
        "schema": "zeref-r12-state-v1",
        "formula_version": FORMULA_VERSION,
        "sequence": 0,
        "triggering_event_sha256": ZERO_SHA256,
        "previous_state_sha256": ZERO_SHA256,
        "vector": vector,
        "last_measured_reality_coupling": 0.0,
    }
    state = dict(body)
    state["state_sha256"] = sha256_json(body)
    return state


def derive_r12_transition(
    prior_events: Sequence[Mapping[str, Any]],
    event: Mapping[str, Any],
    previous_state: Mapping[str, Any],
    query: str = "",
) -> dict[str, Any]:
    integrity = _event_integrity(event)
    provenance = str(event.get("provenance_class"))
    confidence = _clamp(float(event.get("confidence", 0.0))) if provenance == "measured" else 0.0
    source_id = str(event.get("source_id", ""))
    novelty = 0.0 if any(str(old.get("source_id", "")) == source_id for old in prior_events) else 1.0

    distribution = _counts_distribution(event)
    energy = (
        _clamp(_stable_float_sum(distribution[key] * distribution[key] for key in sorted(distribution)))
        if distribution
        else 0.0
    )
    entropy = _entropy32(distribution)

    payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
    backend = str(payload.get("backend", ""))
    job_id = str(payload.get("job_id", ""))
    sibling_distributions: list[dict[str, float]] = []
    measured_prior_distributions: list[dict[str, float]] = []
    for old in prior_events:
        if str(old.get("provenance_class")) != "measured":
            continue
        old_distribution = _counts_distribution(old)
        if old_distribution:
            measured_prior_distributions.append(old_distribution)
        old_payload = old.get("payload") if isinstance(old.get("payload"), Mapping) else {}
        if old_distribution and str(old_payload.get("backend", "")) == backend and str(old_payload.get("job_id", "")) == job_id:
            sibling_distributions.append(old_distribution)

    if distribution and sibling_distributions:
        agreement = _clamp(
            _stable_float_sum(1.0 - _tvd(distribution, other) for other in sibling_distributions)
            / len(sibling_distributions)
        )
    elif distribution:
        agreement = 0.5
    else:
        agreement = 0.0

    if distribution and measured_prior_distributions:
        keys = sorted(set().union(*(set(item) for item in measured_prior_distributions), set(distribution)))
        baseline = {
            key: _stable_float_sum(item.get(key, 0.0) for item in measured_prior_distributions)
            / len(measured_prior_distributions)
            for key in keys
        }
        surprise = _tvd(distribution, baseline)
    else:
        surprise = 0.0

    query_tokens = _tokenize(query)
    event_tokens = _tokenize(_event_descriptor(event))
    if query_tokens:
        relevance = len(query_tokens & event_tokens) / max(1, len(query_tokens | event_tokens))
    elif prior_events:
        recent_tokens = _tokenize(_event_descriptor(prior_events[-1]))
        relevance = len(event_tokens & recent_tokens) / max(1, len(event_tokens | recent_tokens)) if event_tokens or recent_tokens else 0.0
    else:
        relevance = 0.5 if event_tokens else 0.0
    relevance = _clamp(relevance)

    contradiction = 0.0
    for old in prior_events:
        if str(old.get("source_id", "")) == source_id and str(old.get("payload_sha256", "")) != str(event.get("payload_sha256", "")):
            contradiction = 1.0
            break

    retention = _clamp(0.8 + 0.2 * surprise)
    first_ten = [
        integrity,
        novelty,
        confidence,
        energy,
        agreement,
        entropy,
        surprise,
        relevance,
        retention,
        contradiction,
    ]
    previous_vector = previous_state.get("vector") if isinstance(previous_state.get("vector"), Mapping) else {}
    if int(previous_state.get("sequence", 0)) == 0:
        stability = 1.0
    else:
        diffs = [abs(value - float(previous_vector.get(name, 0.0))) for name, value in zip(R12_NAMES[:10], first_ten)]
        stability = _clamp(1.0 - _stable_float_sum(diffs) / len(diffs))

    previous_coupling = _clamp(float(previous_vector.get("reality_coupling", 0.0)))
    last_measured = _clamp(float(previous_state.get("last_measured_reality_coupling", previous_coupling)))
    if provenance == "measured":
        quality = integrity * confidence * (1.0 - contradiction) * (0.5 + 0.5 * stability)
        coupling = _clamp(0.65 * previous_coupling + 0.35 * quality)
        last_measured = coupling
    else:
        coupling = min(previous_coupling, last_measured)

    vector = {
        "source_integrity": integrity,
        "temporal_novelty": novelty,
        "measurement_confidence": confidence,
        "distribution_energy": energy,
        "cross_condition_agreement": agreement,
        "distribution_entropy": entropy,
        "surprise": surprise,
        "memory_relevance": relevance,
        "retention_pressure": retention,
        "contradiction_pressure": contradiction,
        "adaptation_stability": stability,
        "reality_coupling": coupling,
    }
    body = {
        "schema": "zeref-r12-state-v1",
        "formula_version": FORMULA_VERSION,
        "sequence": int(previous_state.get("sequence", 0)) + 1,
        "triggering_event_sha256": str(event.get("event_sha256")),
        "previous_state_sha256": str(previous_state.get("state_sha256")),
        "vector": vector,
        "last_measured_reality_coupling": last_measured,
    }
    state = dict(body)
    state["state_sha256"] = sha256_json(body)
    return state


def rebuild_r12(events: Sequence[Mapping[str, Any]], query: str = "") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    state = initial_r12_state()
    history: list[dict[str, Any]] = []
    prior: list[Mapping[str, Any]] = []
    for event in events:
        state = derive_r12_transition(prior, event, state, query=query)
        history.append(state)
        prior.append(event)
    return state, history
