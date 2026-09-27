#!/usr/bin/env python3
"""Build an isolated, SHA-pinned product tree without changing frozen experiment sources.

The pinned manifest must also be bound to an owner-reviewed signed commit or
external receipt before treating it as authentication against privileged edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

MANIFEST_SHA256 = "fb031195a7055c2a59e98b5532a5d392789fbe4ecf1b42c7aacdd8b664061ec8"
SCHEMA = "finisher-security-patch-manifest-v1"
ALLOWED_TARGETS = {
    "beastbox/persistent_substrate/ledger.py",
    "beastbox/persistent_substrate/substrate.py",
    "beastbox/dad_son.py",
}


class SecurityOverlayError(RuntimeError):
    """Fail-closed patch verification or application failure."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _contained(root: Path, relative: str) -> Path:
    if (not isinstance(relative, str) or not relative or
            relative.startswith("/") or "\\" in relative or
            any(piece in {"", ".", ".."} for piece in relative.split("/"))):
        raise SecurityOverlayError(f"invalid overlay path: {relative!r}")
    target = root.joinpath(*relative.split("/"))
    if target.is_symlink() or root.resolve() not in target.resolve().parents:
        raise SecurityOverlayError(f"overlay target escapes working tree: {relative}")
    return target


def load_manifest(source: Path) -> dict[str, Any]:
    path = source / "patches/PATCH_MANIFEST.json"
    raw = path.read_bytes()
    actual = sha256_bytes(raw)
    if actual != MANIFEST_SHA256:
        raise SecurityOverlayError("pinned patch manifest SHA-256 mismatch")
    manifest = json.loads(raw)
    if raw != canonical_json(manifest):
        raise SecurityOverlayError("patch manifest is not canonical JSON")
    expected_marker = MANIFEST_SHA256 + "  patches/PATCH_MANIFEST.json\n"
    if (source / "patches/PATCH_MANIFEST.sha256").read_text("ascii") != expected_marker:
        raise SecurityOverlayError("patch manifest sidecar disagrees with pinned digest")
    if manifest.get("schema") != SCHEMA or not isinstance(manifest.get("patches"), list):
        raise SecurityOverlayError("unsupported or missing patch manifest schema")
    if len(manifest["patches"]) != 7:
        raise SecurityOverlayError("unexpected security patch count; require reviewed manifest update")
    seen: set[str] = set()
    for entry in manifest["patches"]:
        target = entry.get("target")
        patch_path = entry.get("path")
        if target not in ALLOWED_TARGETS or not isinstance(patch_path, str):
            raise SecurityOverlayError("unreviewed patch target")
        if not patch_path.startswith("patches/") or not patch_path.endswith(".patch"):
            raise SecurityOverlayError("unreviewed patch path")
        if patch_path in seen:
            raise SecurityOverlayError("duplicate patch entry")
        seen.add(patch_path)
        for key in ("original_sha256", "patched_sha256", "patch_sha256"):
            value = entry.get(key)
            if not isinstance(value, str) or len(value) != 64 or any(
                character not in "0123456789abcdef" for character in value
            ):
                raise SecurityOverlayError(f"invalid {key} for {patch_path}")
        actual_patch = sha256_bytes(_contained(source, patch_path).read_bytes())
        if actual_patch != entry["patch_sha256"]:
            raise SecurityOverlayError(f"patch bytes mismatch: {patch_path}")
    return manifest


def apply_overlay(source: Path, destination: Path) -> dict[str, Any]:
    source, destination = source.resolve(), destination.resolve()
    if source == destination or source in destination.parents:
        raise SecurityOverlayError("destination must be outside the original repository")
    if destination.exists():
        raise SecurityOverlayError("product output already exists: will not overwrite")
    if not (source / "pyproject.toml").is_file():
        raise SecurityOverlayError("source is not a Beast Box repository")
    manifest = load_manifest(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".finisher-patch-staging-", dir=destination.parent))
    shutil.rmtree(staged)
    registered = False
    try:
        # A detached worktree preserves Git ancestry for existing acceptance
        # scripts without changing any file in the pristine checkout.
        created = subprocess.run(
            ["git", "-C", str(source), "worktree", "add", "--detach", str(staged), "HEAD"],
            text=True, capture_output=True, check=False,
        )
        if created.returncode:
            raise SecurityOverlayError("cannot create isolated committed-source worktree: " + created.stderr[-1200:])
        registered = True
        if sha256_bytes((staged / "patches/PATCH_MANIFEST.json").read_bytes()) != MANIFEST_SHA256:
            raise SecurityOverlayError("staged commit does not contain pinned manifest")
        receipts: list[dict[str, str]] = []
        for entry in manifest["patches"]:
            target = _contained(staged, entry["target"])
            if not target.is_file():
                raise SecurityOverlayError("frozen source target missing: " + entry["target"])
            if sha256_bytes(target.read_bytes()) != entry["original_sha256"]:
                raise SecurityOverlayError("frozen/intermediate source SHA mismatch: " + entry["target"])
            patch_text = _contained(staged, entry["path"]).read_text(encoding="utf-8")
            expected_header = (
                f"# Target: {entry['target']}\n"
                f"# Original-SHA256: {entry['original_sha256']}\n"
                f"# Expected-Patched-SHA256: {entry['patched_sha256']}\n"
            )
            if expected_header not in patch_text or patch_text.count("\n--- a/") != 1:
                raise SecurityOverlayError("unrecognized patch header/content: " + entry["path"])
            separator = f"--- a/{entry['target']}\n+++ b/{entry['target']}\n"
            if patch_text.count(separator) != 1:
                raise SecurityOverlayError("patch target path mismatch: " + entry["path"])
            unified_diff = patch_text[patch_text.index(separator):]
            for args in (["git", "apply", "--check", "-"], ["git", "apply", "-"]):
                result = subprocess.run(
                    args, input=unified_diff, cwd=staged, text=True,
                    capture_output=True, check=False,
                )
                if result.returncode:
                    raise SecurityOverlayError(
                        "patch failed closed: " + entry["path"] + ": " + result.stderr[-1200:]
                    )
            if sha256_bytes(target.read_bytes()) != entry["patched_sha256"]:
                raise SecurityOverlayError("patched source SHA mismatch: " + entry["target"])
            receipts.append({
                "path": entry["path"],
                "target": entry["target"],
                "original_sha256": entry["original_sha256"],
                "patched_sha256": entry["patched_sha256"],
            })
        receipt = {
            "schema": "finisher-security-overlay-receipt-v1",
            "manifest_sha256": MANIFEST_SHA256,
            "source_commit": manifest["baseline_commit"],
            "patches": receipts,
        }
        output = staged / "build"
        output.mkdir(exist_ok=True)
        (output / "security-overlay-receipt.json").write_bytes(canonical_json(receipt) + b"\n")
        moved = subprocess.run(
            ["git", "-C", str(source), "worktree", "move", str(staged), str(destination)],
            text=True, capture_output=True, check=False,
        )
        if moved.returncode:
            raise SecurityOverlayError("cannot promote fully verified worktree: " + moved.stderr[-1200:])
        registered = False
        return receipt
    finally:
        if registered:
            subprocess.run(
                ["git", "-C", str(source), "worktree", "remove", "--force", str(staged)],
                text=True, capture_output=True, check=False,
            )
        elif staged.exists():
            shutil.rmtree(staged)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.verify_only:
            manifest = load_manifest(args.source)
            print(json.dumps({
                "verified": True, "manifest_sha256": MANIFEST_SHA256,
                "patch_count": len(manifest["patches"]),
            }, sort_keys=True))
        else:
            if args.destination is None:
                parser.error("--destination is required unless --verify-only is set")
            receipt = apply_overlay(args.source, args.destination)
            print(json.dumps({
                "overlay_built": True, "manifest_sha256": MANIFEST_SHA256,
                "patch_count": len(receipt["patches"]),
                "destination": str(args.destination),
            }, sort_keys=True))
    except (OSError, json.JSONDecodeError, SecurityOverlayError) as exc:
        parser.exit(1, f"security overlay FAIL-CLOSED: {exc}\n")


if __name__ == "__main__":
    main()
