from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Literal, Mapping

from beastbox.events import normalize_event
from beastbox.hashutil import canonical_json, sha256_obj, sha256_text

ControlMode = Literal["measured", "pseudorandom", "zero", "shuffled"]

BASIS = ("00", "01", "10", "11")
TRANSFORM = "q12-basis-digest-v1"
RECEIPT_SCHEMA = "zeref-phos-quantum-control-receipt-v1"
CANONICAL_EVENT_SCHEMA = "zeref-phos-canonical-quantum-event-v1"
DEFAULT_SEED = "zeref-phos-qcontrol-v1"

_SECRET_KEYS = {"token", "password", "secret", "credential", "api_key"}
_LABEL_RE = re.compile(r"[A-Za-z0-9_.:-]{1,256}")
_SHA256_RE = re.compile(r"[a-f0-9]{64}")

_IBM_KEYS = {
    "source",
    "mode",
    "result_kind",
    "native_job_id",
    "backend",
    "shots",
    "counts",
    "circuit_sha256",
    "probe",
}
_AZURE_KEYS = {
    "source",
    "mode",
    "result_kind",
    "native_job_id",
    "backend",
    "shots_requested",
    "probabilities",
    "circuit_sha256",
    "probe",
}
_PROVIDER_KEYS = {"source", "mode", "native_job_id", "backend", "circuit_sha256", "probe"}
_RECEIPT_KEYS = {
    "schema",
    "transform",
    "mode",
    "source_event_sha256",
    "provider",
    "result_kind",
    "probabilities",
    "vector",
    "control",
    "claim_boundary",
    "receipt_sha256",
}


def _reject_secret_like_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _SECRET_KEYS:
                raise ValueError(f"secret-like field is forbidden: {key}")
            _reject_secret_like_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_secret_like_keys(child)


def _label(value: Any, field: str) -> str:
    if not isinstance(value, str) or _LABEL_RE.fullmatch(value) is None:
        raise ValueError(f"invalid provider metadata: {field}")
    return value


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"invalid provider metadata: {field}")
    return value


def _bounded_shots(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 1024:
        raise ValueError(f"invalid provider metadata: {field}")
    return value


def _canonical_probabilities(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping) or not value or len(value) > 4:
        raise ValueError("invalid probabilities")
    probabilities: dict[str, float] = {}
    for key, raw in value.items():
        if key not in BASIS or isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError("invalid probabilities")
        number = float(raw)
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            raise ValueError("invalid probabilities")
        probabilities[str(key)] = number
    if not math.isclose(sum(probabilities.values()), 1.0, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError("invalid probabilities")
    return {key: probabilities.get(key, 0.0) for key in BASIS}


def _probabilities_from_counts(counts: Any, shots: int) -> tuple[dict[str, int], dict[str, float]]:
    if not isinstance(counts, Mapping) or not counts or len(counts) > 4:
        raise ValueError("invalid counts")
    normalized: dict[str, int] = {}
    for key, value in counts.items():
        if key not in BASIS or isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("invalid counts")
        normalized[str(key)] = value
    if sum(normalized.values()) != shots:
        raise ValueError("invalid counts")
    ordered_counts = {key: normalized[key] for key in BASIS if key in normalized}
    probabilities = {key: normalized.get(key, 0) / shots for key in BASIS}
    return ordered_counts, probabilities


def _provider(metadata: Mapping[str, Any]) -> dict[str, str]:
    return {
        "source": _label(metadata.get("source"), "source"),
        "mode": _label(metadata.get("mode"), "mode"),
        "native_job_id": _label(metadata.get("native_job_id"), "native_job_id"),
        "backend": _label(metadata.get("backend"), "backend"),
        "circuit_sha256": _sha256(metadata.get("circuit_sha256"), "circuit_sha256"),
        "probe": _label(metadata.get("probe"), "probe"),
    }


def _features_match(features: Any, probabilities: Mapping[str, float]) -> bool:
    if not isinstance(features, list) or len(features) != 4:
        return False
    expected = [2.0 * probabilities[key] - 1.0 for key in BASIS]
    return all(
        isinstance(actual, (int, float))
        and not isinstance(actual, bool)
        and math.isfinite(float(actual))
        and math.isclose(float(actual), wanted, rel_tol=0.0, abs_tol=1e-12)
        for actual, wanted in zip(features, expected)
    )


def canonicalize_quantum_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and canonicalize one already-authorized bounded quantum event.

    This function never submits a provider job and never reads credentials. It
    only accepts the strict software-event contract produced by
    ``optional_resources.quantum_event``.
    """

    normalized = normalize_event(event)
    if normalized["source"] != "software-event":
        raise ValueError("quantum control requires a software-event")
    try:
        metadata = json.loads(normalized["text"])
    except json.JSONDecodeError as exc:
        raise ValueError("invalid provider metadata JSON") from exc
    if not isinstance(metadata, dict):
        raise ValueError("provider metadata must be an object")
    _reject_secret_like_keys(metadata)

    source = metadata.get("source")
    if source == "ibm-quantum":
        if set(metadata) != _IBM_KEYS or metadata.get("mode") != "REAL_IBM" or metadata.get("result_kind") != "observed-counts":
            raise ValueError("invalid provider metadata for IBM")
        shots = _bounded_shots(metadata.get("shots"), "shots")
        counts, probabilities = _probabilities_from_counts(metadata.get("counts"), shots)
        observation: dict[str, Any] = {"shots": shots, "counts": counts}
        result_kind = "observed-counts"
    elif source == "azure-quantum":
        if (
            set(metadata) != _AZURE_KEYS
            or metadata.get("mode") != "AZURE_IONQ_SIMULATOR"
            or metadata.get("result_kind") != "probabilities"
        ):
            raise ValueError("invalid provider metadata for Azure")
        shots_requested = _bounded_shots(metadata.get("shots_requested"), "shots_requested")
        probabilities = _canonical_probabilities(metadata.get("probabilities"))
        observation = {"shots_requested": shots_requested, "probabilities": probabilities}
        result_kind = "probabilities"
    else:
        raise ValueError("invalid provider metadata source")

    provider = _provider(metadata)
    if not _features_match(normalized["features"], probabilities):
        raise ValueError("event features do not match canonical probabilities")

    payload: dict[str, Any] = {
        "schema": CANONICAL_EVENT_SCHEMA,
        "provider": provider,
        "result_kind": result_kind,
        "observation": observation,
        "probabilities": probabilities,
    }
    return {**payload, "source_event_sha256": sha256_obj(payload)}


def _digest_tail(provider: Mapping[str, str], probabilities: Mapping[str, float]) -> list[float]:
    material = {
        "transform": TRANSFORM,
        "circuit_sha256": provider["circuit_sha256"],
        "probe": provider["probe"],
        "probabilities": dict(probabilities),
    }
    digest = hashlib.sha256(canonical_json(material).encode("utf-8")).digest()
    values: list[float] = []
    for index in range(4):
        raw = int.from_bytes(digest[index * 2 : index * 2 + 2], "big")
        values.append(2.0 * (raw / 65535.0) - 1.0)
    return values


def _measured_vector(provider: Mapping[str, str], probabilities: Mapping[str, float]) -> list[float]:
    p00, p01, p10, p11 = (probabilities[key] for key in BASIS)
    vector = [
        2.0 * p00 - 1.0,
        2.0 * p01 - 1.0,
        2.0 * p10 - 1.0,
        2.0 * p11 - 1.0,
        (p00 + p01) - (p10 + p11),
        (p00 + p10) - (p01 + p11),
        (p00 + p11) - (p01 + p10),
        1.0 - 2.0 * sum(value * value for value in (p00, p01, p10, p11)),
    ]
    vector.extend(_digest_tail(provider, probabilities))
    return [max(-1.0, min(1.0, float(value))) for value in vector]


def _permuted_control(values: list[float], *, seed: str, source_event_sha256: str) -> list[float]:
    if not isinstance(seed, str) or not seed.strip() or len(seed) > 256:
        raise ValueError("seed must be a non-empty string of at most 256 characters")
    order = sorted(
        range(len(values)),
        key=lambda index: sha256_text(f"{seed}:{source_event_sha256}:{index}"),
    )
    permuted = [values[index] for index in order]
    if permuted == values and len(permuted) > 1:
        permuted = permuted[1:] + permuted[:1]
    return permuted


def _claim_boundary() -> dict[str, bool]:
    return {
        "quantum_advantage_established": False,
        "semantic_world_knowledge_from_quantum": False,
        "runtime_authority_transferred": False,
    }


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "receipt_sha256": sha256_obj(payload)}


def build_quantum_control_receipt(
    event: Mapping[str, Any],
    *,
    mode: ControlMode = "measured",
    seed: str = DEFAULT_SEED,
    donor_event: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one deterministic A/B/C/D quantum-control receipt."""

    if mode not in ("measured", "pseudorandom", "zero", "shuffled"):
        raise ValueError("mode must be measured, pseudorandom, zero, or shuffled")
    canonical = canonicalize_quantum_event(event)
    measured = _measured_vector(canonical["provider"], canonical["probabilities"])
    control: dict[str, Any]

    if mode == "measured":
        vector = measured
        control = {}
    elif mode == "pseudorandom":
        vector = _permuted_control(measured, seed=seed, source_event_sha256=canonical["source_event_sha256"])
        control = {"seed": seed, "distribution_match": "exact-value-multiset"}
    elif mode == "zero":
        vector = [0.0] * 12
        control = {}
    else:
        if donor_event is None:
            raise ValueError("shuffled mode requires a donor_event")
        donor = canonicalize_quantum_event(donor_event)
        if donor["source_event_sha256"] == canonical["source_event_sha256"]:
            raise ValueError("shuffled mode requires a distinct donor event")
        donor_vector = _measured_vector(donor["provider"], donor["probabilities"])
        vector = donor_vector
        donor_measured_payload = {
            "schema": RECEIPT_SCHEMA,
            "transform": TRANSFORM,
            "mode": "measured",
            "source_event_sha256": donor["source_event_sha256"],
            "provider": donor["provider"],
            "result_kind": donor["result_kind"],
            "probabilities": donor["probabilities"],
            "vector": donor_vector,
            "control": {},
            "claim_boundary": _claim_boundary(),
        }
        donor_receipt = _seal(donor_measured_payload)
        control = {
            "donor_event_sha256": donor["source_event_sha256"],
            "donor_receipt_sha256": donor_receipt["receipt_sha256"],
            "donor_vector_sha256": sha256_obj(donor_vector),
        }

    payload = {
        "schema": RECEIPT_SCHEMA,
        "transform": TRANSFORM,
        "mode": mode,
        "source_event_sha256": canonical["source_event_sha256"],
        "provider": canonical["provider"],
        "result_kind": canonical["result_kind"],
        "probabilities": canonical["probabilities"],
        "vector": vector,
        "control": control,
        "claim_boundary": _claim_boundary(),
    }
    receipt = _seal(payload)
    verify_quantum_control_receipt(receipt)
    return receipt


def _validate_receipt_probabilities(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping) or set(value) != set(BASIS):
        raise ValueError("receipt probabilities must contain the four basis states")
    return _canonical_probabilities(value)


def _validate_vector(value: Any) -> list[float]:
    if not isinstance(value, list) or len(value) != 12:
        raise ValueError("receipt vector must contain 12 values")
    vector: list[float] = []
    for raw in value:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError("receipt vector must contain finite values in [-1, 1]")
        number = float(raw)
        if not math.isfinite(number) or not -1.0 <= number <= 1.0:
            raise ValueError("receipt vector must contain finite values in [-1, 1]")
        vector.append(number)
    return vector


def verify_quantum_control_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Verify structural integrity and the deterministic control transform."""

    _reject_secret_like_keys(receipt)
    if set(receipt) != _RECEIPT_KEYS:
        raise ValueError("unexpected quantum control receipt fields")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("unexpected quantum control receipt schema")
    if receipt.get("transform") != TRANSFORM:
        raise ValueError("unsupported quantum control transform")

    recorded_sha = receipt.get("receipt_sha256")
    if not isinstance(recorded_sha, str) or _SHA256_RE.fullmatch(recorded_sha) is None:
        raise ValueError("invalid receipt SHA-256")
    payload = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    actual_sha = sha256_obj(payload)
    if actual_sha != recorded_sha:
        raise RuntimeError(f"receipt SHA-256 mismatch: {actual_sha} != {recorded_sha}")

    mode = receipt.get("mode")
    if mode not in ("measured", "pseudorandom", "zero", "shuffled"):
        raise ValueError("invalid quantum control mode")
    source_sha = receipt.get("source_event_sha256")
    if not isinstance(source_sha, str) or _SHA256_RE.fullmatch(source_sha) is None:
        raise ValueError("invalid source event SHA-256")

    provider = receipt.get("provider")
    if not isinstance(provider, Mapping) or set(provider) != _PROVIDER_KEYS:
        raise ValueError("invalid receipt provider metadata")
    provider_values = {
        "source": _label(provider.get("source"), "source"),
        "mode": _label(provider.get("mode"), "mode"),
        "native_job_id": _label(provider.get("native_job_id"), "native_job_id"),
        "backend": _label(provider.get("backend"), "backend"),
        "circuit_sha256": _sha256(provider.get("circuit_sha256"), "circuit_sha256"),
        "probe": _label(provider.get("probe"), "probe"),
    }
    result_kind = receipt.get("result_kind")
    if provider_values["source"] == "ibm-quantum":
        if provider_values["mode"] != "REAL_IBM" or result_kind != "observed-counts":
            raise ValueError("invalid receipt provider metadata")
    elif provider_values["source"] == "azure-quantum":
        if provider_values["mode"] != "AZURE_IONQ_SIMULATOR" or result_kind != "probabilities":
            raise ValueError("invalid receipt provider metadata")
    else:
        raise ValueError("invalid receipt provider metadata")

    probabilities = _validate_receipt_probabilities(receipt.get("probabilities"))
    vector = _validate_vector(receipt.get("vector"))
    control = receipt.get("control")
    if not isinstance(control, Mapping):
        raise ValueError("receipt control must be an object")
    claims = receipt.get("claim_boundary")
    if claims != _claim_boundary():
        raise ValueError("unexpected quantum control claim boundary")

    measured = _measured_vector(provider_values, probabilities)
    if mode == "measured":
        if control or vector != measured:
            raise ValueError("measured receipt vector/control mismatch")
    elif mode == "pseudorandom":
        if set(control) != {"seed", "distribution_match"} or control.get("distribution_match") != "exact-value-multiset":
            raise ValueError("invalid pseudorandom control metadata")
        seed = control.get("seed")
        if not isinstance(seed, str):
            raise ValueError("invalid pseudorandom control seed")
        expected = _permuted_control(measured, seed=seed, source_event_sha256=source_sha)
        if vector != expected:
            raise ValueError("pseudorandom control vector mismatch")
    elif mode == "zero":
        if control or vector != [0.0] * 12:
            raise ValueError("zero control vector/control mismatch")
    else:
        expected_keys = {"donor_event_sha256", "donor_receipt_sha256", "donor_vector_sha256"}
        if set(control) != expected_keys:
            raise ValueError("invalid shuffled control metadata")
        donor_event_sha = control.get("donor_event_sha256")
        donor_receipt_sha = control.get("donor_receipt_sha256")
        donor_vector_sha = control.get("donor_vector_sha256")
        for value, field in (
            (donor_event_sha, "donor event"),
            (donor_receipt_sha, "donor receipt"),
            (donor_vector_sha, "donor vector"),
        ):
            if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
                raise ValueError(f"invalid {field} SHA-256")
        if donor_event_sha == source_sha:
            raise ValueError("shuffled control donor must be distinct")
        if donor_vector_sha != sha256_obj(vector):
            raise ValueError("shuffled donor vector SHA-256 mismatch")

    return {"verified": True, "mode": str(mode), "source_event_sha256": source_sha}
