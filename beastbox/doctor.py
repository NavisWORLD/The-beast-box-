"""Non-destructive diagnostics for the installed package and durable state."""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import platform
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from .providers import _assert_loopback, _local_opener


def package_integrity() -> dict:
    try:
        dist = importlib.metadata.distribution("cosmos-beast-box")
        record = dist.read_text("RECORD")
        if not record:
            return {"status": "UNAVAILABLE", "reason": "no installed wheel RECORD"}
        checked = 0
        for name, digest, size in csv.reader(io.StringIO(record)):
            if not name.startswith("beastbox/") or not name.endswith(".py"):
                continue
            if not digest.startswith("sha256="):
                return {"status": "FAILED", "reason": "missing package hash"}
            data = Path(str(dist.locate_file(name))).read_bytes()
            actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
            if digest != "sha256=" + actual or len(data) != int(size):
                return {"status": "FAILED", "reason": "installed source differs from RECORD"}
            checked += 1
        return {
            "status": "VERIFIED" if checked else "UNAVAILABLE",
            "files_checked": checked,
            "boundary": "local RECORD integrity, not publisher authentication",
        }
    except (importlib.metadata.PackageNotFoundError, OSError, ValueError):
        return {"status": "UNAVAILABLE", "reason": "editable/uninstalled or unreadable package"}


def run_doctor(
    ollama_url: str = "http://127.0.0.1:11434",
    *,
    data_dir: Path | None = None,
    provider: str = "reference",
    model: str | None = None,
) -> dict:
    from .optional_resources import resource_status
    from .runtime_cli import verify_database

    root = data_dir or Path.home() / ".beastbox/data"
    checks: dict = {
        "python": sys.version.split()[0],
        "python_supported": (3, 10) <= sys.version_info[:2] <= (3, 12),
        "platform": platform.platform(),
        "sqlite": sqlite3.sqlite_version,
        "package_integrity": package_integrity(),
        "optional_resources": resource_status(),
        "security": {
            "tool_authority": "host-granted per invocation; never restored",
            "credential_export": "host configuration excluded",
            "database_encrypted": False,
        },
    }
    for name in ("qiskit", "qiskit_ibm_runtime", "torch", "huggingface_hub"):
        checks[name + "_available"] = importlib.util.find_spec(name) is not None
    parent = root
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    try:
        if ".." in root.parts or any(p.is_symlink() for p in (root, *root.parents)):
            raise ValueError("unsafe state path")
        with tempfile.TemporaryFile(dir=parent) as handle:
            handle.write(b"beastbox write probe")
            handle.flush()
        checks["state_writable"] = True
        checks["storage_free_bytes"] = shutil.disk_usage(parent).free
    except (OSError, ValueError):
        checks["state_writable"] = False
        checks["storage_free_bytes"] = 0
    checks["cwd_writable"] = checks["state_writable"]  # retained compatibility key
    try:
        database = root / "runtime.sqlite3"
        if database.exists() or database.is_symlink():
            checkpoint = verify_database(database)
            checks["recovery"] = {
                "status": "VERIFIED",
                "system_id": checkpoint["system_id"],
                "checkpoint_sha256": checkpoint["sha256"],
            }
        elif root.exists() and any(root.iterdir()):
            checks["recovery"] = {"status": "FAILED", "reason": "nonempty directory missing required database"}
        else:
            checks["recovery"] = {"status": "COLD_START"}
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        checks["recovery"] = {"status": "FAILED", "reason": "state integrity invalid; restore a verified backup"}
    checks["ollama_local"] = False
    if provider == "ollama":
        try:
            _assert_loopback(ollama_url)
            with _local_opener().open(ollama_url.rstrip("/") + "/api/tags", timeout=2.0) as response:
                raw = response.read(1048577)
            if len(raw) > 1048576:
                raise ValueError("oversized backend response")
            models = json.loads(raw)["models"]
            checks["ollama_models"] = [x["name"] for x in models][:50]
            checks["ollama_local"] = True
            checks["backend"] = {
                "status": "VERIFIED" if model and model in checks["ollama_models"] else "MODEL_REQUIRED",
                "boundary": "discovery only; inference not executed",
            }
        except (OSError, ValueError, KeyError, TypeError):
            checks["backend"] = {"status": "UNAVAILABLE", "reason": "loopback backend inaccessible or invalid"}
    else:
        checks["backend"] = {"status": "REFERENCE_FIXTURE", "network_used": False}
    checks["ok"] = bool(
        checks["python_supported"]
        and checks["state_writable"]
        and checks["storage_free_bytes"] > 0
        and checks["recovery"]["status"] != "FAILED"
        and checks["package_integrity"]["status"] != "FAILED"
        and checks["backend"]["status"] in {"REFERENCE_FIXTURE", "VERIFIED"}
    )
    return checks
