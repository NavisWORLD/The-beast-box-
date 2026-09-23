"""Encrypted single-owner cloud connection vault for the persistent Beast Box bridge.

Only encrypted credential/config payloads are persisted, outside runtime.sqlite3.
NO browser/localStorage/Vercel-file-system storage. Never export this SQLite file.
One owner only: do not claim multi-tenant security or production certification.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import json
import os
import re
import secrets
import sqlite3
import threading
from pathlib import Path

KEY_ENV = "BEASTBOX_CONNECTION_VAULT_KEY"
DATABASE = "owner-connections.sqlite3"
PROVIDERS = ("huggingface", "ollama_cloud", "azure_blob", "ibm_watsonx", "ibm_quantum")
MODELS = frozenset(("huggingface", "ollama_cloud"))
ALLOWED_CONFIG = {
    "huggingface": frozenset(("model",)),
    "ollama_cloud": frozenset(("model",)),
    "azure_blob": frozenset(("account", "container", "auth_mode")),
    "ibm_watsonx": frozenset(("region", "project_id", "model")),
    "ibm_quantum": frozenset(("instance",)),
}
MODEL_RE = re.compile(r"[A-Za-z0-9_.:/-]{1,180}\Z")
REGIONS = frozenset(("us-south", "eu-de", "jp-tok", "au-syd", "ca-tor", "eu-gb"))


class ConnectionError(ValueError):
    """Sanitized error: callers must never include user secret values."""


def _key_from_env() -> bytes:
    text = os.environ.get("BEASTBOX_CONNECTION_VAULT_KEY", "")
    try:
        key = base64.b64decode(text, validate=True)
    except (ValueError, base64.binascii.Error):
        key = b""
    if len(key) != 32 or not text:
        raise ConnectionError("connection vault requires a separate host-only 32-byte base64 encryption key")
    return key


def _validate(provider: str, config: object, secret: object) -> tuple[dict[str, str], str]:
    if provider not in PROVIDERS:
        raise ConnectionError("unsupported cloud provider")
    if not isinstance(config, dict) or (set(config) != ALLOWED_CONFIG[provider] and not (provider == "azure_blob" and set(config) == {"account", "container"})):
        raise ConnectionError("invalid provider configuration fields")
    if any(not isinstance(v, str) or not v.strip() or len(v) > 180 or "\x00" in v for v in config.values()):
        raise ConnectionError("invalid provider configuration")
    cfg = {str(k):v.strip() for k,v in config.items()}
    if not isinstance(secret, str) or not 12 <= len(secret) <= 4096 or any(c in secret for c in "\r\n\x00"):
        raise ConnectionError("missing or invalid private credential")
    if provider in MODELS:
        if MODEL_RE.fullmatch(cfg["model"]) is None or "://" in cfg["model"]:
            raise ConnectionError("invalid hosted model identifier")
        if provider == "huggingface" and (re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?",cfg["model"]) is None or ".." in cfg["model"]):
            raise ConnectionError("invalid Hugging Face repository/model identifier")
    if provider == "azure_blob":
        # Legacy saved records without auth_mode remain SAS; never reinterpret
        # an existing credential as a broadly privileged account key.
        cfg.setdefault("auth_mode", "container_sas")
        if cfg["auth_mode"] not in ("container_sas", "account_key"):
            raise ConnectionError("unsupported Azure credential type")
        if re.fullmatch(r"[a-z0-9]{3,24}",cfg["account"]) is None or (
            len(cfg["container"]) > 63 or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?",cfg["container"]) is None
        ):
            raise ConnectionError("invalid Azure account or container name")
        if cfg["auth_mode"] == "container_sas":
            if "sig=" not in secret or "sp=" not in secret:
                raise ConnectionError("provide a scoped Azure container SAS token")
        else:
            # An account key grants broad rights at Azure. Encrypt it only on
            # the host; all currently exposed operations remain read-only.
            try:
                raw_key = base64.b64decode(secret, validate=True)
            except (ValueError, base64.binascii.Error):
                raw_key = b""
            if len(raw_key) != 64:
                raise ConnectionError("invalid Azure Storage account key format")
    if provider == "ibm_watsonx":
        if cfg["region"] not in REGIONS or re.fullmatch(r"[A-Za-z0-9_-]{4,128}",cfg["project_id"]) is None:
            raise ConnectionError("invalid IBM watsonx region or project")
        if MODEL_RE.fullmatch(cfg["model"]) is None:
            raise ConnectionError("invalid IBM model identifier")
    if provider == "ibm_quantum" and re.fullmatch(r"[A-Za-z0-9_./:-]{1,180}",cfg["instance"]) is None:
        raise ConnectionError("invalid IBM Quantum instance identifier")
    return cfg, secret


class ConnectionVault:
    def __init__(self, root: Path, key: bytes | None = None):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        self._aead_cls = AESGCM
        self._key = key if key is not None else _key_from_env()
        if len(self._key) != 32:
            raise ConnectionError("vault encryption key must be 32 bytes")
        root = Path(root)
        if not root.is_dir() or root.is_symlink():
            raise ConnectionError("vault requires an existing durable state directory")
        self.path = root / DATABASE
        if self.path.is_symlink():
            raise ConnectionError("credential database cannot be a symlink")
        self._lock = threading.RLock()
        with self._open() as db:
            db.execute("CREATE TABLE IF NOT EXISTS connections (provider TEXT PRIMARY KEY, sealed BLOB NOT NULL)")
            db.commit()

    @contextmanager
    def _open(self):
        # Database content is encrypted with AES-GCM; SQLite -journal holds ciphertext.
        if self.path.is_symlink():
            raise ConnectionError("credential database cannot be a symlink")
        db = sqlite3.connect(self.path,timeout=8)
        try:
            os.chmod(self.path,0o600)
            yield db
        finally:
            db.close()

    def _seal(self, provider: str, payload: dict) -> bytes:
        nonce = secrets.token_bytes(12)
        aad = ("beastbox-owner-connection-v1:" + provider).encode()
        return nonce + self._aead_cls(self._key).encrypt(nonce,json.dumps(payload,sort_keys=True).encode(),aad)

    def _unseal(self, provider: str, blob: bytes) -> dict:
        if len(blob) < 29:
            raise ConnectionError("stored cloud connection is invalid")
        nonce,body = blob[:12],blob[12:]
        try:
            raw = self._aead_cls(self._key).decrypt(nonce,body,("beastbox-owner-connection-v1:"+provider).encode())
            result = json.loads(raw)
        except Exception as exc:  # InvalidTag and JSON errors fail closed without exposing values
            raise ConnectionError("stored cloud connection cannot be authenticated") from exc
        if not isinstance(result,dict) or set(result)!={"config","secret"}:
            raise ConnectionError("stored cloud connection has invalid structure")
        cfg,secret = _validate(provider,result["config"],result["secret"])
        return {"config":cfg,"secret":secret}

    def save(self, provider: str, config: dict, secret: str) -> dict:
        config,secret = _validate(provider,config,secret)
        encrypted = self._seal(provider,{"config":config,"secret":secret})
        with self._lock,self._open() as db:
            db.execute("INSERT INTO connections(provider,sealed) VALUES(?,?) ON CONFLICT(provider) DO UPDATE SET sealed=excluded.sealed",(provider,encrypted))
            db.commit()
        return self.public(provider)

    def update_model(self, provider: str, model: str) -> dict:
        """Owner-requested model ID change; preserve the encrypted credential.

        This never tests or invokes the selected model, and never exposes its key.
        The bridge must first ensure the prior model is not actively selected.
        """
        if provider not in MODELS or not isinstance(model, str):
            raise ConnectionError("unsupported model update")
        with self._lock:
            current = self.read_host_only(provider)
            if current is None:
                raise ConnectionError("model connection is not configured")
            new_config, existing_secret = _validate(
                provider, {"model": model}, current["secret"]
            )
            return self.save(provider, new_config, existing_secret)

    def read_host_only(self, provider: str) -> dict | None:
        if provider not in PROVIDERS:
            raise ConnectionError("unsupported cloud provider")
        with self._lock,self._open() as db:
            row = db.execute("SELECT sealed FROM connections WHERE provider=?",(provider,)).fetchone()
        return self._unseal(provider,row[0]) if row else None

    def public(self, provider: str) -> dict:
        item = self.read_host_only(provider)
        if item is None:
            return {"provider":provider,"configured":False,"config":{},"credential":"NOT_CONFIGURED"}
        return {"provider":provider,"configured":True,"config":item["config"],
                "credential":"ENCRYPTED_HOST_ONLY","mode":"INFERENCE" if provider in MODELS else "CONFIGURED_NOT_CONNECTED"}

    def list_public(self) -> dict:
        return {"owner":"SINGLE_OWNER_PREVIEW","vault":"ENCRYPTED_HOST_ONLY",
                "connections":[self.public(provider) for provider in PROVIDERS],
                "active_model":"READ_EXISTING_PROVIDER_PROFILE","automatic_authority":False}

    def remove(self, provider: str) -> dict:
        if provider not in PROVIDERS:
            raise ConnectionError("unsupported cloud provider")
        with self._lock,self._open() as db:
            db.execute("DELETE FROM connections WHERE provider=?",(provider,))
            db.commit()
        return {"provider":provider,"configured":False,"revoked_in_app":True,
                "note":"Also revoke the underlying key at the provider; deleting a local copy cannot revoke it remotely."}
