"""Pinned, opt-in, CPU-only local inference for the existing COSMOS substrate.

The GGUF is a separately licensed upstream model, not a trained Beast Box weight.
No remote inference and no new authority grant. A selected non-reference brain
is never replaced automatically. Provenance is verified before profile handoff.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .cosmic_web import CosmicApp, ProviderProfile

MODEL_ID = "SmolLM2-135M-Instruct-Q4_K_M"
MODEL_PATH = Path("/opt/beastbox/models/SmolLM2-135M-Instruct-Q4_K_M.gguf")
MODEL_SHA256 = "2e8040ceae7815abe0dcb3540b9995eaa1fa0d2ca9e797d0a635ae4433c68c2d"
MODEL_SOURCE = (
    "https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF/resolve/"
    "f0a2b81d63eb57be0e90e82e327e03a7fc66a7dc/"
    "SmolLM2-135M-Instruct-Q4_K_M.gguf"
)
LOCAL_BASE_URL = "http://127.0.0.1:1234/v1"
MIN_BYTES = 90_000_000
MAX_BYTES = 120_000_000


def verify_model(path: Path = MODEL_PATH) -> str:
    """Fail closed on unpinned, absent or corrupted external weights."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("pinned tiny GGUF missing or not a regular file")
    size = path.stat().st_size
    if not MIN_BYTES <= size <= MAX_BYTES:
        raise ValueError("pinned tiny GGUF has unexpected size")
    sha = hashlib.sha256()
    with path.open("rb") as source:
        if source.read(4) != b"GGUF":
            raise ValueError("tiny model is not GGUF")
        source.seek(0)
        for block in iter(lambda: source.read(1024 * 1024), b""):
            sha.update(block)
    digest = sha.hexdigest()
    if digest != MODEL_SHA256:
        raise ValueError("pinned tiny GGUF checksum mismatch")
    return digest


def tiny_profile() -> ProviderProfile:
    return ProviderProfile.from_dict({
        "kind": "compatible", "model": MODEL_ID, "base_url": LOCAL_BASE_URL,
        "allow_remote": False, "api_key_env": None,
    })


def configure_tiny_owner_brain(app: CosmicApp) -> bool:
    """Explicit host opt-in; safely skip a user-selected non-reference provider.

    Returns True only when the pinned tiny model is the active provider. The
    launcher must establish local llama-server readiness before this call.
    """
    if os.environ.get("BEASTBOX_TINY_LOCAL_ENABLED") != "yes":
        return False
    verify_model()
    desired = tiny_profile()
    current = app.profile
    if current == desired:
        return True
    if current.kind != "reference":
        raise ValueError("refusing to overwrite existing user-selected provider")
    # A host-selected default is an *ephemeral provider overlay*: do not
    # overwrite cosmic-provider.json on the volume. Turning off the host flag
    # restores the previous reference selection without rewriting memory.
    revoked = app.authority.revoke_all()
    app.profile = desired
    app.session_events.append({
        "kind": "brain_handoff", "model": desired.model,
        "authority_revoked": revoked, "profile_origin": "HOST_OPT_IN",
    })
    return app.profile == desired
