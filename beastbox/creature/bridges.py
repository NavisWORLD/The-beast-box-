from __future__ import annotations

import hashlib
import json
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

_SECRET_FRAGMENTS = ("token", "secret", "password", "passwd", "api_key", "apikey", "credential")
_ALLOWED_SECRET_METADATA_KEYS = {"secret_exposed_to_subject", "credential_exposed_to_subject"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _secret_like_key(value: Any, path: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if key not in _ALLOWED_SECRET_METADATA_KEYS and any(fragment in lowered for fragment in _SECRET_FRAGMENTS):
                return f"{path}.{key}"
            found = _secret_like_key(child, f"{path}.{key}")
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found = _secret_like_key(child, f"{path}[{index}]")
            if found:
                return found
    return None


def _digest_ok(value: str) -> bool:
    text = str(value).lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


@dataclass(frozen=True)
class BridgeReceipt:
    provider: str
    source: str
    generated_at: int
    expires_at: int
    state12: Sequence[float]
    provenance_sha256: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    credential_exposed_to_subject: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cosmos.bridge-receipt.v1",
            "provider": self.provider,
            "source": self.source,
            "generated_at": int(self.generated_at),
            "expires_at": int(self.expires_at),
            "state12": [float(x) for x in self.state12],
            "provenance_sha256": self.provenance_sha256,
            "metadata": dict(self.metadata),
            "credential_exposed_to_subject": bool(self.credential_exposed_to_subject),
        }


def validate_receipt(
    receipt: BridgeReceipt,
    *,
    now: int | float | None = None,
    require_fresh: bool = False,
) -> BridgeReceipt:
    if not str(receipt.provider).strip():
        raise ValueError("bridge provider is required")
    if not str(receipt.source).strip():
        raise ValueError("bridge source is required")
    vector = [float(x) for x in receipt.state12]
    if len(vector) != 12:
        raise ValueError("bridge state12 must contain exactly 12 values")
    if not all(math.isfinite(x) for x in vector):
        raise ValueError("bridge state12 values must be finite")
    if not _digest_ok(receipt.provenance_sha256):
        raise ValueError("bridge provenance_sha256 must be a SHA-256 hex digest")
    if int(receipt.expires_at) < int(receipt.generated_at):
        raise ValueError("bridge expires_at precedes generated_at")
    if receipt.credential_exposed_to_subject:
        raise ValueError("bridge credential exposure flag must remain false")
    secret_path = _secret_like_key(dict(receipt.metadata))
    if secret_path:
        raise ValueError(f"secret-like bridge metadata rejected: {secret_path}")
    if require_fresh:
        current = int(time.time() if now is None else now)
        if current > int(receipt.expires_at):
            raise ValueError("bridge receipt expired")
    return receipt


def classical_receipt(
    seed: int,
    *,
    now: int | float | None = None,
    ttl_seconds: int = 3600,
) -> BridgeReceipt:
    generated = int(time.time() if now is None else now)
    rng = random.Random(int(seed))
    vector = [2.0 * rng.random() - 1.0 for _ in range(12)]
    provenance = hashlib.sha256(_canonical({"provider": "classical", "seed": int(seed), "state12": vector})).hexdigest()
    return validate_receipt(BridgeReceipt(
        provider="classical",
        source="deterministic-prng",
        generated_at=generated,
        expires_at=generated + max(0, int(ttl_seconds)),
        state12=vector,
        provenance_sha256=provenance,
        metadata={"seed": int(seed)},
    ))


def ibm_receipt_from_resident(value: Mapping[str, Any]) -> BridgeReceipt:
    raw = dict(value)
    secret_path = _secret_like_key(raw)
    if secret_path and not secret_path.endswith(".secret_exposed_to_subject"):
        raise ValueError(f"secret-like IBM receipt key rejected: {secret_path}")
    if raw.get("authenticated") is not True:
        raise ValueError("IBM resident receipt is not authenticated")
    if raw.get("secret_exposed_to_subject") is not False:
        raise ValueError("IBM resident receipt exposed a credential to the subject")
    entropy = [float(x) for x in raw.get("entropy12", [])]
    provenance = str(raw.get("entropy_source_sha256", ""))
    receipt = BridgeReceipt(
        provider="ibm",
        source=str(raw.get("source", "ibm-runtime")),
        generated_at=int(raw.get("generated_at", 0)),
        expires_at=int(raw.get("expires_at", 0)),
        state12=entropy,
        provenance_sha256=provenance,
        metadata={
            "backend": raw.get("backend"),
            "job_id": raw.get("job_id"),
            "job_status": raw.get("job_status"),
            "counts_sha256": raw.get("counts_sha256"),
        },
    )
    return validate_receipt(receipt)


def azure_receipt_from_payload(value: Mapping[str, Any]) -> BridgeReceipt:
    raw = dict(value)
    secret_path = _secret_like_key(raw)
    if secret_path:
        raise ValueError(f"secret-like Azure payload key rejected: {secret_path}")
    receipt = BridgeReceipt(
        provider="azure",
        source=str(raw.get("source", "azure")),
        generated_at=int(raw.get("generated_at", 0)),
        expires_at=int(raw.get("expires_at", 0)),
        state12=[float(x) for x in raw.get("state12", [])],
        provenance_sha256=str(raw.get("provenance_sha256", "")),
        metadata=dict(raw.get("metadata") or {}),
    )
    return validate_receipt(receipt)
