"""Owner-only transport for the real durable CosmicApp. Run behind an authenticated TLS reverse proxy on persistent compute.

NOT a Vercel Function. Not a multi-user service. Never binds publicly. Do not
mistake the deterministic reference provider for a pretrained model.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import urllib.parse

from dataclasses import asdict
from beastbox.cosmic_web import CosmicApp, ProviderProfile
from beastbox.cloud_connections import ConnectionVault, ConnectionError, KEY_ENV, MODELS
from beastbox.cloud_connection_checks import verify_connection
from beastbox.bio_inputs import bio_event
from beastbox.device_observations import normalize_device_observations
from beastbox.durable import DurableRuntime
from beastbox.tiny_local import LOCAL_URL, compatible_profile, verify_model
from beastbox.chat_jobs import ChatJobs

MAX_BYTES = 256_000
GET_ALLOW = frozenset({"orbit", "memory", "trace", "provider", "conversation", "storage", "context", "connections", "bio", "chat-job", "observations", "models"})
POST_ALLOW = frozenset({"chat", "chat-start", "context", "connections", "bio", "observations", "models"})


class OwnerBridge:
    def __init__(self, root: Path, token: str):
        if not isinstance(token, str) or len(token) < 32:
            raise ValueError("missing strong bridge token")
        self.token = token
        self.root = root
        self.device_memory_enabled = os.environ.get('BEASTBOX_DEVICE_MEMORY_ENABLED') == 'yes'
        self.vault = ConnectionVault(root) if os.environ.get(KEY_ENV) else None
        if self.vault is not None and os.environ.get("BEASTBOX_HF_MODEL_ID"):
            raise ConnectionError("choose either the explicit host HF provider or encrypted BYOK vault")
        self.app = CosmicApp(root, provider_secret_resolver=self._resolve_provider_secret if self.vault else None)
        self._configure_explicit_local_tiny_provider(root)
        self.local_model_ready = os.environ.get("BEASTBOX_TINY_LOCAL_ENABLED") == "yes"
        self._configure_explicit_hf_provider(root)
        # Opt-in host settings only. No browser-supplied grant or device access.
        self.bio_enabled = os.environ.get("BEASTBOX_BIO_INGEST_ENABLED") == "yes"
        self.bio_persist_enabled = self.bio_enabled and os.environ.get("BEASTBOX_BIO_PERSIST_ENABLED") == "yes"
        self.bio_remote_allowed = self.bio_persist_enabled and os.environ.get("BEASTBOX_BIO_REMOTE_ALLOWED") == "yes"
        if self.bio_persist_enabled:
            self.app.authority.grant("sensors")
        self.chat_jobs = ChatJobs(lambda payload: self.app.dispatch("POST", "/api/chat", payload))

    def _resolve_provider_secret(self, profile: ProviderProfile) -> str | None:
        if self.vault is None:
            return None
        endpoints = {"huggingface": "https://router.huggingface.co/v1",
                     "ollama_cloud": "https://ollama.com/v1"}
        for name, endpoint in endpoints.items():
            if profile.kind == "compatible" and profile.base_url == endpoint:
                item = self.vault.read_host_only(name)
                if item is None or item["config"]["model"] != profile.model:
                    raise ConnectionError("active model credential is unavailable; select again")
                return item["secret"]
        return None

    def _connection_action(self, data: dict) -> tuple[int, dict]:
        if self.vault is None:
            return 503, {"error":"Encrypted owner vault is not provisioned on the durable host"}
        action = data.get("action")
        provider = data.get("provider")
        try:
            if action == "save" and set(data) == {"action","provider","config","secret"}:
                # Changing a selected model ID behind its active profile would
                # invalidate its vault secret binding. Require a safe local
                # handoff first; same-model credential rotation is allowed.
                endpoint = {"huggingface": "https://router.huggingface.co/v1",
                            "ollama_cloud": "https://ollama.com/v1"}.get(provider)
                if (endpoint and self.app.profile.base_url == endpoint
                        and self.app.profile.model != data["config"].get("model")):
                    return 409, {"error": "Switch to local model in Brain Bay before changing an active cloud model ID."}
                return 200, self.vault.save(provider,data["config"],data["secret"])
            if action == "update_model" and set(data) == {"action","provider","model"} and provider in MODELS:
                endpoint = {"huggingface": "https://router.huggingface.co/v1",
                            "ollama_cloud": "https://ollama.com/v1"}[provider]
                if self.app.profile.kind == "compatible" and self.app.profile.base_url == endpoint:
                    return 409, {"error": "Switch to local model in Brain Bay before editing this active cloud model ID."}
                updated = self.vault.update_model(provider, data["model"])
                return 200, {**updated, "credential_preserved": True,
                             "model_invoked": False, "inference": "NOT_ATTESTED"}
            if action == "remove" and set(data) == {"action","provider"}:
                # If the active model uses a revoked BYOK connection, change to
                # reference and revoke all authority BEFORE discarding its key.
                endpoint = {"huggingface":"https://router.huggingface.co/v1",
                            "ollama_cloud":"https://ollama.com/v1"}.get(provider)
                deactivated = bool(endpoint and self.app.profile.base_url == endpoint)
                if deactivated:
                    self.app._set_profile({"kind":"reference"})
                result = self.vault.remove(provider)
                return 200, {**result,"active_model_deactivated":deactivated}
            if action == "test" and set(data) == {"action","provider"}:
                saved = self.vault.read_host_only(provider)
                if saved is None:
                    return 404, {"error":"connection not configured"}
                return 200, verify_connection(provider,saved)
            if action == "activate" and set(data) == {"action","provider","spend_approved"} and provider in MODELS and data["spend_approved"] is True:
                saved = self.vault.read_host_only(provider)
                if saved is None:
                    return 404, {"error":"connection not configured"}
                endpoint = {"huggingface":"https://router.huggingface.co/v1",
                            "ollama_cloud":"https://ollama.com/v1"}[provider]
                if provider == "ollama_cloud" and saved["config"]["model"] in {"gpt-oss:120b", "gpt-oss:20b"}:
                    return 400, {"error": "Ollama Cloud uses a different model ID. Switch to local, then update this saved model name to its -cloud variant."}
                # Explicit owner selection grants this one remote-model
                # operation; the handoff itself revokes previous grants.
                desired = {"kind":"compatible","model":saved["config"]["model"],
                           "base_url":endpoint,"allow_remote":True,"api_key_env":None}
                self.app.authority.grant("cloud")
                profile,changed,revoked = self.app._set_profile(desired)
                self.app.authority.grant("cloud")
                return 200, {"selected":provider,"model":profile.model,
                             "brain_changed":changed,"authority_revoked":revoked,
                             "cloud_grant":"EXPLICIT_OWNER_SELECTION",
                             "inference":"NOT_ATTESTED_UNTIL_REAL_CHAT"}
        except (ValueError, TypeError, KeyError):
            return 400, {"error":"connection request rejected; no secret was returned"}
        return 400, {"error":"unsupported connection action"}

    def _configure_explicit_local_tiny_provider(self, root: Path) -> None:
        """Explicit host-owned CPU model, never a browser-requested model swap."""
        requested = ProviderProfile.from_dict(compatible_profile())
        if os.environ.get("BEASTBOX_TINY_LOCAL_ENABLED") != "yes":
            if self.app.profile == requested:
                raise ValueError("previous tiny model profile requires a running local model host")
            return
        if os.environ.get("BEASTBOX_HF_MODEL_ID"):
            raise ValueError("choose either the local tiny model or a billed HF host provider")
        # Check actual weights even if an existing profile is already selected.
        verify_model()
        if (self.app.profile != requested and self.app.profile.kind != "reference"
                and not self.app.profile.remote):
            raise ValueError("refusing to overwrite a previously selected Beast Box brain")
        # This health request cannot leave this host. Launch happens before
        # OwnerBridge in the opt-in image's entrypoint, never from HTTP input.
        import urllib.request
        from beastbox.providers import _local_opener
        try:
            with _local_opener().open(LOCAL_URL + "/models", timeout=5) as reply:
                if reply.status != 200:
                    raise ValueError("local tiny inference process is not ready")
        except (OSError, ValueError) as exc:
            raise ValueError("local tiny inference process is not ready") from exc
        if self.app.profile.kind == "reference":
            self.app._set_profile(compatible_profile())
        # An owner-selected remote profile survives restart, but its cloud
        # authority does NOT. The local model remains available to select.

    def _configure_explicit_hf_provider(self, root: Path) -> None:
        """Owner-approved one-model HF setup on the durable host; never silently swap a profile."""
        model = os.environ.get("BEASTBOX_HF_MODEL_ID", "").strip()
        if not model:
            return
        if os.environ.get("BEASTBOX_HF_BILLING_APPROVED") != "yes":
            raise ValueError("Hugging Face model requires explicit host-side billing approval")
        token = os.environ.get("HF_TOKEN", "")
        if len(token) < 20 or any(char in token for char in "\r\n"):
            raise ValueError("HF_TOKEN missing or invalid on the persistent host")
        if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?", model) is None:
            raise ValueError("invalid Hugging Face model ID")
        requested = ProviderProfile.from_dict({
            "kind": "compatible",
            "model": model,
            "base_url": "https://router.huggingface.co/v1",
            "allow_remote": True,
            "api_key_env": "HF_TOKEN",
        })
        if (root / "cosmic-provider.json").exists():
            if self.app.profile != requested:
                raise ValueError("refusing to overwrite an existing Beast Box provider profile")
        else:
            self.app.authority.grant("cloud")
            self.app._set_profile(asdict(requested))
        # Explicit host approval is required again after every restart. A
        # model handoff in CosmicApp revokes all previous authority.
        self.app.authority.grant("cloud")

    def _model_catalog(self) -> dict:
        """Expose only installed local and encrypted configured model choices."""
        choices = []
        if self.local_model_ready:
            choices.append({
                "choice": "local",
                "model": compatible_profile()["model"],
                "kind": "local",
                "configured": True,
                "requires_spend_approval": False,
                "readiness": "LOCAL_WEIGHTS_AND_LOOPBACK_VERIFIED",
            })
        if self.vault is not None:
            for item in self.vault.list_public()["connections"]:
                if item["provider"] in MODELS and item["configured"]:
                    choices.append({
                        "choice": item["provider"],
                        "model": item["config"]["model"],
                        "kind": "remote",
                        "configured": True,
                        "requires_spend_approval": True,
                        "readiness": "CREDENTIAL_CONFIGURED_INFERENCE_NOT_ATTESTED",
                    })
        profile = self.app.profile
        return {
            "active": {"model": profile.model, "kind": profile.kind,
                       "remote": profile.remote},
            "remote_grant_active": profile.remote and self.app.authority.allowed("cloud"),
            "reapproval_required": profile.remote and not self.app.authority.allowed("cloud"),
            "choices": choices,
            "inference_attested": False,
            "no_automatic_fallback": True,
        }

    def _model_action(self, data: dict) -> tuple[int, dict]:
        """Owner-initiated model swap without replacing memory or authority."""
        choice = data.get("choice")
        if choice == "local" and set(data) == {"choice"}:
            if not self.local_model_ready:
                return 503, {"error": "Verified local model is unavailable on this host"}
            # Recheck loopback before committing the profile. No paid inference.
            from beastbox.providers import _local_opener
            try:
                with _local_opener().open(LOCAL_URL + "/models", timeout=5) as reply:
                    if reply.status != 200:
                        raise ValueError("local provider not ready")
            except (OSError, ValueError):
                return 503, {"error": "Verified local model readiness failed; selection unchanged"}
            profile, changed, revoked = self.app._set_profile(compatible_profile())
            return 200, {
                "selected": "local", "model": profile.model,
                "brain_changed": changed, "authority_revoked": revoked,
                "no_paid_inference": True, "inference": "NOT_ATTESTED_UNTIL_REAL_CHAT",
                "substrate": "EXISTING_DURABLE_STATE",
            }
        if (choice in MODELS and set(data) == {"choice", "spend_approved"}
                and data["spend_approved"] is True):
            status, result = self._connection_action({
                "action": "activate", "provider": choice, "spend_approved": True,
            })
            return status, result
        return 400, {"error": "Choose a configured model and approve remote usage explicitly"}

    def _observation_action(self, data: dict) -> tuple[int, dict]:
        """Persist *only* explicitly selected, bounded, unverified device text."""
        if not self.device_memory_enabled:
            return 503, {"error": "Owner device memory is disabled on the durable host"}
        try:
            text, metadata = normalize_device_observations(data)
        except (ValueError, TypeError, KeyError):
            return 400, {"error": "invalid, stale or unconsented device observations"}
        # A stored record is retrievable by future models: no guarantee of
        # exclusion when the owner later selects a remote model.
        with self.app._lock:
            runtime = DurableRuntime(self.root)
            try:
                receipt = runtime.store_external_memory(
                    text, kind="device_observation", metadata=metadata
                )
            finally:
                runtime.close()
        return 200, {
            "persisted": True, "model_invoked": False,
            "raw_media_transmitted": False, "source_verified": False,
            "memory_id": receipt["memory_id"],
            "checkpoint_sha256": receipt["checkpoint"]["sha256"],
            "text_sha256": receipt["text_sha256"],
        }

    def _bio_action(self, data: dict) -> tuple[int, dict]:
        """Process only owner-consented numerical summaries; never access devices."""
        if not self.bio_enabled:
            return 503, {"error": "Bio input is disabled on the persistent host"}
        action = data.get("action")
        base_fields = {"action", "source", "consent", "readings"}
        if action == "preview":
            if set(data) != base_fields:
                return 400, {"error": "unsupported bio request"}
        elif action == "persist":
            if set(data) not in (base_fields | {"persist_confirmed"},
                                 base_fields | {"persist_confirmed", "remote_share_confirmed"}):
                return 400, {"error": "unsupported bio request"}
        else:
            return 400, {"error": "unsupported bio action"}
        try:
            event = bio_event(readings=data["readings"], source=data["source"],
                              consent=data["consent"])
        except (ValueError, TypeError, KeyError):
            return 400, {"error": "invalid, out-of-range, or unconsented bio measurements"}
        if action == "preview":
            return 200, {"event": event, "persisted": False, "model_invoked": False,
                         "raw_media_transmitted": False, "source_verified": False}
        if not self.bio_persist_enabled or data.get("persist_confirmed") is not True:
            return 403, {"error": "Explicit host retention approval and owner confirmation required"}
        # Keep remote-provider selection, permission checks and durable dispatch
        # atomic with BYOK activation. Without this lock, another request could
        # select a remote model between the sharing check and inference.
        with self.app._lock:
            if self.app.profile.remote and (
                not self.bio_remote_allowed or data.get("remote_share_confirmed") is not True
            ):
                return 403, {"error": "Remote bio sharing requires separate explicit approval"}
            if not self.app.authority.allowed("sensors"):
                return 403, {"error": "Sensor authority revoked; no bio data persisted"}
            status, result = self.app.dispatch(
                "POST", "/api/event", {"modality": "sensor", "event": event}
            )
        if status != 200:
            return status, {"error": result.get("error", "Bio event processing failed")}
        return 200, {"persisted": True, "model_invoked": True, "raw_media_transmitted": False,
                     "source_verified": False, "event_sha256": result["result"]["event"]["sha256"],
                     "system_id": result["runtime"]["system_id"],
                     "checkpoint_sha256": result["runtime"]["checkpoint_sha256"]}

    def dispatch(self, method: str, path: str, auth: str, body: bytes = b""):
        if not hmac.compare_digest(
            auth.encode("utf-8", errors="replace"),
            ("Bearer " + self.token).encode("utf-8")
        ):
            return 401, {"error": "unauthorized"}
        parsed = urllib.parse.urlsplit(path)
        if parsed.fragment or (parsed.query and not (method == "GET" and parsed.path == "/api/chat-job")):
            return 404, {"error": "unsupported route"}
        if not parsed.path.startswith("/api/"):
            return 404, {"error": "unsupported route"}
        name = parsed.path.removeprefix("/api/")
        allowed = GET_ALLOW if method == "GET" else POST_ALLOW if method == "POST" else frozenset()
        if name not in allowed:
            return 404, {"error": "unsupported route"}
        if name == "models" and method == "GET":
            with self.app._lock:
                return 200, self._model_catalog()
        if name == "chat-job" and method == "GET":
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            if set(query) != {"id"} or len(query["id"]) != 1:
                return 400, {"error": "invalid chat job query"}
            return self.chat_jobs.get(query["id"][0])
        if name == "observations" and method == "GET":
            return 200, {"enabled": self.device_memory_enabled, "raw_media_accepted": False,
                         "owner": "SINGLE_OWNER_CONSENT", "source_verified": False}
        if name == "bio" and method == "GET":
            return 200, {"enabled": self.bio_enabled,
                         "persist_enabled": self.bio_persist_enabled,
                         "remote_enabled": self.bio_remote_allowed,
                         "owner": "SINGLE_OWNER_PREVIEW",
                         "source_verified": False}
        if name == "connections" and method == "GET":
            if self.vault is None:
                return 200, {"vault":"HOST_KEY_REQUIRED","connections":[],"owner":"SINGLE_OWNER_PREVIEW"}
            return 200, self.vault.list_public()
        if len(body) > MAX_BYTES:
            return 413, {"error": "request too large"}
        data = None
        if method == "POST":
            try:
                data = json.loads(body.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("expected JSON object")
            except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
                return 400, {"error": "invalid JSON"}
            # No arbitrary provider URL or environment-variable name may be
            # supplied by an HTTP chat client. Host configuration only.
            if name == "chat" and (set(data) - {"text", "context_ids"}):
                return 400, {"error": "chat accepts only text and selected context IDs"}
            if name == "context" and (
                set(data) != {"scope", "name", "text"} or data.get("scope") != "temporary_attachment"
            ):
                return 400, {"error": "cloud context is temporary attachment data only"}
        if name == "chat-start":
            return self.chat_jobs.start(data)
        if name == "models":
            with self.app._lock:
                return self.chat_jobs.run_when_idle(lambda: self._model_action(data))
        if name == "connections":
            with self.app._lock:
                if data.get("action") in {"activate", "remove", "save", "update_model"}:
                    return self.chat_jobs.run_when_idle(lambda: self._connection_action(data))
                return self._connection_action(data)
        if name == "bio":
            return self._bio_action(data)
        if name == "observations":
            return self._observation_action(data)
        return self.app.dispatch(method, parsed.path, data)


class Handler(BaseHTTPRequestHandler):
    server_version = "BeastBoxOwnerBridge/1"
    protocol_version = "HTTP/1.1"

    @property
    def bridge(self) -> OwnerBridge:
        return self.server.bridge

    def _emit(self, status: int, value: dict) -> None:
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            # A disconnected HTTP client must not crash the owner bridge or log sensitive output.
            return

    def _handle(self, method: str) -> None:
        # The only unauthenticated path: bounded, non-sensitive runtime readiness
        # for a managed HTTPS reverse proxy. No model or owner state is returned.
        if method == "GET" and self.path == "/healthz":
            self._emit(200, {"ready": True, "service": "beastbox-owner-bridge"})
            return
        auth = self.headers.get("Authorization", "")
        if method == "POST":
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._emit(400, {"error": "missing or invalid Content-Length"})
                return
            if not 0 <= length <= MAX_BYTES:
                self._emit(413, {"error": "request too large"})
                return
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                self._emit(415, {"error": "JSON content type required"})
                return
            raw = self.rfile.read(length)
        else:
            raw = b""
        status, result = self.bridge.dispatch(method, self.path, auth, raw)
        self._emit(status, result)

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_OPTIONS(self) -> None:
        self._emit(405, {"error": "CORS disabled"})

    def log_message(self, format: str, *args: object) -> None:
        # Never log user prompts, bearer values, record text, raw paths or credentials.
        return


class Server(ThreadingHTTPServer):
    daemon_threads = True
    bridge: OwnerBridge


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--port", type=int, default=11521)
    args = parser.parse_args()
    root = args.data_dir.expanduser().absolute()
    if not root.is_dir() or root.is_symlink():
        parser.error("data directory must be a pre-existing real durable directory")
    if str(root).startswith(("/tmp/", "/var/task/", "/run/", "/dev/shm/")):
        parser.error("ephemeral directory refused for production substrate")
    token = os.getenv("BEASTBOX_CLOUD_BRIDGE_TOKEN", "")
    try:
        bridge = OwnerBridge(root, token)
    except ValueError as exc:
        parser.error(str(exc))
    if not 1 <= args.port <= 65535:
        parser.error("port must be in 1..65535")
    server = Server(("127.0.0.1", args.port), Handler)
    server.bridge = bridge
    print(f"BEAST BOX OWNER BRIDGE: loopback: {args.port}; durable root configured; bearer required; no public bind.", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
