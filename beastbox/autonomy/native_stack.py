from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


EXPECTED_REPO_ID = "phera-ra/QC67_cosmo"
EXPECTED_REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"
EXPECTED_GGUF_PATH = "weights/cosmos-cst.gguf"
EXPECTED_GGUF_SHA256 = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"


@dataclass(frozen=True)
class NativeStackLock:
    repo_id: str
    revision: str
    gguf_path: str
    gguf_sha256: str
    entrypoint: str
    required_files: dict[str, str]


def _safe_relative(value: str) -> bool:
    path = PurePosixPath(str(value))
    return bool(str(value)) and not path.is_absolute() and ".." not in path.parts


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_native_stack(snapshot: Path, lock: NativeStackLock) -> tuple[str, ...]:
    """Verify the exact frozen HF stack without importing or executing it."""
    root = Path(snapshot).expanduser().resolve()
    errors: list[str] = []

    if lock.repo_id != EXPECTED_REPO_ID:
        errors.append("unexpected repo_id")
    if lock.revision != EXPECTED_REVISION:
        errors.append("unexpected revision")
    if lock.gguf_path != EXPECTED_GGUF_PATH:
        errors.append("unexpected gguf_path")
    if lock.gguf_sha256 != EXPECTED_GGUF_SHA256:
        errors.append("unexpected gguf_sha256")

    if not _safe_relative(lock.entrypoint):
        errors.append("entrypoint must be a safe relative path")
    elif lock.entrypoint not in lock.required_files:
        errors.append("entrypoint is not included in required_files")

    paths_to_check = dict(lock.required_files)
    paths_to_check[lock.gguf_path] = lock.gguf_sha256

    for relative, expected in sorted(paths_to_check.items()):
        if not _safe_relative(relative):
            errors.append(f"unsafe required path: {relative}")
            continue
        if len(str(expected)) != 64 or any(ch not in "0123456789abcdef" for ch in str(expected).lower()):
            errors.append(f"invalid sha256 in lock: {relative}")
            continue
        path = root.joinpath(*PurePosixPath(relative).parts)
        if not path.is_file():
            errors.append(f"missing required file: {relative}")
            continue
        actual = _sha256(path)
        if actual != str(expected).lower():
            errors.append(f"sha256 mismatch for {relative}: expected {expected}, got {actual}")

    return tuple(errors)
