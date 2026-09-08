"""Owner-facing product services over the canonical Beast Box runtime.

This module intentionally contains host/UI services, not model-granted tools.
Authority is session-local and is never persisted into continuity state.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from .optional_resources import resource_status as optional_resource_status
from .portable_state import export_snapshot

CAPABILITY_STATUSES = (
    "EXISTS_AND_WORKS",
    "EXISTS_BUT_NOT_EXPOSED",
    "HISTORICAL_REUSABLE",
    "PROTOTYPE_ONLY",
    "MISSING",
    "NOT_ESTABLISHED",
)

_ALLOWED_AUTHORITIES = frozenset(
    {"camera", "microphone", "sensors", "cloud", "repo_write", "quantum_live"}
)
_MASTER_PRIVACY_AUTHORITIES = frozenset(
    {"camera", "microphone", "sensors", "cloud", "repo_write", "quantum_live"}
)
_SAFE_FILE_SUFFIXES = frozenset(
    {
        ".txt",
        ".md",
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".csv",
        ".yaml",
        ".yml",
        ".toml",
        ".html",
        ".css",
        ".xml",
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".wav",
    }
)
_TEXT_FILE_SUFFIXES = frozenset(
    {
        ".txt",
        ".md",
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".csv",
        ".yaml",
        ".yml",
        ".toml",
        ".html",
        ".css",
        ".xml",
    }
)


def capability_inventory() -> dict[str, dict[str, str]]:
    """Return product-facing truth labels backed by current repository surfaces."""
    return {
        "persistent_substrate": {
            "status": "EXISTS_AND_WORKS",
            "source": "beastbox.durable + beastbox.continuity",
        },
        "model_swap": {
            "status": "EXISTS_AND_WORKS",
            "source": "DurableRuntime provider boundary + sealed swap evidence",
        },
        "desktop_chat": {
            "status": "EXISTS_AND_WORKS",
            "source": "beastbox.desktop",
        },
        "openai_compatible_provider": {
            "status": "EXISTS_AND_WORKS",
            "source": "beastbox.providers.CompatibleChatProvider",
        },
        "ollama_provider": {
            "status": "EXISTS_AND_WORKS",
            "source": "beastbox.providers.LocalOllamaProvider",
        },
        "pcm_wav_features": {
            "status": "EXISTS_AND_WORKS",
            "source": "beastbox.sensor_inputs.wav_event",
        },
        "light_observation": {
            "status": "EXISTS_AND_WORKS",
            "source": "beastbox.sensor_inputs.light_event",
        },
        "ibm_quantum_adapter": {
            "status": "EXISTS_BUT_NOT_EXPOSED",
            "source": "beastbox.optional_resources.quantum_event",
        },
        "azure_quantum_adapter": {
            "status": "EXISTS_BUT_NOT_EXPOSED",
            "source": "beastbox.optional_resources.quantum_event",
        },
        "portable_state": {
            "status": "EXISTS_AND_WORKS",
            "source": "beastbox.portable_state",
        },
        "reality_probe_hardware": {
            "status": "HISTORICAL_REUSABLE",
            "source": "NavisWORLD/Reality-bridge-universal-probe-engine-sim-",
        },
        "camera_capture": {
            "status": "NOT_ESTABLISHED",
            "source": "no current validated Beast camera capture path",
        },
        "live_microphone_capture": {
            "status": "NOT_ESTABLISHED",
            "source": "current runtime accepts bounded WAV input but opens no microphone",
        },
        "custom_voice": {
            "status": "NOT_ESTABLISHED",
            "source": "no verified production custom-voice implementation recovered",
        },
    }


class AuthoritySession:
    """Default-deny host authority that deliberately lives outside durable state."""

    def __init__(self) -> None:
        self._grants: set[str] = set()

    @staticmethod
    def _validate(name: str) -> None:
        if name not in _ALLOWED_AUTHORITIES:
            raise ValueError(f"unknown authority: {name}")

    def allowed(self, name: str) -> bool:
        self._validate(name)
        return name in self._grants

    def grant(self, name: str) -> None:
        self._validate(name)
        self._grants.add(name)

    def revoke(self, name: str) -> None:
        self._validate(name)
        self._grants.discard(name)

    def snapshot(self) -> dict[str, bool]:
        return {name: name in self._grants for name in sorted(_ALLOWED_AUTHORITIES)}

    def master_privacy_stop(self) -> list[str]:
        stopped = sorted(name for name in _MASTER_PRIVACY_AUTHORITIES if name in self._grants)
        self._grants.difference_update(_MASTER_PRIVACY_AUTHORITIES)
        return stopped


@dataclass(frozen=True)
class FileInspection:
    name: str
    byte_count: int
    sha256: str
    preview: str | None
    persistent: bool = False


class WorkspaceGrant:
    """Read-only allowlisted local workspace; write authority is intentionally absent."""

    def __init__(self, root: str | Path, *, max_read_bytes: int = 1024 * 1024) -> None:
        supplied = Path(root).expanduser()
        if supplied.is_symlink() or not supplied.is_dir():
            raise ValueError("workspace root must be an existing non-symlink directory")
        self.root = supplied.resolve()
        self.max_read_bytes = max_read_bytes

    def _candidate(self, relative: str | Path) -> Path:
        requested = Path(relative)
        if requested.is_absolute() or ".." in requested.parts or not requested.parts:
            raise ValueError("path must remain inside workspace root")
        candidate = self.root.joinpath(*requested.parts)
        current = self.root
        for part in requested.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("workspace path cannot traverse a symlink")
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise ValueError("path must remain inside workspace root") from None
        return candidate

    def list_files(self, *, limit: int = 5000) -> list[str]:
        files: list[str] = []
        for path in self.root.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            files.append(path.relative_to(self.root).as_posix())
            if len(files) > limit:
                raise ValueError("workspace listing exceeds configured limit")
        return sorted(files)

    def read_text(self, relative: str | Path) -> str:
        path = self._candidate(relative)
        if not path.is_file():
            raise ValueError("workspace path is not a regular file")
        with path.open("rb") as handle:
            raw = handle.read(self.max_read_bytes + 1)
        if len(raw) > self.max_read_bytes:
            raise ValueError("workspace file exceeds configured read limit")
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("workspace file is not UTF-8 text") from None


class ProductService:
    """Thin product facade over existing storage/resource implementations."""

    def __init__(
        self,
        root: str | Path,
        *,
        authority: AuthoritySession | None = None,
        max_file_bytes: int = 8 * 1024 * 1024,
    ) -> None:
        self.root = Path(root).expanduser()
        self.authority = authority or AuthoritySession()
        if type(max_file_bytes) is not int or max_file_bytes < 1:
            raise ValueError("max_file_bytes must be a positive integer")
        self.max_file_bytes = max_file_bytes

    def inspect_file(self, source: str | Path) -> FileInspection:
        path = Path(source).expanduser()
        if path.is_symlink() or not path.is_file():
            raise ValueError("file must be a regular non-symlink input")
        suffix = path.suffix.lower()
        if suffix not in _SAFE_FILE_SUFFIXES:
            raise ValueError("unsupported file type")
        with path.open("rb") as handle:
            raw = handle.read(self.max_file_bytes + 1)
        if len(raw) > self.max_file_bytes:
            raise ValueError("file exceeds configured maximum size")
        preview: str | None = None
        if suffix in _TEXT_FILE_SUFFIXES:
            try:
                preview = raw.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("text file is not valid UTF-8") from None
        return FileInspection(
            name=path.name,
            byte_count=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            preview=preview,
            persistent=False,
        )

    def resource_status(self) -> dict[str, dict[str, str]]:
        return optional_resource_status()

    def export_portable(self, destination: str | Path) -> dict[str, Any]:
        return export_snapshot(self.root, Path(destination))
