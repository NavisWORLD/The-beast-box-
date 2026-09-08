"""COSMIC.CYPHER owner UI over the canonical durable Beast Box runtime.

The browser owns camera/microphone device handles. The Python side accepts only
explicit bounded events and never grants those host capabilities to model output.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
from typing import Any
import urllib.parse

from .cosmic_ui import render_cosmic_ui
from .durable import DurableRuntime
from .optional_resources import ResourceUnavailable, quantum_event
from .product_services import AuthoritySession, ProductService
from .providers import CompatibleChatProvider, LocalOllamaProvider, ReferenceTextProvider, TextProvider

_MAX_REQUEST_BYTES = 1024 * 1024
_ENV_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")


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
        if kind not in {"reference", "ollama", "compatible"}:
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


class CosmicApp:
    """Testable product controller; HTTP is only a transport adapter around this."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        if self.root.is_symlink():
            raise ValueError("cosmic runtime root cannot be a symlink")
        self.authority = AuthoritySession()
        self.service = ProductService(self.root, authority=self.authority)
        self.profile = load_provider_profile(self.root)

    def _provider(self, profile: ProviderProfile | None = None) -> TextProvider:
        selected = profile or self.profile
        if selected.remote and not self.authority.allowed("cloud"):
            raise PermissionError("cloud authority required")
        return selected.make_provider()

    def _runtime(self, profile: ProviderProfile | None = None) -> DurableRuntime:
        return DurableRuntime(self.root, self._provider(profile))

    def _set_profile(self, raw: dict[str, Any]) -> ProviderProfile:
        profile = ProviderProfile.from_dict(raw)
        self._provider(profile)
        save_provider_profile(self.root, profile)
        self.profile = profile
        return profile

    def _authority(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        action = body.get("action")
        if action == "master_stop" and set(body) == {"action"}:
            stopped = self.authority.master_privacy_stop()
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
        return 200, {"authority": self.authority.snapshot()}

    def _chat(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        text = body.get("text")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 8192:
            return 400, {"error": "chat text must contain 1..8192 characters"}
        previous = self.profile.identity
        profile = self.profile
        if "provider" in body:
            raw = body.get("provider")
            if not isinstance(raw, dict):
                return 400, {"error": "provider must be an object"}
            profile = self._set_profile(raw)
        runtime = self._runtime(profile)
        try:
            before = runtime.inspect()
            result = runtime.respond(text)
            after = runtime.inspect()
        finally:
            runtime.close()
        return 200, {
            "result": result,
            "runtime": after,
            "brain_changed": previous != profile.identity,
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

    def dispatch(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        data = body or {}
        try:
            if method == "GET" and path == "/api/orbit":
                return 200, self.service.orbit_snapshot()
            if method == "GET" and path == "/api/memory":
                return 200, {"records": self.service.memory_records()}
            if method == "GET" and path == "/api/trace":
                return 200, {"events": self.service.trace_events()}
            if method == "GET" and path == "/api/provider":
                return 200, {"profile": asdict(self.profile), "secret_storage": "ENVIRONMENT_REFERENCE_ONLY"}
            if method == "GET" and path == "/api/resources":
                return 200, {"resources": self.service.resource_status()}
            if method == "POST" and path == "/api/authority":
                return self._authority(data)
            if method == "POST" and path == "/api/provider":
                profile = self._set_profile(data)
                return 200, {"profile": asdict(profile), "secret_storage": "ENVIRONMENT_REFERENCE_ONLY"}
            if method == "POST" and path == "/api/chat":
                return self._chat(data)
            if method == "POST" and path == "/api/event":
                return self._event(data)
            if method == "POST" and path == "/api/quantum":
                return self._quantum(data)
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
        server.serve_forever()
    finally:
        server.server_close()
