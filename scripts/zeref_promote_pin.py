#!/usr/bin/env python3
"""Write the served RAWRPHOS fingerprint from a verified release asset.

A promotion that changes what the bridge serves must record that fingerprint
in the same motion. This is the same download and check as
beastbox/install_promoted_rawrphos.py: the public release tarball, its sha256,
accepted-checkpoint/model.safetensors, and metadata.json. The sha256 of those
weight bytes is what gets written. See docs/zeref-promote-pin.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = "NavisWORLD/The-beast-box-"
ROOT = Path(__file__).resolve().parents[1]
PIN_REL = Path("apps/beastbox-cloud/lib/rawrphos-public-pin.json")
BRAIN_RELS = (
    Path("apps/beastbox-cloud/lib/companion/brain.mjs"),
    Path("apps/beastbox-cloud/public/spark/shared/brain.mjs"),
)
BRIDGE_HEALTH_URL = "https://cosmos-owner-bridge-production.up.railway.app/healthz"
TAG_RE = re.compile(r"zeref-006-cycle-[0-9]+-[0-9a-f]{12}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
BRAIN_RE = re.compile(
    r'^(export const RAWRPHOS_PUBLIC_PIN = Object\.freeze\(\{ step: )(\d+)'
    r'(, checkpoint_sha256: ")([0-9a-f]{64})(" \}\);)$',
    re.M,
)
POLL_ATTEMPTS = 50
POLL_DELAY_SECONDS = 30


class PromotePinError(Exception):
    """A check failed. The pin and both brain files stay as they were."""


def asset_url(tag: str) -> str:
    return f"https://github.com/{REPO}/releases/download/{tag}/{tag}.tar.gz"


def fetch_bytes(url: str, timeout: int = 120) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "beastbox-zeref-promote-pin"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_health(url: str = BRIDGE_HEALTH_URL) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "beastbox-zeref-promote-pin"})
    with urllib.request.urlopen(request, timeout=20) as response:
        parsed = json.loads(response.read(8192))
    if not isinstance(parsed, dict):
        raise PromotePinError("bridge health refused")
    return parsed


def parse_sidecar(text: bytes, filename: str) -> str:
    try:
        lines = [line for line in text.decode("utf-8").splitlines() if line.strip()]
    except UnicodeError as exc:
        raise PromotePinError("promoted release asset sha256 mismatch") from exc
    if len(lines) != 1:
        raise PromotePinError("promoted release asset sha256 mismatch")
    digest, _sep, name = lines[0].partition(" ")
    name = name.strip()
    if name.startswith("*"):
        name = name[1:]
    if SHA_RE.fullmatch(digest) is None or name != filename:
        raise PromotePinError("promoted release asset sha256 mismatch")
    return digest


def _reject_member(member: tarfile.TarInfo) -> None:
    path = Path(member.name)
    if path.is_absolute() or ".." in path.parts:
        raise PromotePinError("promoted release asset refused")
    if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
        raise PromotePinError("promoted release asset refused")


def open_checkpoint(tar_bytes: bytes, dest: Path) -> tuple[int, str]:
    tar_path = dest / "release.tar.gz"
    tar_path.write_bytes(tar_bytes)
    try:
        with tarfile.open(tar_path, "r:gz") as archive:
            members = archive.getmembers()
            for member in members:
                _reject_member(member)
            try:
                archive.extractall(dest, members=members, filter="data")
            except TypeError:
                archive.extractall(dest, members=members)
    except PromotePinError:
        raise
    except (tarfile.TarError, OSError, ValueError) as exc:
        raise PromotePinError("promoted release asset refused") from exc
    checkpoint = dest / "accepted-checkpoint"
    model = checkpoint / "model.safetensors"
    meta_path = checkpoint / "metadata.json"
    if model.is_symlink() or meta_path.is_symlink() or not model.is_file() or not meta_path.is_file():
        raise PromotePinError("promoted checkpoint sha256 mismatch")
    if meta_path.stat().st_size > 65536:
        raise PromotePinError("promoted checkpoint metadata mismatch")
    model_sha = hashlib.sha256(model.read_bytes()).hexdigest()
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PromotePinError("promoted checkpoint metadata mismatch") from exc
    step = metadata.get("training_steps")
    if type(step) is not int or metadata.get("checkpoint_sha256") != model_sha:
        raise PromotePinError("promoted checkpoint metadata mismatch")
    return step, model_sha


def promote(tag: str, root: Path, fetch=fetch_bytes) -> dict:
    if TAG_RE.fullmatch(tag) is None:
        raise PromotePinError("release tag refused")
    url = asset_url(tag)
    try:
        tar_bytes = fetch(url)
        sidecar = fetch(url + ".sha256")
    except PromotePinError:
        raise
    except Exception as exc:
        raise PromotePinError("promoted release asset refused") from exc
    if not isinstance(tar_bytes, (bytes, bytearray)) or not isinstance(sidecar, (bytes, bytearray)):
        raise PromotePinError("promoted release asset refused")
    tar_bytes = bytes(tar_bytes)
    expected = parse_sidecar(bytes(sidecar), f"{tag}.tar.gz")
    asset_sha = hashlib.sha256(tar_bytes).hexdigest()
    if asset_sha != expected:
        raise PromotePinError("promoted release asset sha256 mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        step, model_sha = open_checkpoint(tar_bytes, Path(tmp))
    if not tag.endswith(model_sha[:12]):
        raise PromotePinError("release tag does not match model.safetensors sha256")
    write_fingerprint(root, step, model_sha, tag, asset_sha)
    return {
        "training_steps": step,
        "checkpoint_sha256": model_sha,
        "release_tag": tag,
        "release_asset_sha256": asset_sha,
    }


def render_brain(text: str, step: int, sha: str) -> str:
    if len(BRAIN_RE.findall(text)) != 1:
        raise PromotePinError("refusing to write; brain pin constant missing or duplicated")
    return BRAIN_RE.sub(rf"\g<1>{step}\g<3>{sha}\g<5>", text, count=1)


def write_fingerprint(root: Path, step: int, sha: str, tag: str, asset_sha: str) -> None:
    if type(step) is not int or SHA_RE.fullmatch(sha) is None or SHA_RE.fullmatch(asset_sha) is None:
        raise PromotePinError("refusing to write; fingerprint is not a step and two sha256 digests")
    if not tag.endswith(sha[:12]):
        raise PromotePinError("refusing to write; release tag does not match the checkpoint")
    pin_path = root / PIN_REL
    try:
        pin = json.loads(pin_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PromotePinError("refusing to write; pin json unreadable") from exc
    if pin.get("schema") != "rawrphos-public-pin-v1":
        raise PromotePinError("refusing to write; pin schema mismatch")
    promotion = pin.get("promotion")
    if not isinstance(promotion, dict):
        raise PromotePinError("refusing to write; pin promotion block missing")
    for key in ("release_tag", "release_asset_sha256", "candidate_sha256"):
        if key not in promotion:
            raise PromotePinError(f"refusing to write; promotion.{key} missing")
    if "training_steps" not in pin or "checkpoint_sha256" not in pin or "gate_v2" not in pin:
        raise PromotePinError("refusing to write; pin fingerprint missing")
    pin["training_steps"] = step
    pin["checkpoint_sha256"] = sha
    promotion["release_tag"] = tag
    promotion["release_asset_sha256"] = asset_sha
    promotion["candidate_sha256"] = sha
    files = [(pin_path, (json.dumps(pin, indent=1) + "\n").encode("utf-8"))]
    for rel in BRAIN_RELS:
        path = root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise PromotePinError(f"refusing to write; {rel} unreadable") from exc
        files.append((path, render_brain(text, step, sha).encode("utf-8")))
    atomic_replace_all(files)


def _restore(path: Path, previous: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        with temporary.open("wb") as handle:
            handle.write(previous)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def atomic_replace_all(items: list[tuple[Path, bytes]]) -> None:
    originals: list[tuple[Path, bytes]] = []
    temps: list[Path] = []
    try:
        staged: list[tuple[Path, Path]] = []
        for path, data in items:
            if path.is_symlink() or not path.is_file():
                raise PromotePinError(f"refusing to write; {path} is not a regular file")
            originals.append((path, path.read_bytes()))
            descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            os.close(descriptor)
            temporary = Path(name)
            temps.append(temporary)
            with temporary.open("wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((temporary, path))
        for temporary, path in staged:
            os.replace(temporary, path)
            temps.remove(temporary)
    except Exception:
        for path, previous in originals:
            _restore(path, previous)
        raise
    finally:
        for temporary in temps:
            temporary.unlink(missing_ok=True)


def files_agree(root: Path) -> None:
    pin_path = root / PIN_REL
    try:
        pin = json.loads(pin_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PromotePinError("pin fingerprint unreadable") from exc
    step, sha = pin.get("training_steps"), pin.get("checkpoint_sha256")
    if type(step) is not int or not isinstance(sha, str) or SHA_RE.fullmatch(sha) is None:
        raise PromotePinError("pin fingerprint unreadable")
    for rel in BRAIN_RELS:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise PromotePinError(f"{rel} pin constant unreadable") from exc
        found = BRAIN_RE.findall(text)
        if len(found) != 1:
            raise PromotePinError(f"{rel} pin constant unreadable")
        if (int(found[0][1]), found[0][3]) != (step, sha):
            raise PromotePinError(f"{rel} disagrees with the pin")
    promotion = pin.get("promotion")
    if isinstance(promotion, dict) and promotion.get("candidate_sha256") != sha:
        raise PromotePinError("pin candidate_sha256 disagrees with checkpoint_sha256")


def bridge_serves_pin(health: dict, checkpoint_sha256: str) -> bool:
    return (
        isinstance(health, dict)
        and health.get("serving_pin") is True
        and health.get("served_checkpoint_sha256") == checkpoint_sha256
    )


def poll_bridge(fetch_health_fn, checkpoint_sha256: str, attempts: int = POLL_ATTEMPTS,
                delay: float = POLL_DELAY_SECONDS, sleep=time.sleep, echo=print) -> None:
    if type(attempts) is not int or not 1 <= attempts <= POLL_ATTEMPTS:
        raise PromotePinError("bridge poll must be bounded")
    if isinstance(delay, bool) or not isinstance(delay, (int, float)) or not 0 <= delay <= 60:
        raise PromotePinError("bridge poll must be bounded")
    if SHA_RE.fullmatch(checkpoint_sha256) is None:
        raise PromotePinError("pin fingerprint unreadable")
    last: dict = {}
    for attempt in range(1, attempts + 1):
        try:
            health = fetch_health_fn()
        except Exception:
            health = {}
        if not isinstance(health, dict):
            health = {}
        last = health
        echo(
            f"attempt {attempt}: serving_pin={health.get('serving_pin')!r} "
            f"served_checkpoint_sha256={health.get('served_checkpoint_sha256')} want={checkpoint_sha256}"
        )
        if bridge_serves_pin(health, checkpoint_sha256):
            echo("BRIDGE_IN_SYNC")
            return
        if attempt != attempts:
            sleep(delay)
    raise PromotePinError(
        "Live bridge served model does not match the pin. "
        f"want={checkpoint_sha256} served_checkpoint_sha256={last.get('served_checkpoint_sha256')} "
        f"serving_pin={last.get('serving_pin')}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_tag", nargs="?")
    parser.add_argument("--check", action="store_true", help="exit 0 only when the pin and both brain constants agree")
    parser.add_argument("--await-bridge", action="store_true",
                        help="poll bridge /healthz until it serves this pin, then fail if it does not")
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    if sum((bool(args.release_tag), args.check, args.await_bridge)) != 1:
        parser.error("pass one release tag, or --check, or --await-bridge")
    root = (args.root or ROOT).resolve()
    try:
        if args.check:
            files_agree(root)
            print("PIN_FILES_AGREE")
        elif args.await_bridge:
            pin = json.loads((root / PIN_REL).read_text(encoding="utf-8"))
            poll_bridge(fetch_health, pin["checkpoint_sha256"])
        else:
            result = promote(args.release_tag, root)
            print(f"RAWRPHOS_PUBLIC_PIN={result['training_steps']} {result['checkpoint_sha256']}")
    except PromotePinError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
