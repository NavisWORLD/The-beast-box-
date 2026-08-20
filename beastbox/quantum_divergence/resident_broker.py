from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from beastbox.quantum import IBMReceipt, _bitarray_counts, service_from_token

from .entropy import quantum_entropy_from_counts

_SCHEMA = "synapse.zeref.ibm-receipt.v1"
_SECRET_KEY_FRAGMENTS = ("token", "secret", "password", "passwd", "api_key", "apikey", "credential")
_ALLOWED_SECRET_METADATA_KEYS = {"secret_exposed_to_subject"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _find_secret_like_key(value: Any, path: str = "$") -> str | None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if key not in _ALLOWED_SECRET_METADATA_KEYS and any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
                return f"{path}.{key}"
            found = _find_secret_like_key(child, f"{path}.{key}")
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found = _find_secret_like_key(child, f"{path}[{index}]")
            if found:
                return found
    return None


def validate_sanitized_receipt(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("IBM resident receipt must be a JSON object")
    secret_key = _find_secret_like_key(value)
    if secret_key:
        raise ValueError(f"secret-like receipt key rejected: {secret_key}")

    required = {
        "schema",
        "authenticated",
        "backend",
        "job_id",
        "job_status",
        "source",
        "generated_at",
        "expires_at",
        "entropy12",
        "entropy_source_sha256",
        "counts_sha256",
        "secret_exposed_to_subject",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ValueError("IBM resident receipt missing: " + ", ".join(missing))
    if value["schema"] != _SCHEMA:
        raise ValueError("unsupported IBM resident receipt schema")
    if value["authenticated"] is not True:
        raise ValueError("IBM resident receipt must be authenticated")
    if value["secret_exposed_to_subject"] is not False:
        raise ValueError("secret_exposed_to_subject must be false")
    backend = str(value["backend"])
    if not backend or "simulator" in backend.lower() or backend.lower().startswith(("aer", "fake")):
        raise ValueError("IBM resident receipt requires a real hardware backend")
    vector = [float(x) for x in value["entropy12"]]
    if len(vector) != 12:
        raise ValueError("IBM resident receipt entropy12 must contain exactly 12 values")
    for key in ("entropy_source_sha256", "counts_sha256"):
        digest = str(value[key]).lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError(f"{key} must be a SHA-256 hex digest")
    generated = int(value["generated_at"])
    expires = int(value["expires_at"])
    if expires < generated:
        raise ValueError("IBM resident receipt expires_at precedes generated_at")
    return dict(value)


def build_sanitized_receipt(
    receipt: IBMReceipt,
    counts: dict[str, int],
    *,
    job_status: str,
    now: int | float | None = None,
    ttl_seconds: int = 3600,
) -> dict[str, Any]:
    generated_at = int(time.time() if now is None else now)
    ttl = max(0, int(ttl_seconds))
    clean_counts = {str(k).replace(" ", ""): int(v) for k, v in counts.items()}
    entropy = quantum_entropy_from_counts(clean_counts, receipt.to_dict(), dimensions=12)
    value = {
        "schema": _SCHEMA,
        "authenticated": True,
        "backend": str(receipt.backend),
        "job_id": str(receipt.job_id),
        "job_status": str(job_status),
        "source": "ibm-runtime",
        "generated_at": generated_at,
        "expires_at": generated_at + ttl,
        "entropy12": [float(x) for x in entropy.vector],
        "entropy_source_sha256": entropy.source_sha256,
        "counts_sha256": hashlib.sha256(_canonical(clean_counts)).hexdigest(),
        "shots": int(receipt.shots),
        "circuit_sha256": str(receipt.circuit_sha256),
        "secret_exposed_to_subject": False,
    }
    return validate_sanitized_receipt(value)


def refresh_existing_job(
    *,
    token: str,
    job_id: str,
    backend: str,
    shots: int,
    circuit_sha256: str,
    instance: str | None = None,
    ttl_seconds: int = 3600,
) -> dict[str, Any]:
    """Retrieve one already-approved IBM job and emit only sanitized provenance.

    This never submits a new workload. The caller supplies the credential directly
    from an isolated broker process; it is not written to environment variables.
    """
    service = service_from_token(token, instance=instance)
    job = service.job(str(job_id))
    status_attr = getattr(job, "status", None)
    status_value = status_attr() if callable(status_attr) else status_attr
    result = job.result()
    if not result:
        raise RuntimeError("IBM resident job returned no primitive result")
    counts = _bitarray_counts(result[0].data)
    receipt = IBMReceipt(
        job_id=str(job_id),
        backend=str(backend),
        shots=int(shots),
        circuit_sha256=str(circuit_sha256),
        pubs=1,
    )
    return build_sanitized_receipt(
        receipt,
        counts,
        job_status=str(status_value or "UNKNOWN"),
        ttl_seconds=ttl_seconds,
    )
