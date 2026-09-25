"""Versioned bounded person/quantum state, separate from model weights or authority."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
import struct

MODES = frozenset((
    "off", "matched_classical", "replay", "sim_unentangled",
    "sim_entangled", "hardware_rigetti", "hardware_ibm",
))
SOURCE_CLASSES = {
    "off": "none",
    "matched_classical": "classical",
    "replay": "replay",
    "sim_unentangled": "simulator",
    "sim_entangled": "simulator",
    "hardware_rigetti": "hardware",
    "hardware_ibm": "hardware",
}
SCHEMA = "quantum-buddy-state-v1"
_HEX = re.compile(r"^[0-9a-f]{64}$")
_USER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_LABEL = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")


class BuddyStateError(ValueError):
    """Invalid untrusted state or provenance; never expose provider credentials."""


def validate_vector12(value, field_name: str) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != 12:
        raise BuddyStateError(f"{field_name} must contain exactly 12 values")
    out = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise BuddyStateError(f"{field_name} must be numeric")
        try:
            number = float(item)
            # The persistence hash is IEEE float32, so reject values that round
            # outside the bounded domain or cannot round-trip to finite f32.
            rounded = struct.unpack("<f", struct.pack("<f", number))[0]
        except (OverflowError, ValueError, struct.error):
            raise BuddyStateError(f"{field_name} has invalid precision") from None
        if not math.isfinite(number) or not math.isfinite(rounded) or abs(number) > 1:
            raise BuddyStateError(f"{field_name} must be finite in [-1,1]")
        out.append(number)
    return tuple(out)


def canonical_vector_sha256(vector) -> str:
    values = validate_vector12(vector, "vector")
    return hashlib.sha256(struct.pack("<12f", *values)).hexdigest()


def _hex_hash(value, label: str) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise BuddyStateError(f"invalid {label}")
    return value


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value) -> datetime:
    if not isinstance(value, str):
        raise BuddyStateError("invalid timestamp")
    try:
        stamp = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise BuddyStateError("invalid timestamp") from None
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise BuddyStateError("timestamp must include timezone")
    return stamp


def _receipt_sha(qstate12, source, mode, source_class, backend, shots,
                 circuit_version, circuit_hash, job_id) -> str:
    receipt = {
        "qstateSha256": canonical_vector_sha256(qstate12),
        "sourceStateSha256": source,
        "mode": mode,
        "sourceClass": source_class,
        "backend": backend,
        "shotCount": shots,
        "circuitVersion": circuit_version,
        "circuitSha256": circuit_hash,
        "jobId": job_id,
    }
    payload = json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class BuddyQuantumState:
    qstate12: tuple[float, ...]
    source_state_sha256: str
    mode: str
    source_class: str
    backend: str
    shot_count: int
    circuit_version: str
    circuit_sha256: str
    result_sha256: str
    job_id: str | None
    created_at: datetime
    valid_until: datetime

    @classmethod
    def create(cls, *, qstate12, source_state_sha256, mode, source_class,
               backend, shot_count, circuit_version, circuit_sha256,
               job_id, valid_for_seconds):
        vector = validate_vector12(qstate12, "qstate12")
        _hex_hash(source_state_sha256, "source state hash")
        _hex_hash(circuit_sha256, "circuit hash")
        if mode not in MODES or SOURCE_CLASSES.get(mode) != source_class:
            raise BuddyStateError("mode/source class mismatch")
        if not isinstance(backend, str) or not _LABEL.fullmatch(backend):
            raise BuddyStateError("invalid backend label")
        if not isinstance(circuit_version, str) or not _LABEL.fullmatch(circuit_version):
            raise BuddyStateError("invalid circuit version")
        if type(shot_count) is not int or not 0 <= shot_count <= 10_000_000:
            raise BuddyStateError("invalid shot count")
        if type(valid_for_seconds) is not int or not 1 <= valid_for_seconds <= 86400:
            raise BuddyStateError("invalid validity window")
        if job_id is not None and (
            not isinstance(job_id, str) or not _LABEL.fullmatch(job_id)
        ):
            raise BuddyStateError("invalid job id")
        if mode in {"off", "matched_classical", "sim_entangled", "sim_unentangled"} and job_id:
            raise BuddyStateError("offline mode must not claim a provider job")
        if mode == "off" and any(vector):
            raise BuddyStateError("off state must be zero")
        now = _utcnow()
        return cls(
            qstate12=vector,
            source_state_sha256=source_state_sha256,
            mode=mode, source_class=source_class, backend=backend,
            shot_count=shot_count, circuit_version=circuit_version,
            circuit_sha256=circuit_sha256,
            result_sha256=_receipt_sha(
                vector, source_state_sha256, mode, source_class, backend,
                shot_count, circuit_version, circuit_sha256, job_id,
            ),
            job_id=job_id, created_at=now,
            valid_until=now + timedelta(seconds=valid_for_seconds),
        )

    def to_document(self) -> dict:
        return {
            "qstate12": list(self.qstate12),
            "sourceStateSha256": self.source_state_sha256,
            "mode": self.mode, "sourceClass": self.source_class,
            "backend": self.backend, "shotCount": self.shot_count,
            "circuitVersion": self.circuit_version,
            "circuitSha256": self.circuit_sha256,
            "resultSha256": self.result_sha256, "jobId": self.job_id,
            "createdAt": self.created_at.isoformat(),
            "validUntil": self.valid_until.isoformat(),
        }

    @classmethod
    def from_document(cls, raw) -> "BuddyQuantumState":
        if not isinstance(raw, dict):
            raise BuddyStateError("invalid qstate document")
        try:
            source = _hex_hash(raw["sourceStateSha256"], "source hash")
            circuit = _hex_hash(raw["circuitSha256"], "circuit hash")
            result = _hex_hash(raw["resultSha256"], "result hash")
            mode, source_class = raw["mode"], raw["sourceClass"]
            vector = validate_vector12(raw["qstate12"], "qstate12")
            shots = raw["shotCount"]
            backend = raw["backend"]
            version = raw["circuitVersion"]
            job_id = raw.get("jobId")
            created, expires = _timestamp(raw["createdAt"]), _timestamp(raw["validUntil"])
        except (KeyError, TypeError):
            raise BuddyStateError("missing qstate provenance") from None
        if mode not in MODES or SOURCE_CLASSES[mode] != source_class:
            raise BuddyStateError("mode/source class mismatch")
        if not isinstance(backend, str) or not _LABEL.fullmatch(backend):
            raise BuddyStateError("invalid backend label")
        if not isinstance(version, str) or not _LABEL.fullmatch(version):
            raise BuddyStateError("invalid circuit version")
        if type(shots) is not int or not 0 <= shots <= 10_000_000:
            raise BuddyStateError("invalid shot count")
        if job_id is not None and (not isinstance(job_id, str) or not _LABEL.fullmatch(job_id)):
            raise BuddyStateError("invalid job id")
        if mode in {"off", "matched_classical", "sim_entangled", "sim_unentangled"} and job_id:
            raise BuddyStateError("offline mode has provider job")
        if mode == "off" and any(vector):
            raise BuddyStateError("off state must be zero")
        if expires <= created:
            raise BuddyStateError("invalid validity window")
        recomputed = _receipt_sha(vector, source, mode, source_class, backend,
                                  shots, version, circuit, job_id)
        if recomputed != result:
            raise BuddyStateError("result provenance hash mismatch")
        return cls(vector, source, mode, source_class, backend, shots, version,
                   circuit, result, job_id, created, expires)


@dataclass(frozen=True)
class BuddyCurrentState:
    user_id: str
    state_version: int
    dyn12: tuple[float, ...]
    dyn12_sha256: str
    qstate: BuddyQuantumState | None
    qstate_valid: bool
    state_conditioning_consent: bool
    quantum_refresh_consent: bool

    @classmethod
    def new(cls, *, user_id, dyn12, state_version,
            state_conditioning_consent=False, quantum_refresh_consent=False):
        if not isinstance(user_id, str) or not _USER.fullmatch(user_id):
            raise BuddyStateError("invalid opaque user id")
        if type(state_version) is not int or not 0 <= state_version < 2**63:
            raise BuddyStateError("invalid state version")
        vector = validate_vector12(dyn12, "dyn12")
        if type(state_conditioning_consent) is not bool or type(quantum_refresh_consent) is not bool:
            raise BuddyStateError("consent must be explicit boolean")
        return cls(
            user_id=user_id, state_version=state_version, dyn12=vector,
            dyn12_sha256=canonical_vector_sha256(vector), qstate=None,
            qstate_valid=False,
            state_conditioning_consent=state_conditioning_consent,
            quantum_refresh_consent=quantum_refresh_consent,
        )

    def with_qstate(self, qstate: BuddyQuantumState, *, now=None) -> "BuddyCurrentState":
        if not isinstance(qstate, BuddyQuantumState):
            raise BuddyStateError("invalid qstate")
        if qstate.source_state_sha256 != self.dyn12_sha256:
            raise BuddyStateError("qstate source mismatch")
        stamp = _utcnow() if now is None else now
        if stamp.tzinfo is None or stamp.utcoffset() is None or stamp >= qstate.valid_until:
            raise BuddyStateError("qstate expired or invalid time")
        return replace(self, qstate=qstate, qstate_valid=True)

    def to_document(self) -> dict:
        quantum = (
            self.qstate.to_document() if self.qstate is not None else {
                "mode": "off", "sourceClass": "none",
                "backend": None, "jobId": None, "shotCount": 0,
                "circuitVersion": "qb-v1",
                "circuitSha256": None, "sourceStateSha256": None,
                "resultSha256": None, "createdAt": None, "validUntil": None,
            }
        )
        quantum.pop("qstate12", None)
        return {
            "id": "current", "userId": self.user_id, "schema": SCHEMA,
            "stateVersion": self.state_version,
            "dyn12": list(self.dyn12), "dyn12Sha256": self.dyn12_sha256,
            "qstate12": list(self.qstate.qstate12) if self.qstate else [0.0] * 12,
            "qstateValid": self.qstate_valid,
            "quantum": quantum,
            "consent": {
                "stateConditioning": self.state_conditioning_consent,
                "quantumRefresh": self.quantum_refresh_consent,
            },
        }

    @classmethod
    def from_document(cls, raw) -> "BuddyCurrentState":
        if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or raw.get("id") != "current":
            raise BuddyStateError("wrong buddy schema or item id")
        consent = raw.get("consent")
        if not isinstance(consent, dict):
            raise BuddyStateError("missing consent contract")
        state = cls.new(
            user_id=raw.get("userId"), dyn12=raw.get("dyn12"),
            state_version=raw.get("stateVersion"),
            state_conditioning_consent=consent.get("stateConditioning"),
            quantum_refresh_consent=consent.get("quantumRefresh"),
        )
        if state.dyn12_sha256 != raw.get("dyn12Sha256"):
            raise BuddyStateError("dyn12 hash mismatch")
        if type(raw.get("qstateValid")) is not bool:
            raise BuddyStateError("invalid qstate validity")
        if raw["qstateValid"] is False:
            validate_vector12(raw.get("qstate12"), "qstate12")
            return state
        quantum = raw.get("quantum")
        if not isinstance(quantum, dict):
            raise BuddyStateError("missing qstate provenance")
        q = BuddyQuantumState.from_document({
            **quantum, "qstate12": raw.get("qstate12"),
        })
        return state.with_qstate(q)
