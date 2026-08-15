"""Guarded descendant stage planning and GENESIS ancestry manifests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping

_ALLOWED_STAGES = {"CORPUS-CLEAN", "MEMORY", "QUANTUM", "TWIN"}


def _sha_ok(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class StageInputs:
    manifest_hashes: Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.manifest_hashes:
            raise ValueError("at least one input manifest hash is required")
        for name, digest in self.manifest_hashes.items():
            if not name.strip() or not _sha_ok(digest):
                raise ValueError("every input manifest must have a valid SHA-256")

    @property
    def combined_sha256(self) -> str:
        return _sha(dict(sorted(self.manifest_hashes.items())))


@dataclass(frozen=True)
class StagePlan:
    stage: str
    status: str
    seed: int
    parent_checkpoint_sha256: str | None
    input_manifest_sha256: str
    manifest_hashes: Mapping[str, str]

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["manifest_hashes"] = dict(sorted(self.manifest_hashes.items()))
        return value

    @property
    def plan_sha256(self) -> str:
        return _sha(self.to_dict())


def create_genesis_manifest(
    *,
    prime_gguf_sha256: str,
    canonical_checkpoint_sha256: str,
    reconstruction_proof_sha256: str,
    training_allowed: bool,
) -> dict[str, object]:
    for name, digest in (
        ("prime_gguf_sha256", prime_gguf_sha256),
        ("canonical_checkpoint_sha256", canonical_checkpoint_sha256),
        ("reconstruction_proof_sha256", reconstruction_proof_sha256),
    ):
        if not _sha_ok(digest):
            raise ValueError(f"{name} must be a SHA-256")
    manifest = {
        "schema": "d001-genesis-v1",
        "parent_prime_gguf_sha256": prime_gguf_sha256,
        "trainable_parent_sha256": canonical_checkpoint_sha256,
        "reconstruction_proof_sha256": reconstruction_proof_sha256,
        "parent_kind": "canonical-trainable-reconstruction",
        "canonical_reconstruction": True,
        "historical_raw_parameters_recovered": False,
        "historical_optimizer_continuity": False,
        "training_allowed": bool(training_allowed),
        "quantum_source_inherited_from_prime": "unknown_from_prime_artifact",
    }
    manifest["manifest_sha256"] = _sha(manifest)
    return manifest


def plan_stage(
    *,
    stage: str,
    parent_training_allowed: bool,
    parent_checkpoint_sha256: str | None,
    inputs: StageInputs,
    seed: int,
) -> StagePlan:
    if stage not in _ALLOWED_STAGES:
        raise ValueError(f"unsupported stage: {stage}")
    if parent_checkpoint_sha256 is not None and not _sha_ok(parent_checkpoint_sha256):
        raise ValueError("parent checkpoint must be a SHA-256")
    status = "READY" if parent_training_allowed and parent_checkpoint_sha256 else "BLOCKED_PARENT_PROVENANCE"
    return StagePlan(
        stage=stage,
        status=status,
        seed=int(seed),
        parent_checkpoint_sha256=parent_checkpoint_sha256,
        input_manifest_sha256=inputs.combined_sha256,
        manifest_hashes=dict(sorted(inputs.manifest_hashes.items())),
    )
