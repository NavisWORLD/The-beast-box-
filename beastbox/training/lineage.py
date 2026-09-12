from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

_SECRET_KEYS = {"token", "password", "secret", "credential", "api_key"}
_ARTIFACT_NAMES = ("checkpoint", "architecture", "tokenizer", "memory_ledger")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def write_canonical_json(path: str | Path, value: Mapping[str, Any]) -> str:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical_json_bytes(value) + b"\n")
    return sha256_file(output)


def _validate_model_id(model_id: str) -> str:
    value = str(model_id).strip()
    if not value:
        raise ValueError("model_id must be non-empty")
    return value


def _is_sha256(value: Any) -> bool:
    text = str(value)
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text.lower())


def _reject_secret_like_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _SECRET_KEYS:
                raise ValueError(f"secret-like manifest key is forbidden: {key}")
            _reject_secret_like_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_secret_like_keys(child)


def _resolve_under_root(root: Path, stored_path: str | Path) -> Path:
    base = root.resolve()
    candidate = (base / Path(stored_path)).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"artifact path is outside root: {stored_path}") from exc
    return candidate


def _artifact_entry(*, name: str, stored_path: str | Path | None, root: Path) -> dict[str, str] | None:
    if stored_path is None:
        return None
    display_path = str(stored_path)
    target = _resolve_under_root(root, display_path)
    if not target.is_file():
        raise FileNotFoundError(f"{name} artifact does not exist: {display_path}")
    return {"path": display_path, "sha256": sha256_file(target)}


def build_parent_manifest(
    *,
    model_id: str,
    checkpoint_path: str | Path,
    architecture_path: str | Path,
    tokenizer_path: str | Path | None,
    memory_ledger_path: str | Path | None,
    root: str | Path = ".",
    expected_checkpoint_sha256: str | None = None,
    expected_architecture_sha256: str | None = None,
) -> dict[str, Any]:
    """Create a deterministic manifest for an immutable parent model lineage."""

    parent_id = _validate_model_id(model_id)
    base = Path(root)
    artifacts = {
        "checkpoint": _artifact_entry(name="checkpoint", stored_path=checkpoint_path, root=base),
        "architecture": _artifact_entry(name="architecture", stored_path=architecture_path, root=base),
        "tokenizer": _artifact_entry(name="tokenizer", stored_path=tokenizer_path, root=base),
        "memory_ledger": _artifact_entry(name="memory_ledger", stored_path=memory_ledger_path, root=base),
    }

    checkpoint_sha = artifacts["checkpoint"]["sha256"] if artifacts["checkpoint"] else ""
    architecture_sha = artifacts["architecture"]["sha256"] if artifacts["architecture"] else ""
    if expected_checkpoint_sha256 is not None and checkpoint_sha != str(expected_checkpoint_sha256).lower():
        raise RuntimeError(
            f"checkpoint SHA-256 mismatch: {checkpoint_sha} != {str(expected_checkpoint_sha256).lower()}"
        )
    if expected_architecture_sha256 is not None and architecture_sha != str(expected_architecture_sha256).lower():
        raise RuntimeError(
            f"architecture SHA-256 mismatch: {architecture_sha} != {str(expected_architecture_sha256).lower()}"
        )

    manifest: dict[str, Any] = {
        "schema": "zeref-phos-parent-manifest-v1",
        "model_id": parent_id,
        "artifacts": artifacts,
        "claim_boundary": {
            "historical_parent_immutable": True,
            "model_is_not_memory": True,
            "model_is_not_authority": True,
        },
    }
    _reject_secret_like_keys(manifest)
    return manifest


def verify_parent_manifest(
    manifest: Mapping[str, Any],
    *,
    root: str | Path = ".",
) -> dict[str, Any]:
    """Re-hash every recorded artifact and fail closed on any mismatch."""

    _reject_secret_like_keys(manifest)
    if manifest.get("schema") != "zeref-phos-parent-manifest-v1":
        raise ValueError("unexpected parent manifest schema")
    model_id = _validate_model_id(str(manifest.get("model_id", "")))
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise ValueError("parent manifest artifacts must be an object")

    base = Path(root)
    verified_count = 0
    for name in _ARTIFACT_NAMES:
        entry = artifacts.get(name)
        if entry is None:
            if name in ("checkpoint", "architecture"):
                raise ValueError(f"parent manifest requires {name} artifact")
            continue
        if not isinstance(entry, Mapping):
            raise ValueError(f"{name} artifact entry must be an object")
        stored_path = entry.get("path")
        expected_sha = entry.get("sha256")
        if not isinstance(stored_path, str) or not stored_path.strip():
            raise ValueError(f"{name} artifact path must be non-empty")
        if not _is_sha256(expected_sha):
            raise ValueError(f"{name} artifact SHA-256 is invalid")
        target = _resolve_under_root(base, stored_path)
        if not target.is_file():
            raise FileNotFoundError(f"{name} artifact does not exist: {stored_path}")
        actual_sha = sha256_file(target)
        if actual_sha != str(expected_sha).lower():
            raise RuntimeError(f"{name} SHA-256 mismatch: {actual_sha} != {str(expected_sha).lower()}")
        verified_count += 1

    return {"verified": True, "model_id": model_id, "artifact_count": verified_count}
