"""COSMIC.CYPHER owner surface over the canonical durable Beast Box runtime.

Browser device handles remain browser-local. Workspace, storage and provider
operations are explicit owner actions; retained state never grants host authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
import threading
from collections import deque
from typing import Any, Iterable
import urllib.parse

from .cosmic_ui import render_cosmic_ui
from .cypher.workspace import FULL_REPLACEMENT_DIFF_HEADER, Workspace
from .durable import DurableRuntime
from .optional_resources import ResourceUnavailable, quantum_event
from .portable_state import import_snapshot, verify_snapshot
from .product_services import AuthoritySession, ProductService
from .providers import CompatibleChatProvider, LocalOllamaProvider, ReferenceTextProvider, TextProvider

_MAX_REQUEST_BYTES = 1024 * 1024
_MAX_CONTEXT_CHARS = 512 * 1024
_ENV_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
_CONTEXT_SCOPES = frozenset(
    {"temporary_attachment", "conversation_context", "workspace_knowledge", "persistent_memory"}
)


def _is_loopback_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_bind_host(host: str) -> str:
    if host == "localhost":
        return host
    try:
        if ipaddress.ip_address(host).is_loopback:
            return host
    except ValueError:
        pass
    raise ValueError("cosmic UI must bind to a loopback host")


@dataclass(frozen=True)
class ProviderProfile:
    kind: str = "reference"
    model: str = "COSMOS reference"
    base_url: str = ""
    allow_remote: bool = False
    api_key_env: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ProviderProfile:
        if not isinstance(value, dict):
            raise ValueError("provider profile must be an object")
        allowed = {"kind", "model", "base_url", "allow_remote", "api_key_env"}
        if set(value) - allowed:
            raise ValueError("provider profile contains unsupported fields")
        kind = value.get("kind", "reference")
        model = value.get("model", "COSMOS reference")
        base_url = value.get("base_url", "")
        allow_remote = value.get("allow_remote", False)
        api_key_env = value.get("api_key_env")
        if not isinstance(kind, str) or kind not in {"reference", "ollama", "compatible"}:
            raise ValueError("provider kind must be reference, ollama, or compatible")
        if not isinstance(model, str) or not model.strip() or len(model) > 256:
            raise ValueError("provider model must contain 1..256 characters")
        if not isinstance(base_url, str) or len(base_url) > 2048:
            raise ValueError("provider base URL is invalid")
        if type(allow_remote) is not bool:
            raise ValueError("allow_remote must be boolean")
        if api_key_env is not None and (
            not isinstance(api_key_env, str) or _ENV_NAME_RE.fullmatch(api_key_env) is None
        ):
            raise ValueError("api_key_env must be an environment variable name")
        if kind == "ollama" and not base_url:
            base_url = "http://127.0.0.1:11434"
        if kind == "compatible" and not base_url:
            base_url = "http://127.0.0.1:1234/v1"
        profile = cls(kind, model.strip(), base_url, allow_remote, api_key_env)
        profile.make_provider()
        return profile

    @property
    def remote(self) -> bool:
        return self.kind == "compatible" and not _is_loopback_url(self.base_url)

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.kind, self.model, self.base_url

    def make_provider(self) -> TextProvider:
        if self.kind == "reference":
            return ReferenceTextProvider(prefix=self.model)
        if self.kind == "ollama":
            return LocalOllamaProvider(model=self.model, base_url=self.base_url)
        return CompatibleChatProvider(
            model=self.model,
            base_url=self.base_url,
            allow_remote=self.allow_remote,
            api_key_env=self.api_key_env,
        )


def _provider_path(root: Path) -> Path:
    return root / "cosmic-provider.json"


def save_provider_profile(root: Path, profile: ProviderProfile) -> None:
    root.mkdir(parents=True, exist_ok=True)
    path = _provider_path(root)
    if path.is_symlink():
        raise ValueError("provider settings cannot be a symlink")
    payload = json.dumps(asdict(profile), sort_keys=True, indent=2) + "\n"
    fd, name = tempfile.mkstemp(prefix=".cosmic-provider-", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def load_provider_profile(root: Path) -> ProviderProfile:
    path = _provider_path(root)
    if not path.exists():
        return ProviderProfile()
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise ValueError("provider settings must be a small regular file")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ProviderProfile.from_dict(raw)


def _regular_directory(value: str | Path) -> Path:
    supplied = Path(value).expanduser()
    if supplied.is_symlink() or not supplied.is_dir():
        raise ValueError("workspace root must be an existing non-symlink directory")
    return supplied.resolve()


class CosmicApp:
    """Testable owner controller; HTTP is only a transport adapter around this."""

    def __init__(self, root: str | Path, *, workspace_roots: Iterable[str | Path] = ()) -> None:
        supplied_root = Path(root).expanduser()
        if supplied_root.is_symlink():
            raise ValueError("cosmic runtime root cannot be a symlink")
        self.root = supplied_root.absolute()
        self.authority = AuthoritySession()
        self.service = ProductService(self.root, authority=self.authority)
        self.profile = load_provider_profile(self.root)
        self.workspace_allowlist: set[Path] = set()
        self.workspace: Workspace | None = None
        self.contexts: list[dict[str, Any]] = []
        self._context_sequence = 0
        self._context_content: dict[int, str] = {}
        self._lock = threading.RLock()
        self.session_events: deque[dict[str, Any]] = deque(maxlen=100)
        candidates: list[str | Path] = list(workspace_roots)
        configured = os.environ.get("BEASTBOX_WORKSPACE_ROOTS", "")
        if configured:
            candidates.extend(part for part in configured.split(os.pathsep) if part)
        for candidate in candidates:
            self.workspace_allowlist.add(_regular_directory(candidate))

    def _provider(self, profile: ProviderProfile | None = None) -> TextProvider:
        selected = profile or self.profile
        if selected.remote and not self.authority.allowed("cloud"):
            raise PermissionError("cloud authority required")
        return selected.make_provider()

    def _runtime(self, profile: ProviderProfile | None = None) -> DurableRuntime:
        return DurableRuntime(self.root, self._provider(profile))

    def _set_profile(self, raw: dict[str, Any]) -> tuple[ProviderProfile, bool, list[str]]:
        previous = self.profile.identity
        profile = ProviderProfile.from_dict(raw)
        # Validate configured remote access using the old brain's current owner grant.
        self._provider(profile)
        save_provider_profile(self.root, profile)
        self.profile = profile
        changed = previous != profile.identity
        revoked = self.authority.revoke_all() if changed else []
        if changed:
            self.session_events.append({"kind": "brain_handoff", "model": profile.model, "authority_revoked": revoked})
        return profile, changed, revoked

    def _authority(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        action = body.get("action")
        if not isinstance(action, str):
            return 400, {"error": "invalid authority action"}
        if action == "master_stop" and set(body) == {"action"}:
            stopped = self.authority.master_privacy_stop()
            self.session_events.append({"kind": "master_stop", "revoked": stopped})
            return 200, {"stopped": stopped, "authority": self.authority.snapshot()}
        if action not in {"grant", "revoke"} or set(body) != {"action", "name"}:
            return 400, {"error": "invalid authority request"}
        name = body.get("name")
        if not isinstance(name, str):
            return 400, {"error": "invalid authority name"}
        try:
            if action == "grant":
                self.authority.grant(name)
            else:
                self.authority.revoke(name)
        except ValueError as exc:
            return 400, {"error": str(exc)}
        self.session_events.append({"kind": "authority", "action": action, "name": name})
        return 200, {"authority": self.authority.snapshot()}

    def _chat(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        text = body.get("text")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 8192:
            return 400, {"error": "chat text must contain 1..8192 characters"}
        ids = body.get("context_ids", [])
        if (set(body) - {"text", "provider", "context_ids"} or not isinstance(ids, list)
                or len(ids) > 100 or any(type(i) is not int for i in ids) or len(set(ids)) != len(ids)):
            return 400, {"error": "invalid context selection"}
        if any(i not in self._context_content for i in ids):
            return 400, {"error": "context expired or unavailable; select it again"}
        context = "\n\n".join(self._context_content[i] for i in ids)
        if len(context) > _MAX_CONTEXT_CHARS:
            return 400, {"error": "combined context exceeds limit"}
        profile = self.profile
        changed = False
        revoked: list[str] = []
        if "provider" in body:
            raw = body.get("provider")
            if not isinstance(raw, dict):
                return 400, {"error": "provider must be an object"}
            profile, changed, revoked = self._set_profile(raw)
        runtime = self._runtime(profile)
        try:
            before = runtime.inspect()
            result = runtime.respond(text, transient_context=context)
            after = runtime.inspect()
        finally:
            runtime.close()
        for record in list(self.contexts):
            if record["id"] in ids and record["scope"] == "temporary_attachment":
                self.contexts.remove(record)
                self._context_content.pop(record["id"], None)
        return 200, {
            "context_used": ids,
            "response_persistent": not bool(context),
            "result": result,
            "runtime": after,
            "brain_changed": changed,
            "authority_revoked": revoked,
            "substrate_preserved": before["system_id"] == after["system_id"],
            "provider": asdict(profile),
        }

    def _event(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        modality = body.get("modality")
        event = body.get("event")
        if not isinstance(modality, str):
            return 400, {"error": "invalid bounded event request"}
        authority_name = {"camera": "camera", "microphone": "microphone", "sensor": "sensors"}.get(modality)
        if authority_name is None or not isinstance(event, dict) or set(body) != {"modality", "event"}:
            return 400, {"error": "invalid bounded event request"}
        if not self.authority.allowed(authority_name):
            return 403, {"error": f"{authority_name} authority required"}
        runtime = self._runtime()
        try:
            result = runtime.respond_event(event)
            inspection = runtime.inspect()
        finally:
            runtime.close()
        return 200, {"result": result, "runtime": inspection, "raw_media_transmitted": False}

    def _quantum(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not self.authority.allowed("quantum_live"):
            return 403, {"error": "quantum live authority required"}
        if set(body) != {"provider", "shots"}:
            return 400, {"error": "invalid quantum request"}
        provider = body.get("provider")
        shots = body.get("shots")
        try:
            event = quantum_event(provider, shots=shots, allow_live=True)
            runtime = self._runtime()
            try:
                result = runtime.respond_event(event)
            finally:
                runtime.close()
        except ResourceUnavailable as exc:
            return 503, {"error": str(exc)}
        except (ValueError, TypeError):
            return 400, {"error": "invalid quantum request"}
        return 200, {"event": event, "result": result, "experimental": True}

    def _workspace_allow(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not self.authority.allowed("filesystem"):
            return 403, {"error": "filesystem authority required"}
        root = body.get("root")
        if not isinstance(root, str) or set(body) != {"root"}:
            return 400, {"error": "invalid workspace allow request"}
        path = _regular_directory(root)
        self.workspace_allowlist.add(path)
        return 200, {"allowed": str(path), "allowlist": sorted(str(item) for item in self.workspace_allowlist)}

    def _workspace_select(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        root = body.get("root")
        if not isinstance(root, str) or set(body) != {"root"}:
            return 400, {"error": "invalid workspace selection"}
        path = _regular_directory(root)
        if path not in self.workspace_allowlist:
            return 403, {"error": "workspace root is not allowlisted"}
        self.workspace = Workspace(path)
        return 200, self._workspace_snapshot()

    def _workspace_snapshot(self) -> dict[str, Any]:
        if self.workspace is None:
            return {
                "selected": None,
                "allowlist": sorted(str(item) for item in self.workspace_allowlist),
                "tree": [],
                "read_only": True,
            }
        writable = self.authority.allowed("filesystem") and self.authority.allowed("repo_write")
        return {
            "selected": str(self.workspace.root),
            "allowlist": sorted(str(item) for item in self.workspace_allowlist),
            "tree": self.workspace.tree(),
            "read_only": not writable,
        }

    def _selected_workspace(self) -> Workspace:
        if self.workspace is None:
            raise ValueError("no workspace selected")
        return self.workspace

    def _workspace_read(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        path = body.get("path")
        if not isinstance(path, str) or set(body) != {"path"}:
            return 400, {"error": "invalid workspace read request"}
        content = self._selected_workspace().read(path)
        return 200, {"path": path, "content": content, "persistent_memory": False}

    def _workspace_write(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not self.authority.allowed("filesystem") or not self.authority.allowed("repo_write"):
            return 403, {"error": "filesystem and repo_write authority required"}
        path = body.get("path")
        content = body.get("content")
        if (
            not isinstance(path, str)
            or not isinstance(content, str)
            or len(content) > 1024 * 1024
            or set(body) != {"path", "content"}
        ):
            return 400, {"error": "invalid bounded workspace write request"}
        return 200, self._selected_workspace().write(path, content)

    def _workspace_search(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        query = body.get("query")
        if not isinstance(query, str) or not 1 <= len(query) <= 256 or set(body) != {"query"}:
            return 400, {"error": "search needs 1..256 characters"}
        return 200, {"hits": self._selected_workspace().search(query), "persistent_memory": False}

    def _workspace_diff(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        path, content = body.get("path"), body.get("content")
        if not isinstance(path, str) or not isinstance(content, str) or set(body) != {"path", "content"}:
            return 400, {"error": "invalid workspace preview request"}
        diff = self._selected_workspace().diff(path, content)
        lines = diff.splitlines(keepends=True)
        preview = "".join(lines[:2000])[:250_000]
        return 200, {
            "path": path, "diff": preview, "written": False, "persistent_memory": False,
            "mode": "full_replacement" if diff.startswith(FULL_REPLACEMENT_DIFF_HEADER) else "unified",
            "truncated": len(preview) < len(diff), "line_count": len(lines),
        }

    def _workspace_status(self) -> tuple[int, dict[str, Any]]:
        workspace = self._selected_workspace()
        if not self._workspace_has_repository():
            return 200, {"is_git_repo": False, "status": {"stdout": "Selected root has no .git directory"}}
        result = workspace.run(["git", "status", "--short", "--branch"], timeout=15)
        return 200, {"is_git_repo": result["returncode"] == 0, "status": result}

    def _workspace_has_repository(self) -> bool:
        metadata = self._selected_workspace().resolve(".git")
        if metadata.is_file():
            raise ValueError("external gitdir/worktree indirection is not supported in the browser")
        return metadata.is_dir()

    def _workspace_run(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not self.authority.allowed("tools"):
            return 403, {"error": "tools authority required"}
        argv = body.get("argv")
        if (
            not isinstance(argv, list)
            or not argv
            or not all(isinstance(item, str) for item in argv)
            or set(body) != {"argv"}
        ):
            return 400, {"error": "invalid bounded workspace command"}
        # Browser command input is deliberately narrower than owner CLI test execution.
        # Arbitrary Git flags can invoke helpers, write files or read outside the root.
        permitted = {
            ("git", "status", "--short"), ("git", "status", "--short", "--branch"),
            ("git", "diff", "--stat"), ("git", "log", "-5", "--oneline"),
        }
        if tuple(argv) not in permitted:
            return 400, {"error": "browser runner permits only the listed read-only Git commands; push stays an owner terminal action"}
        if not self._workspace_has_repository():
            return 400, {"error": "selected root has no confined repository"}
        try:
            result = self._selected_workspace().run(argv, timeout=15)
        except PermissionError as exc:
            return 400, {"error": str(exc)}
        return 200, {"result": result}

    @staticmethod
    def _context_text(name: Any, text: Any) -> tuple[str, str]:
        if not isinstance(name, str) or not name.strip() or len(name) > 256:
            raise ValueError("context name must contain 1..256 characters")
        if not isinstance(text, str) or not 1 <= len(text) <= _MAX_CONTEXT_CHARS:
            raise ValueError("context text must contain 1..524288 characters")
        return name.strip(), text

    def _remember_context_record(self, scope: str, name: str, text: str, *, persistent: bool) -> dict[str, Any]:
        self._context_sequence += 1
        record = {
            "id": self._context_sequence,
            "scope": scope,
            "name": name,
            "bytes": len(text.encode("utf-8")),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "persistent": persistent,
            "lifetime": "DURABLE_SUBSTRATE" if persistent else (
                "TURN_ATTACHMENT" if scope == "temporary_attachment" else "SESSION_ONLY"
            ),
        }
        if not persistent:
            if sum(len(value) for value in self._context_content.values()) + len(text) > 2 * 1024 * 1024:
                raise ValueError("session context full; remove an item first")
            self._context_content[self._context_sequence] = text
        self.contexts.append(record)
        if len(self.contexts) > 100:
            expired = self.contexts.pop(0)
            self._context_content.pop(expired["id"], None)
        return record

    def _context(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        scope = body.get("scope")
        if not isinstance(scope, str) or scope not in _CONTEXT_SCOPES:
            return 400, {"error": "invalid context scope"}
        if scope == "workspace_knowledge":
            path = body.get("path")
            if not isinstance(path, str) or set(body) != {"scope", "path"}:
                return 400, {"error": "invalid workspace context request"}
            text = self._selected_workspace().read(path)
            record = self._remember_context_record(scope, path, text, persistent=False)
            return 200, {**record, "lifetime": "SESSION_ONLY"}
        name, text = self._context_text(body.get("name"), body.get("text"))
        if scope == "persistent_memory":
            if set(body) != {"scope", "name", "text", "confirm_persist"} or body.get("confirm_persist") is not True:
                return 400, {"error": "persistent memory requires explicit confirm_persist=true"}
            runtime = DurableRuntime(self.root)
            try:
                receipt = runtime.store_external_memory(
                    text,
                    kind="file_context",
                    metadata={"scope": scope, "name": name},
                )
            finally:
                runtime.close()
            record = self._remember_context_record(scope, name, text, persistent=True)
            return 200, {**record, **receipt, "lifetime": "DURABLE_SUBSTRATE"}
        if set(body) != {"scope", "name", "text"}:
            return 400, {"error": "invalid session context request"}
        record = self._remember_context_record(scope, name, text, persistent=False)
        lifetime = "TURN_ATTACHMENT" if scope == "temporary_attachment" else "SESSION_ONLY"
        return 200, {**record, "lifetime": lifetime}

    def _storage_status(self) -> dict[str, Any]:
        runtime = DurableRuntime(self.root)
        try:
            inspection = runtime.inspect()
        finally:
            runtime.close()
        return {
            "substrate_location": str(self.root),
            "system_id": inspection["system_id"],
            "memory_records": inspection["memory"]["memories"],
            "checkpoint_sequence": inspection["sequence"],
            "checkpoint_sha256": inspection["checkpoint_sha256"],
            "memory_digest": inspection["memory_digest"],
            "credentials": "HOST_CONFIGURATION_EXCLUDED",
            "authority": "NOT_TRANSFERRED",
            "encryption": {
                "status": "NOT_ESTABLISHED",
                "detail": "No application-layer encrypted portable bundle format is established; use host storage encryption.",
            },
        }

    def _storage_export(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        destination = body.get("destination")
        if not isinstance(destination, str) or set(body) != {"destination"}:
            return 400, {"error": "invalid export destination"}
        receipt = self.service.export_portable(Path(destination).expanduser().absolute())
        return 200, receipt

    @staticmethod
    def _storage_verify(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        bundle = body.get("bundle")
        expected = body.get("manifest_sha256")
        if not isinstance(bundle, str) or not isinstance(expected, str) or set(body) != {"bundle", "manifest_sha256"}:
            return 400, {"error": "invalid snapshot verification request"}
        receipt = verify_snapshot(Path(bundle).expanduser().absolute(), expected)
        return 200, receipt

    @staticmethod
    def _storage_import(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        bundle = body.get("bundle")
        destination = body.get("destination")
        expected = body.get("manifest_sha256")
        if (
            not isinstance(bundle, str)
            or not isinstance(destination, str)
            or not isinstance(expected, str)
            or set(body) != {"bundle", "destination", "manifest_sha256"}
        ):
            return 400, {"error": "invalid snapshot import request"}
        receipt = import_snapshot(
            Path(bundle).expanduser().absolute(),
            Path(destination).expanduser().absolute(),
            expected,
        )
        return 200, receipt

    def dispatch(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        with self._lock:
            status, result = self._dispatch(method, path, body)
            if status >= 400:
                self.session_events.append({"kind": "request_denied", "path": path, "status": status})
            return status, result

    def _dispatch(self, method: str, path: str, body: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
        data = body or {}
        try:
            if method == "GET" and path == "/api/orbit":
                return 200, {
                    **self.service.orbit_snapshot(),
                    "workspace": {"root": str(self.workspace.root) if self.workspace else None},
                }
            if method == "GET" and path == "/api/memory":
                return 200, {"records": self.service.memory_records()}
            if method == "GET" and path == "/api/trace":
                return 200, {"events": self.service.trace_events(), "session_events": list(self.session_events)}
            if method == "GET" and path == "/api/provider":
                return 200, {
                    "profile": asdict(self.profile), "secret_storage": "ENVIRONMENT_REFERENCE_ONLY",
                    "network_boundary": "REMOTE" if self.profile.remote else "LOCAL",
                }
            if method == "GET" and path == "/api/resources":
                return 200, {"resources": self.service.resource_status()}
            if method == "GET" and path == "/api/workspace":
                return 200, self._workspace_snapshot()
            if method == "GET" and path == "/api/workspace/status":
                return self._workspace_status()
            if method == "GET" and path == "/api/context":
                return 200, {"contexts": list(self.contexts), "default_persistence": "NOT_PERSISTED"}
            if method == "GET" and path == "/api/storage":
                return 200, self._storage_status()
            if method == "POST" and path == "/api/authority":
                return self._authority(data)
            if method == "POST" and path == "/api/provider":
                profile, changed, revoked = self._set_profile(data)
                return 200, {
                    "profile": asdict(profile),
                    "secret_storage": "ENVIRONMENT_REFERENCE_ONLY",
                    "brain_changed": changed,
                    "authority_revoked": revoked,
                }
            if method == "POST" and path == "/api/chat":
                return self._chat(data)
            if method == "POST" and path == "/api/event":
                return self._event(data)
            if method == "POST" and path == "/api/quantum":
                return self._quantum(data)
            if method == "POST" and path == "/api/workspace/allow":
                return self._workspace_allow(data)
            if method == "POST" and path == "/api/workspace/select":
                return self._workspace_select(data)
            if method == "POST" and path == "/api/workspace/read":
                return self._workspace_read(data)
            if method == "POST" and path == "/api/workspace/search":
                return self._workspace_search(data)
            if method == "POST" and path == "/api/workspace/diff":
                return self._workspace_diff(data)
            if method == "POST" and path == "/api/workspace/write":
                return self._workspace_write(data)
            if method == "POST" and path == "/api/workspace/run":
                return self._workspace_run(data)
            if method == "POST" and path == "/api/context/remove":
                context_id = data.get("id")
                if set(data) != {"id"} or type(context_id) is not int:
                    return 400, {"error": "invalid context id"}
                self.contexts = [record for record in self.contexts if record["id"] != context_id]
                self._context_content.pop(context_id, None)
                return 200, {"removed": context_id, "durable_memory_deleted": False}
            if method == "POST" and path == "/api/context":
                return self._context(data)
            if method == "POST" and path == "/api/storage/export":
                return self._storage_export(data)
            if method == "POST" and path == "/api/storage/verify":
                return self._storage_verify(data)
            if method == "POST" and path == "/api/storage/import":
                return self._storage_import(data)
            return 404, {"error": "not found"}
        except PermissionError as exc:
            return 403, {"error": str(exc)}
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
            return 400, {"error": "request rejected; no fallback was performed"}


class _CosmicHandler(BaseHTTPRequestHandler):
    server_version = "BeastBoxCosmic/1"

    @property
    def app(self) -> CosmicApp:
        return self.server.cosmic_app  # type: ignore[attr-defined,no-any-return]

    @property
    def session_token(self) -> str:
        return self.server.session_token  # type: ignore[attr-defined,no-any-return]

    def _headers(self, status: int, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(self), microphone=(self), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()

    def _host_ok(self) -> bool:
        host = self.headers.get("Host", "").split(":", 1)[0].strip("[]")
        try:
            validate_bind_host(host)
            return True
        except ValueError:
            return False

    def _json(self, status: int, value: dict[str, Any]) -> None:
        raw = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8")
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if not self._host_ok():
            self._json(400, {"error": "invalid host"})
            return
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            raw = render_cosmic_ui(self.session_token).encode("utf-8")
            self._headers(200, "text/html; charset=utf-8")
            self.wfile.write(raw)
            return
        status, value = self.app.dispatch("GET", path)
        self._json(status, value)

    def do_POST(self) -> None:
        if not self._host_ok():
            self._json(400, {"error": "invalid host"})
            return
        if not secrets.compare_digest(self.headers.get("X-Beast-Session", ""), self.session_token):
            self._json(403, {"error": "invalid session"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= _MAX_REQUEST_BYTES:
                raise ValueError
            raw = self.rfile.read(length)
            body = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(body, dict):
                raise ValueError
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "invalid JSON request"})
            return
        path = urllib.parse.urlparse(self.path).path
        status, value = self.app.dispatch("POST", path, body)
        self._json(status, value)

    def log_message(self, format: str, *args: Any) -> None:
        return


class CosmicHTTPServer(ThreadingHTTPServer):
    cosmic_app: CosmicApp
    session_token: str


def serve(root: str | Path, host: str = "127.0.0.1", port: int = 8081) -> None:
    bind = validate_bind_host(host)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("port must be an integer in 1..65535")
    server = CosmicHTTPServer((bind, port), _CosmicHandler)
    server.cosmic_app = CosmicApp(root)
    server.session_token = secrets.token_urlsafe(32)
    try:
        runtime = server.cosmic_app.service.orbit_snapshot()["runtime"]
        profile = server.cosmic_app.profile
        print(
            f"BEAST BOX ONLINE / COSMIC.CYPHER\n"
            f"SUBSTRATE: {server.cosmic_app.root}\n"
            f"SYSTEM ID: {runtime['system_id']}\n"
            f"PROVIDER: {profile.kind} / {profile.model}\n"
            f"UI: http://{bind}:{port}\n"
            "AUTHORITY: ALL OFF\n"
            "Swap the brain. Keep the story.",
            file=sys.stderr,
        )
        server.serve_forever()
    finally:
        server.server_close()
