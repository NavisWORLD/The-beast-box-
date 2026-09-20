"""Export a verifiable owner-owned Beast Box substrate; NOT model weights or GGUF.

This CLI runs only on the persistent owner host. It wraps the original audited
portable-state export/verification; it does not expose local file paths through
the internet-facing chat API. A manifest hash is integrity, not a signature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

from beastbox.portable_state import LIMIT, export_snapshot, import_snapshot, safe_path, verify_snapshot

CONTENTS = frozenset({"manifest.json", "runtime.sqlite3"})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def export_archive(root: Path, output: Path) -> dict:
    root, output = root.expanduser().absolute(), output.expanduser().absolute()
    safe_path(root)
    safe_path(output)
    if not root.is_dir() or output.suffix.lower() != ".zip" or not output.parent.is_dir() or output.exists():
        raise ValueError("requires an existing durable state directory and a new .zip destination")
    with tempfile.TemporaryDirectory(prefix=".beast-owner-export-", dir=output.parent) as work:
        staged = Path(work) / "snapshot"
        receipt = export_snapshot(root, staged)
        verify_snapshot(staged, receipt["manifest_sha256"])
        total = sum((staged / name).stat().st_size for name in CONTENTS)
        if total > LIMIT:
            raise ValueError("owner archive exceeds portable-state size limit")
        target = Path(work) / "export.zip"
        with zipfile.ZipFile(target, mode="x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name in sorted(CONTENTS):
                archive.write(staged / name, arcname=name)
        target.chmod(0o600)
        archive_hash = sha256(target)
        # Validate the ZIP by reading it, not just by trusting the writer.
        verify_archive(target, receipt["manifest_sha256"])
        if output.exists():
            raise ValueError("export destination appeared concurrently")
        os.replace(target, output)
    return {
        "schema": "beastbox-owner-archive-v1",
        "archive_sha256": archive_hash,
        "manifest_sha256": receipt["manifest_sha256"],
        "checkpoint_sha256": receipt["checkpoint_sha256"],
        "system_id": receipt["system_id"],
        "bytes": output.stat().st_size,
        "credentials": "EXCLUDED",
        "authority": "NOT_TRANSFERRED",
        "model_weights": "NOT_INCLUDED",
        "gguf": "NOT_INCLUDED",
    }


def verify_archive(archive_path: Path, expected_manifest_sha256: str) -> dict:
    archive_path = archive_path.expanduser().absolute()
    safe_path(archive_path)
    if not archive_path.is_file() or archive_path.stat().st_size > LIMIT + 1024 * 1024:
        raise ValueError("missing or oversized owner archive")
    with zipfile.ZipFile(archive_path, "r") as archive:
        items = archive.infolist()
        if len(items) != len(CONTENTS) or {i.filename for i in items} != CONTENTS:
            raise ValueError("archive entries are not exactly the permitted snapshot files")
        if any(i.is_dir() or i.file_size > LIMIT for i in items) or sum(i.file_size for i in items) > LIMIT:
            raise ValueError("invalid or oversized archive members")
        with tempfile.TemporaryDirectory(prefix="beast-verify-") as work:
            staged = Path(work) / "snapshot"
            staged.mkdir(mode=0o700)
            for name in sorted(CONTENTS):
                target = staged / name
                with archive.open(name) as source, target.open("xb") as dest:
                    copied = 0
                    while chunk := source.read(1024 * 1024):
                        copied += len(chunk)
                        if copied > LIMIT:
                            raise ValueError("archive member exceeds limit")
                        dest.write(chunk)
                target.chmod(0o600)
            return verify_snapshot(staged, expected_manifest_sha256)


def restore_archive(archive_path: Path, destination: Path, expected_manifest_sha256: str) -> dict:
    """Restore only to a new directory, never overwrite existing user state."""
    destination = destination.expanduser().absolute()
    safe_path(destination)
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError("restore requires a new state directory")
    verify_archive(archive_path, expected_manifest_sha256)
    with zipfile.ZipFile(archive_path, "r") as archive:
        with tempfile.TemporaryDirectory(prefix=".beast-restore-", dir=destination.parent) as work:
            staged = Path(work) / "snapshot"
            staged.mkdir(mode=0o700)
            for name in sorted(CONTENTS):
                with archive.open(name) as source, (staged / name).open("xb") as dest:
                    shutil.copyfileobj(source, dest, length=1024 * 1024)
                (staged / name).chmod(0o600)
            receipt = import_snapshot(staged, destination, expected_manifest_sha256)
    return {**receipt, "model_weights": "NOT_INCLUDED", "authority": "NOT_TRANSFERRED"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Existing owner substrate")
    parser.add_argument("--output", type=Path, required=True, help="New .zip archive (must not exist)")
    args = parser.parse_args()
    receipt = export_archive(args.root, args.output)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
