"""Owner-only transport for the real durable CosmicApp. Run behind an authenticated TLS reverse proxy on persistent compute.

NOT a Vercel Function. Not a multi-user service. Never binds publicly. Do not
mistake the deterministic reference provider for a pretrained model.
"""
from __future__ import annotations

import argparse
import hmac
import json
import math
import os
import re
import urllib.parse
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from beastbox.azure_read import AzureReadError, read_owner_text
from beastbox.bio_inputs import bio_event
from beastbox.chat_jobs import ChatJobs
from beastbox.cloud_connection_checks import verify_connection
from beastbox.cloud_connections import KEY_ENV, MODELS, ConnectionError, ConnectionVault
from beastbox.cns_model_probe import cns_model_probe
from beastbox.cosmic_web import CosmicApp, ProviderProfile
from beastbox.cst_sensor_preview import compare_sensor_state
from beastbox.device_observations import normalize_device_observations
from beastbox.durable import DurableRuntime
from beastbox.engine_growth_report import engine_growth_report
from beastbox.guest_local import guest_local_infer
from beastbox.ollama_models import MODEL_ID, ModelInventoryUnavailable, fetch_public_models
from beastbox.quantum_buddy.cosmos_repository import (
    BuddyStateNotFound,
    BuddyStorageUnavailable,
    CosmosBuddyRepository,
    StaleBuddyState,
)
from beastbox.quantum_buddy.operators import QuantumStateOperator
from beastbox.quantum_buddy.state import (
    SOURCE_CLASSES,
    BuddyCurrentState,
    BuddyStateError,
    validate_vector12,
)
from beastbox.rawrphos_experimental_local import profile as experimental_profile
from beastbox.rawrphos_experimental_local import status as experimental_status
from beastbox.rawrphos_hf import MODEL as HF_NATIVE_MODEL
from beastbox.rawrphos_hf import SPACE_URL as HF_NATIVE_URL
from beastbox.rawrphos_hf import STEP as HF_NATIVE_STEP
from beastbox.rawrphos_hf import WEIGHT_SHA as HF_NATIVE_SHA
from beastbox.rawrphos_hf import PrivateSpaceProvider
from beastbox.rawrphos_hf import profile as hosted_native_profile
from beastbox.rawrphos_local import MODEL as NATIVE_ID
from beastbox.rawrphos_local import SHA as NATIVE_SHA
from beastbox.rawrphos_local import URL as NATIVE_URL
from beastbox.rawrphos_local import profile as native_profile
from beastbox.rawrphos_local import status as native_status
from beastbox.tiny_local import LOCAL_URL, compatible_profile, verify_model

MAX_BYTES = 256_000
GET_ALLOW = frozenset({"orbit", "memory", "trace", "provider", "conversation", "storage", "context", "connections", "bio", "chat-job", "observations", "models", "model-inventory", "engine-growth", "quantum-buddy"})
POST_ALLOW = frozenset({"chat", "chat-start", "context", "connections", "bio", "observations", "models", "azure-read", "guest-local", "cns-model-probe", "quantum-buddy/state", "quantum-buddy/shadow"})


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
        self.cst_preview_enabled = self.bio_enabled and os.environ.get("BEASTBOX_CST_PREVIEW_ENABLED") == "yes"
        self.bio_persist_enabled = self.bio_enabled and os.environ.get("BEASTBOX_BIO_PERSIST_ENABLED") == "yes"
        self.bio_remote_allowed = self.bio_persist_enabled and os.environ.get("BEASTBOX_BIO_REMOTE_ALLOWED") == "yes"
        if self.bio_persist_enabled:
            self.app.authority.grant("sensors")
        self.chat_jobs = ChatJobs(lambda payload: self.app.dispatch("POST", "/api/chat", payload))
        # Host-controlled research switches. None is enabled by a browser payload.
        self.quantum_buddy_enabled = os.environ.get("BEASTBOX_QUANTUM_BUDDY_ENABLED") == "yes"
        self.quantum_buddy_shadow_enabled = (self.quantum_buddy_enabled
            and os.environ.get("BEASTBOX_QUANTUM_BUDDY_SHADOW_ENABLED") == "yes")
        # Separate write authority is retained for consent revocation even if
        # research inference is turned off. Creation/update still require Buddy
        # enabled; disabled-mode access is revoke-only and owner-authenticated.
        self.quantum_buddy_cosmos_writes_enabled = (
            os.environ.get("BEASTBOX_QUANTUM_BUDDY_COSMOS_WRITES_ENABLED") == "yes"
        )
        self.quantum_buddy_repo_factory = CosmosBuddyRepository.from_environment
        self.quantum_buddy_operator_factory = QuantumStateOperator
        self.quantum_buddy_shadow_infer = self._native_buddy_shadow_infer

    def _resolve_provider_secret(self, profile: ProviderProfile) -> str | None:
        if self.vault is None:
            return None
        if profile.kind == "hf_space" and profile.base_url == HF_NATIVE_URL:
            saved = self.vault.read_host_only("huggingface")
            if saved is None:
                raise ConnectionError("Hugging Face owner credential is unavailable")
            return saved["secret"]
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
                if (endpoint and (self.app.profile.base_url == endpoint or
                                  (provider == "huggingface" and self.app.profile.kind == "hf_space"))
                        and isinstance(data["config"], dict)
                        and self.app.profile.model != data["config"].get("model")):
                    return 409, {"error": "Switch to local model in Brain Bay before changing an active cloud model ID."}
                return 200, self.vault.save(provider,data["config"],data["secret"])
            if action == "update_model" and set(data) == {"action","provider","model"} and provider in MODELS:
                endpoint = {"huggingface": "https://router.huggingface.co/v1",
                            "ollama_cloud": "https://ollama.com/v1"}[provider]
                if (self.app.profile.kind == "compatible" and self.app.profile.base_url == endpoint
                        or provider == "huggingface" and self.app.profile.kind == "hf_space"):
                    return 409, {"error": "Switch to local model in Brain Bay before editing this active cloud model ID."}
                updated = self.vault.update_model(provider, data["model"])
                return 200, {**updated, "credential_preserved": True,
                             "model_invoked": False, "inference": "NOT_ATTESTED"}
            if action == "remove" and set(data) == {"action","provider"}:
                # If the active model uses a revoked BYOK connection, change to
                # reference and revoke all authority BEFORE discarding its key.
                endpoint = {"huggingface":"https://router.huggingface.co/v1",
                            "ollama_cloud":"https://ollama.com/v1"}.get(provider)
                deactivated = bool(endpoint and (self.app.profile.base_url == endpoint or
                    (provider == "huggingface" and self.app.profile.kind == "hf_space")))
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
                if provider == "ollama_cloud" and saved["config"]["model"].endswith("-cloud"):
                    return 400, {"error": "Direct Ollama API model IDs must match https://ollama.com/api/tags (for example gpt-oss:120b, without -cloud). Switch to local in Brain Bay, then update the saved model ID without replacing its encrypted key."}
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
                and not self.app.profile.remote and self.app.profile.model != NATIVE_ID):
            raise ValueError("refusing to overwrite a previously selected Beast Box brain")
        # This health request cannot leave this host. Launch happens before
        # OwnerBridge in the opt-in image's entrypoint, never from HTTP input.
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

    def _azure_read_action(self, data: dict) -> tuple[int, dict]:
        """One explicit owner-approved text read. No ambient chat retrieval."""
        if self.vault is None:
            return 503, {"error": "Encrypted Azure credential vault unavailable"}
        if (set(data) != {"blob_name", "read_confirmed"}
                or data.get("read_confirmed") is not True):
            return 400, {"error": "Explicit Azure document read confirmation required"}
        saved = self.vault.read_host_only("azure_blob")
        if saved is None:
            return 404, {"error": "Azure Blob connection not configured"}
        try:
            return 200, read_owner_text(saved, data["blob_name"])
        except AzureReadError as exc:
            return 400, {"error": str(exc)}

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
        choices.append(native_status())
        choices.append(experimental_status())
        listed = self.vault.list_public()["connections"] if self.vault is not None else []
        hf_configured = any(row["provider"] == "huggingface" and row["configured"] for row in listed)
        choices.append({"choice": "rawrphos_hf", "model": HF_NATIVE_MODEL,
                        "label": "RAWRPHØS Native 12K — Private HF ZeroGPU", "kind": "remote",
                        "configured": bool(hf_configured), "requires_spend_approval": True,
                        "readiness": "PRIVATE_SPACE_REQUIRES_OWNER_ATTESTATION" if hf_configured
                                     else "HF_OWNER_CREDENTIAL_NOT_CONFIGURED",
                        "loaded_step": HF_NATIVE_STEP if hf_configured else None})
        if self.vault is not None:
            for item in listed:
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
        native = next(item for item in choices if item["choice"] == "rawrphos_native")
        experimental = next(item for item in choices if item["choice"] == "rawrphos_native_18k_experimental")
        return {
            "active": {"model": profile.model, "kind": profile.kind,
                       "remote": profile.remote,
                       "loaded_step": (HF_NATIVE_STEP if profile.kind == "hf_space"
                                       else experimental["loaded_step"] if profile.base_url == experimental_profile()["base_url"]
                                       else native["loaded_step"]) if profile.model == NATIVE_ID else None,
                       "experimental": profile.base_url == experimental_profile()["base_url"]},
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
        if (choice == "rawrphos_hf" and set(data) == {"choice", "spend_approved"}
                and data["spend_approved"] is True):
            if self.vault is None:
                return 503, {"error": "Encrypted owner vault is required for the private Hugging Face Space"}
            saved = self.vault.read_host_only("huggingface")
            if saved is None:
                return 404, {"error": "Save an owner Hugging Face token in Connections first"}
            remote = PrivateSpaceProvider(api_key=saved["secret"])
            try:
                remote.attest()
            except Exception:
                return 503, {"error": "Private RAWRPHØS Space identity unavailable; selection unchanged"}
            self.app.authority.grant("cloud")
            try:
                profile, changed, revoked = self.app._set_profile(hosted_native_profile())
            except (ValueError, ConnectionError):
                return 503, {"error": "Private RAWRPHØS provider unavailable; selection unchanged"}
            self.app.authority.grant("cloud")
            return 200, {"selected": "rawrphos_hf", "model": profile.model,
                         "loaded_step": HF_NATIVE_STEP, "checkpoint_sha256": HF_NATIVE_SHA,
                         "brain_changed": changed, "authority_revoked": revoked,
                         "cloud_grant": "EXPLICIT_OWNER_SELECTION",
                         "inference": "HOSTED_IDENTITY_ATTESTED_CHAT_NOT_YET_COMPLETED",
                         "substrate": "EXISTING_DURABLE_STATE"}
        if choice == "rawrphos_native_18k_experimental" and set(data) == {"choice"}:
            ready = experimental_status()
            if ready["readiness"] != "INSTALLED_AND_READY":
                return 503, {"error": "Experimental RAWRPHØS unavailable: " + ready["readiness"] +
                             ". Selection unchanged; no automatic fallback."}
            profile, changed, revoked = self.app._set_profile(experimental_profile())
            return 200, {"selected": "rawrphos_native_18k_experimental", "model": profile.model,
                         "loaded_step": ready["loaded_step"],
                         "checkpoint_sha256": ready["checkpoint_sha256"],
                         "experimental": True, "promotion_checks_pass": False,
                         "brain_changed": changed, "authority_revoked": revoked,
                         "no_paid_inference": True, "inference": "NOT_ATTESTED_UNTIL_REAL_CHAT",
                         "substrate": "EXISTING_DURABLE_STATE"}
        if choice == "rawrphos_native" and set(data) == {"choice"}:
            ready = native_status()
            if ready["readiness"] != "INSTALLED_AND_READY":
                return 503, {"error": "RAWRPHØS unavailable: " + ready["readiness"] +
                             ". Selection unchanged; no automatic fallback."}
            profile, changed, revoked = self.app._set_profile(native_profile())
            return 200, {"selected": "rawrphos_native", "model": profile.model,
                         "loaded_step": ready["loaded_step"],
                         "checkpoint_sha256": ready["checkpoint_sha256"],
                         "brain_changed": changed, "authority_revoked": revoked,
                         "no_paid_inference": True, "inference": "NOT_ATTESTED_UNTIL_REAL_CHAT",
                         "substrate": "EXISTING_DURABLE_STATE"}
        if (choice == "ollama_cloud" and set(data) == {"choice", "model", "spend_approved"}
                and data["spend_approved"] is True):
            # Model selection is a single owner-initiated, read-only inventory
            # check followed by a host-only vault model update and a handoff.
            # No chat/inference happens on this route. Caller holds the app lock
            # and run_when_idle, so a pending chat cannot switch brains midway.
            requested = data["model"]
            if not isinstance(requested, str) or MODEL_ID.fullmatch(requested) is None or requested.endswith("-cloud"):
                return 400, {"error": "Choose a canonical Ollama direct API model ID"}
            if self.vault is None:
                return 503, {"error": "Encrypted owner vault is unavailable"}
            saved = self.vault.read_host_only("ollama_cloud")
            if saved is None:
                return 404, {"error": "Ollama Cloud credential is not configured"}
            try:
                available = fetch_public_models()
            except ModelInventoryUnavailable:
                return 503, {"error": "Public Ollama inventory unavailable; no profile or credential changed"}
            if requested not in available:
                return 409, {"error": "Model is absent from Ollama's public direct API inventory; selection unchanged"}
            previous = saved["config"]["model"]
            prior_grant = self.app.authority.allowed("cloud")
            if previous != requested:
                try:
                    self.vault.update_model("ollama_cloud", requested)
                except (ConnectionError, ValueError):
                    return 400, {"error": "Encrypted model metadata update failed; selection unchanged"}
            try:
                status, result = self._connection_action({
                    "action": "activate", "provider": "ollama_cloud", "spend_approved": True
                })
                if status != 200:
                    raise ValueError("model activation failed")
            except (ValueError, OSError, ConnectionError):
                # Restore the old secret-model binding if handoff does not succeed.
                # Never report success or automatically retry billable inference.
                if previous != requested:
                    self.vault.update_model("ollama_cloud", previous)
                if not prior_grant:
                    self.app.authority.revoke("cloud")
                return 503, {"error": "Model handoff not completed; previous profile retained"}
            return 200, {**result, "credential_preserved": True,
                         "inventory": "PUBLIC_ID_LISTED_ACCOUNT_ACCESS_UNVERIFIED",
                         "substrate": "EXISTING_DURABLE_STATE"}
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
        elif action == "cst_preview":
            if set(data) != base_fields | {"compare_confirmed"} or data.get("compare_confirmed") is not True:
                return 400, {"error": "Separate owner approval required for isolated CST preview"}
            if not self.cst_preview_enabled:
                return 503, {"error": "Isolated CST comparison is disabled on this host"}
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
        if action == "cst_preview":
            try:
                return 200, compare_sensor_state(event)
            except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                return 400, {"error": "Sensor-state comparison rejected invalid event"}
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

    def _quantum_buddy_status(self) -> dict:
        """Report host flags, not actual Azure connectivity or account secrets."""
        return {
            "enabled": self.quantum_buddy_enabled,
            "shadow_enabled": self.quantum_buddy_shadow_enabled,
            "cosmos_writes_enabled": self.quantum_buddy_cosmos_writes_enabled,
            "storage_configuration_present": bool(
                os.environ.get("COSMOS_BUDDY_ENDPOINT") and
                os.environ.get("COSMOS_BUDDY_DATABASE")
            ),
            "hardware_enabled": False,
            "model_weights_changed": False,
            "fresh_hardware_used": False,
            "mode": "RESEARCH_SHADOW_ONLY",
        }

    def _quantum_buddy_state_action(self, data: dict) -> tuple[int, dict]:
        """Owner-only state CRUD; never submits QPU work or accesses sensors."""
        # Revocation remains available even when Buddy inference is disabled.
        # It still requires owner authentication and separate Cosmos write authority.
        action = data.get("action")
        if not self.quantum_buddy_enabled and action != "revoke":
            return 503, {"error": "Quantum Buddy is disabled"}
        user_id = data.get("userId")
        if not isinstance(user_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", user_id):
            return 400, {"error": "invalid opaque user ID"}
        if action == "revoke":
            if (set(data) != {"action", "userId", "etag", "scope"}
                    or data.get("scope") not in {"quantum", "state", "both"}
                    or not isinstance(data.get("etag"), str)
                    or not 1 <= len(data["etag"]) <= 128):
                return 400, {"error": "invalid Buddy consent revocation request"}
            if not self.quantum_buddy_cosmos_writes_enabled:
                return 403, {"error": "Cosmos Buddy writes require separate host approval"}
            try:
                repo = self.quantum_buddy_repo_factory()
                state, current_etag = repo.read_current(user_id)
                if current_etag != data["etag"] or state.user_id != user_id:
                    return 409, {"error": "Buddy consent changed; refresh before retrying"}
                # Turning off state conditioning also stops refresh and wipes
                # the current numerical reading. Revoking only refresh leaves
                # an explicitly consented person state available for off-mode.
                state_allowed = (
                    data["scope"] == "quantum"
                    and state.state_conditioning_consent is True
                )
                updated = repo.update_person_state(
                    user_id,
                    dyn12=list(state.dyn12) if state_allowed else [0.0] * 12,
                    etag=current_etag,
                    state_conditioning_consent=state_allowed,
                    quantum_refresh_consent=False,
                )
            except BuddyStateNotFound:
                return 404, {"error": "Buddy state not provisioned"}
            except StaleBuddyState:
                return 409, {"error": "Buddy consent changed; refresh before retrying"}
            except Exception:  # noqa: BLE001 - never echo SDK/provider exception text
                return 503, {"error": "Buddy consent revocation unavailable"}
            return 200, {
                "userId": updated.user_id,
                "stateVersion": updated.state_version,
                "stateConditioningConsent": updated.state_conditioning_consent,
                "quantumRefreshConsent": updated.quantum_refresh_consent,
                "qstateValid": False,
                "fresh_hardware_used": False,
                "historical_data_erased": False,
            }
        if action == "read":
            if set(data) != {"action", "userId"}:
                return 400, {"error": "unsupported Buddy state request"}
            try:
                state, etag = self.quantum_buddy_repo_factory().read_current(user_id)
                if state.user_id != user_id:
                    raise BuddyStorageUnavailable("partition identity mismatch")
            except BuddyStateNotFound:
                return 404, {"error": "Buddy state not provisioned"}
            except Exception:  # noqa: BLE001 - redact external storage errors
                return 503, {"error": "Buddy state unavailable"}
            return 200, {
                "userId": user_id, "stateVersion": state.state_version,
                "dyn12Sha256": state.dyn12_sha256,
                "qstateValid": bool(state.qstate_valid),
                "etag": etag,
                "consent": {
                    "stateConditioning": state.state_conditioning_consent,
                    "quantumRefresh": state.quantum_refresh_consent,
                },
                "raw_media_retained": False,
            }
        if action not in {"create", "update"}:
            return 400, {"error": "unsupported Buddy state action"}
        expected = {
            "action", "userId", "dyn12",
            "stateConditioningConsent", "quantumRefreshConsent",
        }
        if action == "update":
            expected |= {"etag"}
        if set(data) != expected:
            return 400, {"error": "unsupported Buddy state fields"}
        if not self.quantum_buddy_cosmos_writes_enabled:
            return 403, {"error": "Cosmos Buddy writes require separate host approval"}
        if (data["stateConditioningConsent"] is not True
                or type(data["quantumRefreshConsent"]) is not bool):
            return 403, {"error": "explicit Buddy state consent required"}
        try:
            vector = list(validate_vector12(data["dyn12"], "dyn12"))
        except BuddyStateError:
            return 400, {"error": "invalid bounded dyn12"}
        try:
            repo = self.quantum_buddy_repo_factory()
            if action == "create":
                state = BuddyCurrentState.new(
                    user_id=user_id, dyn12=vector, state_version=1,
                    state_conditioning_consent=True,
                    quantum_refresh_consent=data["quantumRefreshConsent"],
                )
                updated = repo.create_current(state)
            else:
                etag = data["etag"]
                if not isinstance(etag, str) or not 1 <= len(etag) <= 128:
                    return 400, {"error": "invalid conditional ETag"}
                updated = repo.update_person_state(
                    user_id, dyn12=vector, etag=etag,
                    state_conditioning_consent=True,
                    quantum_refresh_consent=data["quantumRefreshConsent"],
                )
        except StaleBuddyState:
            return 409, {"error": "Buddy state already exists or was updated"}
        except Exception:  # noqa: BLE001 - external SDK text is never user-facing
            return 503, {"error": "Buddy state write unavailable"}
        return 200, {
            "persisted": True, "model_invoked": False, "fresh_hardware_used": False,
            "raw_media_retained": False,
            "userId": updated.user_id, "stateVersion": updated.state_version,
            "dyn12Sha256": updated.dyn12_sha256,
            "qstateValid": False,
        }

    def _native_buddy_shadow_infer(self, prompt, person, metric, max_tokens, seed):
        """Fixed loopback native server; never allow arbitrary provider URLs."""
        from beastbox.providers import _local_opener

        readiness = native_status()
        if readiness.get("readiness") != "INSTALLED_AND_READY":
            raise RuntimeError("pinned native model unavailable")
        key = os.environ.get("RAWRPHOS_API_KEY", "")
        if len(key) < 32 or any(ch in key for ch in "\r\n"):
            raise RuntimeError("native host authorization not configured")
        body = json.dumps({
            "model": NATIVE_ID,
            "prompt": prompt,
            "control_vector": person,
            "qstate_metric12": metric,
            "max_tokens": max_tokens,
            "seed": seed,
        }, allow_nan=False).encode("utf-8")
        request = urllib.request.Request(
            NATIVE_URL + "/quantum-buddy-shadow",
            data=body, method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + key,
            },
        )
        with _local_opener().open(request, timeout=45) as response:
            raw = response.read(65_537)
            if response.status != 200 or len(raw) > 65_536:
                raise RuntimeError("native shadow response unavailable")
        reply = json.loads(raw)
        if (not isinstance(reply, dict) or reply.get("checkpoint_sha256") != NATIVE_SHA
                or reply.get("model_weights_changed") is not False
                or reply.get("fresh_hardware_used") is not False
                or reply.get("quantum_advantage_proven") is not False):
            raise RuntimeError("native shadow identity mismatch")
        return reply

    def _quantum_buddy_shadow_action(self, data: dict) -> tuple[int, dict]:
        """Explicit owner-only comparison; ordinary /api/chat is unaffected."""
        if not self.quantum_buddy_enabled or not self.quantum_buddy_shadow_enabled:
            return 503, {"error": "Quantum Buddy shadow is disabled"}
        required = {"userId", "prompt", "mode", "max_tokens", "seed"}
        if set(data) != required:
            return 400, {"error": "unsupported Buddy shadow fields"}
        user_id, prompt, mode = data["userId"], data["prompt"], data["mode"]
        count, seed = data["max_tokens"], data["seed"]
        allowed_modes = {"off", "matched_classical", "sim_unentangled",
                         "sim_entangled", "replay"}
        if (not isinstance(user_id, str)
                or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", user_id)
                or not isinstance(prompt, str)
                or not 1 <= len(prompt.strip()) <= 220
                or type(count) is not int or not 1 <= count <= 32
                or type(seed) is not int or not 0 <= seed < 2**63
                or not isinstance(mode, str) or mode not in allowed_modes):
            return 400, {"error": "invalid bounded Buddy shadow request"}
        try:
            repo = self.quantum_buddy_repo_factory()
            state, _etag = repo.read_current(user_id)
            if state.user_id != user_id:
                raise BuddyStorageUnavailable("partition mismatch")
        except BuddyStateNotFound:
            return 404, {"error": "Buddy state not provisioned"}
        except Exception:  # noqa: BLE001 - storage errors may contain credentials
            return 503, {"error": "Buddy state unavailable"}
        if (state.state_conditioning_consent is not True
                or (mode != "off" and state.quantum_refresh_consent is not True)):
            return 403, {"error": "explicit Buddy conditioning and refresh consent required"}
        started = __import__("time").perf_counter()
        try:
            operator = self.quantum_buddy_operator_factory()
            packet = operator.evaluate(
                state.dyn12, mode=mode, circuit_version="qb-v1",
                shot_budget=0, provenance={},
            )
            if (packet.mode != mode or packet.source_class != SOURCE_CLASSES[mode]
                    or packet.source_state_sha256 != state.dyn12_sha256):
                raise BuddyStateError("invalid operator provenance")
            report = self.quantum_buddy_shadow_infer(
                prompt, list(state.dyn12), list(packet.qstate12), count, seed,
            )
            if (not isinstance(report, dict)
                    or report.get("model_weights_changed") is not False
                    or report.get("quantum_advantage_proven") is not False
                    or type(report.get("logit_l2")) not in (float, int)
                    or not math.isfinite(report["logit_l2"])
                    or not re.fullmatch(r"[0-9a-f]{64}",
                                        str(report.get("checkpoint_sha256", "")))):
                raise ValueError("unvalidated native shadow comparison")
            receipt = {
                "userId": user_id,
                "sourceStateSha256": state.dyn12_sha256,
                "stateVersion": state.state_version,
                "status": "SHADOW_EVALUATED",
                "mode": mode,
                "sourceClass": packet.source_class,
                "backend": packet.backend,
                "resultSha256": packet.result_sha256,
                "modelSha256": report["checkpoint_sha256"],
                "logitL2": float(report["logit_l2"]),
                "latencyMs": (__import__("time").perf_counter()-started)*1000,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            # Shadow permission is not permission to mutate Cosmos.
            # The separate host-level write flag gates *all* durable receipts.
            receipt_id = (
                repo.append_history(receipt)
                if self.quantum_buddy_cosmos_writes_enabled
                else None
            )
        except Exception:  # noqa: BLE001 - never echo SDK/model exception text
            return 503, {"error": "Buddy shadow unavailable; ordinary chat unaffected"}
        return 200, {
            "mode": mode,
            "source_class": packet.source_class,
            "backend": packet.backend,
            "sourceStateSha256": packet.source_state_sha256,
            "resultSha256": packet.result_sha256,
            "model_checkpoint_sha256": report["checkpoint_sha256"],
            "logit_l2": float(report["logit_l2"]),
            "response_ordinary": str(report.get("response_ordinary", ""))[:4096],
            "response_buddy": str(report.get("response_buddy", ""))[:4096],
            "history_receipt_id": receipt_id,
            "persisted": receipt_id is not None,
            "fresh_hardware_used": False,
            "model_weights_changed": False,
            "quantum_advantage_proven": False,
            "public_answers_changed": False,
        }

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
        if name == "quantum-buddy" and method == "GET":
            return 200, self._quantum_buddy_status()
        if name == "engine-growth" and method == "GET":
            with self.app._lock:
                return 200, engine_growth_report(self.root)
        if name == "models" and method == "GET":
            with self.app._lock:
                return 200, self._model_catalog()
        if name == "model-inventory" and method == "GET":
            if self.vault is None or self.vault.read_host_only("ollama_cloud") is None:
                return 404, {"error": "Ollama Cloud credential is not configured"}
            try:
                names = fetch_public_models()
            except ModelInventoryUnavailable:
                return 503, {"error": "Public Ollama inventory unavailable; no inference was performed"}
            return 200, {"provider": "ollama_cloud", "models": names,
                         "status": "PUBLIC_MODEL_LIST_ONLY",
                         "credential_reused": True, "account_access_verified": False,
                         "inference_attested": False, "model_invoked": False}
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
                         "cst_preview_enabled": self.cst_preview_enabled,
                         "cns_model_probe_enabled": os.environ.get("BEASTBOX_CNS_MODEL_PROBE_ENABLED", "no") == "yes",
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
                    raise TypeError("expected JSON object")
            except (UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError):
                return 400, {"error": "invalid JSON"}
            # No arbitrary provider URL or environment-variable name may be
            # supplied by an HTTP chat client. Host configuration only.
            if name == "chat" and (set(data) - {"text", "context_ids"}):
                return 400, {"error": "chat accepts only text and selected context IDs"}
            if name == "context" and (
                set(data) != {"scope", "name", "text"} or data.get("scope") != "temporary_attachment"
            ):
                return 400, {"error": "cloud context is temporary attachment data only"}
        if name == "quantum-buddy/state":
            return self._quantum_buddy_state_action(data)
        if name == "quantum-buddy/shadow":
            return self._quantum_buddy_shadow_action(data)
        if name == "cns-model-probe":
            with self.app._lock:
                return self.chat_jobs.run_when_idle(lambda: cns_model_probe(data))
        if name == "guest-local":
            if not self.chat_jobs.acquire_guest():
                return 429, {"error": "Owner inference or local guest slot is busy"}
            try:
                return guest_local_infer(self.root, data)
            finally:
                self.chat_jobs.release_guest()
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
        if name == "azure-read":
            with self.app._lock:
                return self.chat_jobs.run_when_idle(lambda: self._azure_read_action(data))
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
