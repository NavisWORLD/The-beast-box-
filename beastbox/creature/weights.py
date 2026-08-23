from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    target = Path(path)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _format_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".gguf":
        try:
            magic = path.read_bytes()[:4]
        except OSError:
            magic = b""
        return "gguf" if magic == b"GGUF" else "invalid-gguf"
    if suffix in {".pt", ".pth", ".ckpt", ".safetensors", ".bin"}:
        return "native"
    return "unknown"


def inspect_weight(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(target)
    return {
        "path": str(target),
        "filename": target.name,
        "size": target.stat().st_size,
        "sha256": sha256_file(target),
        "format": _format_for(target),
    }


def build_weight_manifest(
    path: str | Path,
    *,
    architecture: str | None = None,
    quantization: str | None = None,
    tokenizer: str | None = None,
    source_checkpoint: str | None = None,
    license_name: str | None = None,
    provenance: str | None = None,
    converter: str | None = None,
) -> dict[str, Any]:
    info = inspect_weight(path)
    return {
        "schema": "cosmos.weight-manifest.v1",
        "filename": info["filename"],
        "size": info["size"],
        "sha256": info["sha256"],
        "format": info["format"],
        "architecture": architecture,
        "quantization": quantization,
        "tokenizer": tokenizer,
        "source_checkpoint": source_checkpoint,
        "license": license_name,
        "provenance": provenance,
        "converter": converter,
    }
