"""Immutable evidence and episodic-memory manifests for Descendant-001."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping

from .hashing import canonical_json, sha256_bytes

ZERO_SHA256 = "0" * 64
_VALID_PROMOTION = {"UNREVIEWED", "PROMOTED", "QUARANTINED", "BLOCKED_INVALID", "REJECTED"}


def _require_sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower()):
        raise ValueError(f"{name} must be a 64-character SHA-256 hex digest")


@dataclass(frozen=True)
class RunEvidenceManifest:
    """Provenance record for one experimental run or frozen artifact."""

    run_id: str
    source_kind: str
    source_ref: str
    source_sha256: str
    repo_commit: str
    configured_duration_seconds: int
    observed_duration_seconds: float | None
    verdict: str
    validity: str
    evidence_hashes: Mapping[str, str] = field(default_factory=dict)
    early_stop_reason: str | None = None
    workflow_conclusion: str | None = None
    experiment_step_conclusion: str | None = None
    publication_conclusion: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id is required")
        if not self.source_kind.strip() or not self.source_ref.strip():
            raise ValueError("source identity is required")
        _require_sha256("source_sha256", self.source_sha256)
        if len(self.repo_commit) != 40:
            raise ValueError("repo_commit must be a 40-character git commit SHA")
        if self.configured_duration_seconds <= 0:
            raise ValueError("configured duration must be positive")
        if self.observed_duration_seconds is not None and self.observed_duration_seconds < 0:
            raise ValueError("observed duration cannot be negative")
        if self.validity == "VALID" and self.observed_duration_seconds is None and not self.early_stop_reason:
            raise ValueError("VALID evidence requires observed duration or an approved early-stop reason")
        if not self.verdict.strip() or not self.validity.strip():
            raise ValueError("verdict and validity are required")
        if not self.evidence_hashes:
            raise ValueError("evidence hashes are required")
        for name, digest in self.evidence_hashes.items():
            if not name:
                raise ValueError("evidence hash names cannot be empty")
            _require_sha256(f"evidence hash {name}", digest)

    def to_dict(self) -> dict:
        value = asdict(self)
        value["evidence_hashes"] = dict(sorted(self.evidence_hashes.items()))
        return value

    @property
    def manifest_sha256(self) -> str:
        return sha256_bytes(canonical_json(self.to_dict()))


@dataclass(frozen=True)
class EpisodeManifest:
    """Durable episodic-memory pointer derived from run evidence."""

    run_id: str
    source_kind: str
    source_sha256: str
    validity: str
    configured_duration_seconds: int
    observed_duration_seconds: float | None
    training_promotion: str = "UNREVIEWED"
    source_ref: str = ""
    repo_commit: str = ""
    evidence_manifest_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id is required")
        _require_sha256("source_sha256", self.source_sha256)
        if self.training_promotion not in _VALID_PROMOTION:
            raise ValueError(f"unknown training promotion: {self.training_promotion}")
        if self.configured_duration_seconds <= 0:
            raise ValueError("configured duration must be positive")
        if self.observed_duration_seconds is not None and self.observed_duration_seconds < 0:
            raise ValueError("observed duration cannot be negative")
        if self.repo_commit and len(self.repo_commit) != 40:
            raise ValueError("repo_commit must be a 40-character git commit SHA")
        if self.evidence_manifest_sha256 is not None:
            _require_sha256("evidence_manifest_sha256", self.evidence_manifest_sha256)

    def to_dict(self) -> dict:
        return asdict(self)



def episode_from_run(run: RunEvidenceManifest) -> EpisodeManifest:
    promotion = "UNREVIEWED" if run.validity == "VALID" else "BLOCKED_INVALID"
    return EpisodeManifest(
        run_id=run.run_id,
        source_kind=run.source_kind,
        source_sha256=run.source_sha256,
        validity=run.validity,
        configured_duration_seconds=run.configured_duration_seconds,
        observed_duration_seconds=run.observed_duration_seconds,
        training_promotion=promotion,
        source_ref=run.source_ref,
        repo_commit=run.repo_commit,
        evidence_manifest_sha256=run.manifest_sha256,
    )


def _read_last_hash(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return ZERO_SHA256
    last = None
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last = json.loads(line)
    if last is None:
        return ZERO_SHA256
    digest = str(last.get("record_sha256", ""))
    _require_sha256("record_sha256", digest)
    return digest


def append_episode(path: str | Path, episode: EpisodeManifest) -> str:
    """Append one hash-chained episode. Existing records are never rewritten."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = _read_last_hash(path)
    unsigned = episode.to_dict()
    unsigned["previous_record_sha256"] = previous
    digest = sha256_bytes(canonical_json(unsigned))
    record = dict(unsigned)
    record["record_sha256"] = digest
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return digest


def verify_episode_index(path: str | Path) -> dict[str, object]:
    path = Path(path)
    previous = ZERO_SHA256
    records = 0
    if not path.exists():
        return {"valid": True, "records": 0, "final_sha256": previous}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            claimed = record.pop("record_sha256", "")
            if record.get("previous_record_sha256") != previous:
                return {"valid": False, "records": records, "error": f"chain break at line {line_no}"}
            expected = sha256_bytes(canonical_json(record))
            if claimed != expected:
                return {"valid": False, "records": records, "error": f"hash mismatch at line {line_no}"}
            previous = claimed
            records += 1
    return {"valid": True, "records": records, "final_sha256": previous}
