#!/usr/bin/env python3
"""Discover trainable checkpoint candidates without inventing lineage equivalence."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


PRIME_REPO = "phera-ra/QC67_cosmo"
PRIME_REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"
PRIME_GGUF = "weights/cosmos-cst.gguf"
PRIME_GGUF_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
TRAINABLE_SUFFIXES = (".safetensors", ".pt", ".pth", ".bin", ".ckpt")
PROOF_METHODS = {
    "source-checkpoint-export-manifest",
    "deterministic-conversion-manifest",
}


@dataclass(frozen=True)
class ParentPreflightResult:
    status: str
    training_allowed: bool
    trainable_candidates: tuple[str, ...]
    proven_artifact: str | None = None
    reason: str = ""


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _candidate_paths(paths: Iterable[str]) -> tuple[str, ...]:
    values = {
        str(path)
        for path in paths
        if str(path).lower().endswith(TRAINABLE_SUFFIXES)
    }
    return tuple(sorted(values))


def _proof_matches_candidate(
    proof: dict[str, Any] | None,
    candidates: tuple[str, ...],
) -> str | None:
    if not proof:
        return None
    artifact = proof.get("artifact_path")
    if artifact not in candidates:
        return None
    if proof.get("prime_gguf_sha256") != PRIME_GGUF_SHA256:
        return None
    if proof.get("equivalence_method") not in PROOF_METHODS:
        return None
    if not _is_sha256(proof.get("artifact_sha256")):
        return None
    return str(artifact)


def classify_files(
    paths: Iterable[str],
    *,
    proof: dict[str, Any] | None = None,
) -> ParentPreflightResult:
    """Classify repository file inventory without trusting filenames as lineage."""
    candidates = _candidate_paths(paths)
    if not candidates:
        return ParentPreflightResult(
            status="NO_TRAINABLE_PARENT",
            training_allowed=False,
            trainable_candidates=(),
            reason="No trainable checkpoint-format files were present in the pinned inventory.",
        )

    proven = _proof_matches_candidate(proof, candidates)
    if proven:
        return ParentPreflightResult(
            status="PROVEN",
            training_allowed=True,
            trainable_candidates=candidates,
            proven_artifact=proven,
            reason="An explicit Prime-equivalence manifest names a present trainable artifact.",
        )

    return ParentPreflightResult(
        status="CONVERSION_REQUIRED",
        training_allowed=False,
        trainable_candidates=candidates,
        reason=(
            "Trainable-format candidate(s) exist, but no valid cryptographic mapping proves "
            "that any candidate is the trainable ancestor/equivalent of Zeref Prime."
        ),
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_proven_artifact_bytes(
    *,
    repo_id: str,
    revision: str,
    proof: dict[str, Any],
) -> bool:
    """Download and hash a proof-named artifact before allowing real training."""
    from huggingface_hub import hf_hub_download

    artifact = str(proof["artifact_path"])
    expected = str(proof["artifact_sha256"])
    local = Path(
        hf_hub_download(
            repo_id=repo_id,
            filename=artifact,
            revision=revision,
        )
    )
    return _sha256_file(local) == expected


def inspect_hub(
    *,
    repo_id: str,
    revision: str,
    proof: dict[str, Any] | None = None,
) -> tuple[list[str], ParentPreflightResult]:
    from huggingface_hub import HfApi

    files = sorted(HfApi().list_repo_files(repo_id=repo_id, revision=revision))
    result = classify_files(files, proof=proof)

    # A pure proof document is not enough for the live preflight. If it would
    # unlock training, verify the named bytes from the exact revision first.
    if result.training_allowed and proof is not None:
        if not _verify_proven_artifact_bytes(
            repo_id=repo_id,
            revision=revision,
            proof=proof,
        ):
            result = ParentPreflightResult(
                status="CONVERSION_REQUIRED",
                training_allowed=False,
                trainable_candidates=result.trainable_candidates,
                reason="Equivalence proof named an artifact whose downloaded SHA-256 did not match.",
            )
    return files, result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=PRIME_REPO)
    parser.add_argument("--revision", default=PRIME_REVISION)
    parser.add_argument("--proof", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("experiments/descendant-d001/parent-preflight.json"),
    )
    args = parser.parse_args()

    proof = None
    if args.proof:
        proof = json.loads(args.proof.read_text(encoding="utf-8"))

    files, result = inspect_hub(
        repo_id=args.repo,
        revision=args.revision,
        proof=proof,
    )
    payload = {
        "schema": "d001-parent-preflight-v1",
        "repo_id": args.repo,
        "revision": args.revision,
        "prime_gguf_path": PRIME_GGUF,
        "prime_gguf_sha256": PRIME_GGUF_SHA256,
        "inventory_count": len(files),
        "inventory": files,
        **asdict(result),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
