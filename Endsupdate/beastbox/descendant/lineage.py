"""Frozen model-lineage manifests for Zeref/COSMOS descendants."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .hashing import sha256_file


PRIME_GGUF_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
PRIME_REPO_ID = "phera-ra/QC67_cosmo"
PRIME_REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"
PRIME_NATIVE_CONTEXT = 128


def _require_sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")


@dataclass(frozen=True)
class PrimeManifest:
    repo_id: str
    revision: str
    gguf_path: str
    gguf_sha256: str
    native_context: int
    source_lock_sha256: str
    required_files: tuple[tuple[str, str], ...]

    @classmethod
    def from_lock(cls, path: str | Path, *, native_context: int) -> "PrimeManifest":
        lock_path = Path(path)
        value = json.loads(lock_path.read_text(encoding="utf-8"))

        if value.get("repo_id") != PRIME_REPO_ID:
            raise ValueError("Prime repository identity does not match the frozen lineage")
        if value.get("revision") != PRIME_REVISION:
            raise ValueError("Prime revision does not match the frozen lineage")
        if value.get("gguf_sha256") != PRIME_GGUF_SHA256:
            raise ValueError("Prime GGUF identity does not match the frozen lineage")
        if native_context != PRIME_NATIVE_CONTEXT:
            raise ValueError("Prime native context must remain 128")

        required = tuple(sorted((str(k), str(v)) for k, v in value.get("required_files", {}).items()))
        for file_path, digest in required:
            if not file_path:
                raise ValueError("Prime required-file path cannot be blank")
            _require_sha256(f"required_files[{file_path!r}]", digest)

        return cls(
            repo_id=value["repo_id"],
            revision=value["revision"],
            gguf_path=value["gguf_path"],
            gguf_sha256=value["gguf_sha256"],
            native_context=native_context,
            source_lock_sha256=sha256_file(lock_path),
            required_files=required,
        )


@dataclass(frozen=True)
class TrainableParentManifest:
    artifact_path: str
    artifact_sha256: str
    provenance_status: str
    prime_equivalence_proven: bool
    architecture: str

    def __post_init__(self) -> None:
        if not self.artifact_path:
            raise ValueError("trainable parent artifact path cannot be blank")
        _require_sha256("trainable parent artifact_sha256", self.artifact_sha256)
        if not self.provenance_status:
            raise ValueError("trainable parent provenance status cannot be blank")
        if not self.architecture:
            raise ValueError("trainable parent architecture cannot be blank")

    @property
    def training_allowed(self) -> bool:
        return self.provenance_status == "PROVEN" and self.prime_equivalence_proven


@dataclass(frozen=True)
class DescendantCheckpointManifest:
    stage: str
    parent_sha256: str
    output_sha256: str
    code_commit: str
    corpus_manifest_sha256: str

    def __post_init__(self) -> None:
        if not self.stage:
            raise ValueError("descendant stage cannot be blank")
        if not self.parent_sha256:
            raise ValueError("parent SHA-256 cannot be blank")
        _require_sha256("parent_sha256", self.parent_sha256)
        _require_sha256("output_sha256", self.output_sha256)
        if self.parent_sha256 == self.output_sha256:
            raise ValueError("parent and output checkpoints must be distinct")
        if not self.code_commit:
            raise ValueError("code commit cannot be blank")
        _require_sha256("corpus_manifest_sha256", self.corpus_manifest_sha256)
