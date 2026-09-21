"""Pinned, CPU-only tiny-model integration for the existing COSMOS provider contract.

This module never runs inference, grants authority, persists state or sends
credentials. It validates a single openly licensed model file and prepares a
loopback-only compatible-provider profile. The local inference *process* is
started separately by the opt-in Railway image.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile
import urllib.request

MODEL_REPO = "bartowski/SmolLM2-135M-Instruct-GGUF"
MODEL_REV = "f0a2b81d63eb57be0e90e82e327e03a7fc66a7dc"
MODEL_FILENAME = "SmolLM2-135M-Instruct-Q4_K_M.gguf"
MODEL_SHA256 = "2e8040ceae7815abe0dcb3540b9995eaa1fa0d2ca9e797d0a635ae4433c68c2d"
MODEL_PATH = Path("/opt/beastbox/models") / MODEL_FILENAME
MODEL_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REV}/{MODEL_FILENAME}"
MODEL_NAME = "SmolLM2-135M-Instruct-Q4_K_M"
LOCAL_URL = "http://127.0.0.1:11522/v1"
MAX_MODEL_BYTES = 120_000_000


def verify_model(path: Path = MODEL_PATH) -> str:
    """Verify the actual GGUF bytes, not an Xet pointer, symlink or model label."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("pinned local GGUF file is absent or is a symlink")
    identity = path.stat()
    if not stat.S_ISREG(identity.st_mode) or not 80_000_000 <= identity.st_size <= MAX_MODEL_BYTES:
        raise ValueError("local GGUF model size is invalid")
    digest = hashlib.sha256()
    with path.open("rb") as reader:
        while chunk := reader.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != MODEL_SHA256:
        raise ValueError("local GGUF model checksum mismatch")
    return digest.hexdigest()


def compatible_profile() -> dict:
    """The existing provider interface can use this profile without new authority."""
    return {"kind": "compatible", "model": MODEL_NAME, "base_url": LOCAL_URL,
            "allow_remote": False, "api_key_env": None}


def fetch_pinned_model(path: Path = MODEL_PATH) -> str:
    """Build-only download. Never fetch a model during a live request or startup."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return verify_model(path)
    if path.is_symlink():
        raise ValueError("model destination may not be a symlink")
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".gguf-download-")
    try:
        with os.fdopen(fd, "wb") as output, urllib.request.urlopen(MODEL_URL, timeout=180) as source:
            if not source.geturl().startswith("https://"):
                raise ValueError("model download redirected to non-HTTPS destination")
            total = 0
            digest = hashlib.sha256()
            while chunk := source.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_MODEL_BYTES:
                    raise ValueError("model artifact too large")
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if total < 80_000_000 or digest.hexdigest() != MODEL_SHA256:
            raise ValueError("downloaded model does not match published SHA-256")
        os.chmod(name, 0o444)
        os.replace(name, path)
        return verify_model(path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


if __name__ == "__main__":
    print(fetch_pinned_model())
