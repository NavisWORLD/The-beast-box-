"""Owner-facing product services over the canonical Beast Box runtime.

This module intentionally contains host/UI services, not model-granted tools.
Authority is session-local and is never persisted into continuity state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from typing import Any

from .durable import DurableRuntime
from .optional_resources import resource_status as optional_resource_status
from .portable_state import export_snapshot

CAPABILITY_STATUSES = (
    "IMPLEMENTED_AND_TESTED",
    "IMPLEMENTED_NOT_PHYSICALLY_VALIDATED",
    "PROTOTYPE",
    "BLOCKED_EXTERNAL",
    "NOT_ESTABLISHED",
)

_ALLOWED_AUTHORITIES = frozenset(
    {
        "camera",
        "microphone",
        "sensors",
        "cloud",
        "repo_write",
        "filesystem",
        "tools",
        "quantum_live",
        "external_integrations",
    }
)
_MASTER_PRIVACY_AUTHORITIES = _ALLOWED_AUTHORITIES
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
_MODEL_TRACE_FIELDS = (
    "provider",
    "model",
    "identity_kind",
    "prompt_sha256",
    "output_sha256",
)


def capability_inventory() -> dict[str, dict[str, str]]:
    """Return the product-facing truth matrix using the release vocabulary."""
    return {
        "persistent_substrate": {
            "status": "IMPLEMENTED_AND_TESTED",
            "source": "beastbox.durable + beastbox.continuity",
        },
        "model_swap": {
            "status": "IMPLEMENTED_AND_TESTED",
            "source": "DurableRuntime provider boundary + architecture acceptance",
        },
        "desktop_chat": {
            "status": "IMPLEMENTED_AND_TESTED",
            "source": "beastbox.desktop",
        },
        "cosmic_browser_ui": {
            "status": "IMPLEMENTED_AND_TESTED",
            "source": "beastbox.cosmic_web + beastbox.cosmic_ui",
        },
        "openai_compatible_provider": {
            "status": "IMPLEMENTED_AND_TESTED",
            "source": "beastbox.providers.CompatibleChatProvider",
        },
        "ollama_provider": {
            "status": "IMPLEMENTED_AND_TESTED",
            "source": "beastbox.providers.LocalOllamaProvider",
        },
        "pcm_wav_features": {
            "status": "IMPLEMENTED_AND_TESTED",
            "source": "beastbox.sensor_inputs.wav_event",
        },
        "light_observation": {
            "status": "IMPLEMENTED_AND_TESTED",
            "source": "beastbox.sensor_inputs.light_event",
        },
        "portable_state": {
            "status": "IMPLEMENTED_AND_TESTED",
            "source": "beastbox.portable_state",
        },
        "workspace_repository": {
            "status": "IMPLEMENTED_AND_TESTED",
            "source": "beastbox.cypher.workspace + cosmic owner controller",
        },
        "camera_capture": {
            "status": "IMPLEMENTED_NOT_PHYSICALLY_VALIDATED",
            "source": "browser getUserMedia implementation; physical/mobile capture not CI-validated",
        },
        "live_microphone_capture": {
            "status": "IMPLEMENTED_NOT_PHYSICALLY_VALIDATED",
            "source": "browser getUserMedia + bounded local feature path; physical capture not CI-validated",
        },
        "browser_tts": {
            "status": "IMPLEMENTED_NOT_PHYSICALLY_VALIDATED",
            "source": "browser speechSynthesis UI path; audible output is not headless-CI validated",
        },
        "ibm_quantum_adapter": {
            "status": "PROTOTYPE",
            "source": "beastbox.optional_resources.quantum_event",
        },
        "azure_quantum_adapter": {
            "status": "PROTOTYPE",
            "source": "beastbox.optional_resources.quantum_event",
        },
        "quantum_hardware_execution": {
            "status": "BLOCKED_EXTERNAL",
            "source": "requires owner credentials, provider access, and live external hardware validation",
        },
        "reality_probe_hardware": {
            "status": "PROTOTYPE",
            "source": "historical Reality Bridge work; current product has no physical validation receipt",
        },
        "custom_voice": {
            "status": "NOT_ESTABLISHED",
            "source": "no verified production custom-voice implementation recovered",
        },
        "privileged_external_integrations": {
            "status": "BLOCKED_EXTERNAL",
            "source": "requires separately authorized external service connections",
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

    def revoke_all(self) -> list[str]:
        """Drop every model-facing host grant when a different brain clocks in."""
        stopped = sorted(self._grants)
        self._grants.clear()
        return stopped


@dataclass(frozen=True)
class FileInspection:
    name: str
    byte_count: int
    sha256: str
    preview: str | None
    persistent: bool = False


class WorkspaceGrant:
    """Legacy read-only allowlisted local workspace retained for compatibility."""

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

    def memory_records(self, *, limit: int = 50) -> list[dict[str, Any]]:
        runtime = DurableRuntime(self.root)
        try:
            return [asdict(record) for record in runtime.memory.recent(limit=limit)]
        finally:
            runtime.close()

    def trace_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        runtime = DurableRuntime(self.root)
        try:
            checkpoints = runtime.continuity.history(limit=limit)
        finally:
            runtime.close()
        events: list[dict[str, Any]] = []
        for checkpoint in checkpoints:
            receipt = checkpoint.get("receipt", {})
            if not isinstance(receipt, dict):
                receipt = {}
            model = receipt.get("model", {})
            safe_model = {
                field: model[field]
                for field in _MODEL_TRACE_FIELDS
                if isinstance(model, dict) and field in model
            }
            stages = receipt.get("trace", [])
            events.append(
                {
                    "sequence": checkpoint["sequence"],
                    "checkpoint_sha256": checkpoint["sha256"],
                    "previous": checkpoint["previous"],
                    "stages": list(stages) if isinstance(stages, list) else [],
                    "event": receipt.get("event"),
                    "routing": receipt.get("routing", {}),
                    "model": safe_model,
                    "tool_result": receipt.get("tool_result", {}),
                }
            )
        return events

    def orbit_snapshot(self) -> dict[str, Any]:
        runtime = DurableRuntime(self.root)
        try:
            inspection = runtime.inspect()
        finally:
            runtime.close()
        return {
            "runtime": inspection,
            "authority": self.authority.snapshot(),
            "resources": self.resource_status(),
            "capabilities": capability_inventory(),
        }

    def export_portable(self, destination: str | Path) -> dict[str, Any]:
        return export_snapshot(self.root, Path(destination))
