"""Portable copies of verified durable state; never export host configuration."""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path

from . import __version__
from .runtime_cli import backup_database, file_sha256, verify_database

LIMIT = 256 * 1024 * 1024
SECRET_NAMES = (
    "IBM_QUANTUM_TOKEN",
    "QISKIT_IBM_TOKEN",
    "AZURE_CLIENT_SECRET",
    "AZURE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
)


def safe_path(path: Path) -> None:
    if ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("portable state paths must not traverse parents or symlinks")


def private_history_check(path: Path) -> None:
    if path.stat().st_size > LIMIT:
        raise ValueError("portable state exceeds the 256 MiB supported limit")
    data = path.read_bytes()
    if re.search(
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}",
        data,
    ):
        raise ValueError("portable history contains a recognizable credential; export refused")
    if any(value.encode() in data for name in SECRET_NAMES if len(value := os.environ.get(name, "")) >= 12):
        raise ValueError("portable history contains a configured credential; export refused")


def export_snapshot(root: Path, destination: Path) -> dict:
    safe_path(root)
    safe_path(destination)
    if destination.exists():
        raise ValueError("portable export requires a new destination directory")
    if not destination.parent.is_dir():
        raise ValueError("portable export parent directory must exist")
    with tempfile.TemporaryDirectory(prefix=".beast-export-", dir=destination.parent) as temp:
        stage = Path(temp) / "snapshot"
        stage.mkdir(mode=0o700)
        database = stage / "runtime.sqlite3"
        backup_database(root, database)
        db = sqlite3.connect(database)
        try:
            db.execute("PRAGMA journal_mode=DELETE")
        finally:
            db.close()
        database.chmod(0o600)
        private_history_check(database)
        checkpoint = verify_database(database, standalone=True)
        manifest = {
            "schema": "beastbox-portable-state-v1",
            "package_version": __version__,
            "checkpoint_schema": "continuity-checkpoint-v1",
            "system_id": checkpoint["system_id"],
            "checkpoint_sha256": checkpoint["sha256"],
            "sequence": checkpoint["sequence"],
            "database": {"name": "runtime.sqlite3", "bytes": database.stat().st_size, "sha256": file_sha256(database)},
            "authority": "NOT_TRANSFERRED",
            "credentials": "HOST_CONFIGURATION_EXCLUDED",
        }
        path = stage / "manifest.json"
        path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        path.chmod(0o600)
        digest = file_sha256(path)
        # Retain the manifest hash separately; the manifest alone is not a signature.
        verify_snapshot(stage, digest)
        for file in (database, path):
            with file.open("rb") as handle:
                os.fsync(handle.fileno())
        if destination.exists():
            raise ValueError("portable destination appeared during export")
        os.rename(stage, destination)
    return {
        "exported": True,
        "manifest_sha256": digest,
        "system_id": checkpoint["system_id"],
        "checkpoint_sha256": checkpoint["sha256"],
        "authority": "NOT_TRANSFERRED",
    }


def verify_snapshot(bundle: Path, expected: str) -> dict:
    safe_path(bundle)
    if not re.fullmatch("[0-9a-f]{64}", expected):
        raise ValueError("expected manifest SHA-256 must be 64 lowercase hex characters")
    if not bundle.is_dir() or set(p.name for p in bundle.iterdir()) != {"manifest.json", "runtime.sqlite3"}:
        raise ValueError("snapshot must contain exactly manifest.json and runtime.sqlite3")
    for name in ("manifest.json", "runtime.sqlite3"):
        safe_path(bundle / name)
        if not (bundle / name).is_file():
            raise ValueError("snapshot entries must be regular files")
    path = bundle / "manifest.json"
    if path.stat().st_size > 16384 or file_sha256(path) != expected:
        raise ValueError("portable manifest SHA-256 mismatch or oversized manifest")
    data = json.loads(path.read_text())
    fields = {
        "schema",
        "package_version",
        "checkpoint_schema",
        "system_id",
        "checkpoint_sha256",
        "sequence",
        "database",
        "authority",
        "credentials",
    }
    if not isinstance(data, dict) or set(data) != fields or data["schema"] != "beastbox-portable-state-v1":
        raise ValueError("unsupported portable manifest schema or fields")
    if data["authority"] != "NOT_TRANSFERRED" or data["credentials"] != "HOST_CONFIGURATION_EXCLUDED":
        raise ValueError("portable manifest cannot transfer credentials or authority")
    if data["checkpoint_schema"] != "continuity-checkpoint-v1":
        raise ValueError("unsupported checkpoint schema")
    info = data["database"]
    if not isinstance(info, dict) or set(info) != {"name", "bytes", "sha256"} or info["name"] != "runtime.sqlite3":
        raise ValueError("invalid database manifest; paths cannot be supplied by a snapshot")
    database = bundle / "runtime.sqlite3"
    private_history_check(database)
    if database.stat().st_size != info["bytes"] or file_sha256(database) != info["sha256"]:
        raise ValueError("portable database SHA-256 or size mismatch")
    checkpoint = verify_database(database, standalone=True)
    if any(
        data[key] != checkpoint[other]
        for key, other in [("system_id", "system_id"), ("checkpoint_sha256", "sha256"), ("sequence", "sequence")]
    ):
        raise ValueError("portable checkpoint does not match manifest")
    return {
        "verified": True,
        "system_id": checkpoint["system_id"],
        "checkpoint_sha256": checkpoint["sha256"],
        "manifest_sha256": expected,
        "authority": "NOT_TRANSFERRED",
    }


def import_snapshot(bundle: Path, destination: Path, expected: str) -> dict:
    safe_path(destination)
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError("restore requires a new directory in an existing parent")
    verify_snapshot(bundle, expected)
    with tempfile.TemporaryDirectory(prefix=".beast-import-", dir=destination.parent) as temp:
        stage = Path(temp) / "state"
        stage.mkdir(mode=0o700)
        for name in ("manifest.json", "runtime.sqlite3"):
            shutil.copyfile(bundle / name, stage / name)
            (stage / name).chmod(0o600)
        # Verify the copied bytes, closing the source verification/copy race.
        receipt = verify_snapshot(stage, expected)
        (stage / "manifest.json").unlink()
        with (stage / "runtime.sqlite3").open("rb") as handle:
            os.fsync(handle.fileno())
        if destination.exists():
            raise ValueError("restore destination appeared during import")
        os.rename(stage, destination)
    return {**receipt, "restored": True}
