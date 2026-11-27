#!/usr/bin/env python3
"""Write the served RAWRPHOS fingerprint from a verified release asset.

A promotion that changes what the bridge serves must record that fingerprint
in the same motion. This is the same download and check as
beastbox/install_promoted_rawrphos.py: the public release tarball, its sha256,
accepted-checkpoint/model.safetensors, and metadata.json. The sha256 of those
weight bytes is what gets written. See docs/zeref-promote-pin.md.

Ledger accounting (Step 6): a promotion also records the ledger that justifies
advancing the pin, in the pin file's promotion block as `ledger_accounting`:
{"S_lived", "S_taught_lessons", "S_taught_self_study", "R_pin"}. The guard
refuses to advance R_pin unless the lived+taught total grew since the previous
promotion: (dS_lived + dS_taught_lessons + dS_taught_self_study) > 0.
Counting rules (see docs/zeref-promote-pin.md): S_taught_lessons is the
non-empty line count of evidence/zeref-lessons-006/dialogue.jsonl in the
checkout; S_taught_self_study is the rows in that file whose source is the
self-study landing (0 until self-study rows land on main); R_pin is the new
training step. S_lived cannot be counted from the repo: it is the live Talk
turn count (one turn per `Zeref:` line in the live Talk thread), counted by
the caller at promote time and passed as --lived-turns. A pin with no previous
ledger_accounting is treated as all zeros for the delta.
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

# Ledger accounting (Step 6). The dialogue file is the landed lessons-006 mix
# on main; a self-study row counts as landed only once it is in that file
# with the self-study source (the self-study branch alone does not count).
LEDGER_DIALOGUE_REL = Path("evidence/zeref-lessons-006/dialogue.jsonl")
LEDGER_SELF_STUDY_SOURCE = "zeref-self-study-taught"
LEDGER_KEYS = ("S_lived", "S_taught_lessons", "S_taught_self_study", "R_pin")


class PromotePinError(Exception):
    """A check failed. The pin and both brain files stay as they were."""


def count_jsonl_rows(path: Path) -> list[dict]:
    """Non-empty JSONL rows from a file; a missing file counts as no rows."""
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def count_taught_lessons(root: Path) -> int:
    """Landed lessons-006 rows on main: non-empty lines in dialogue.jsonl."""
    path = root / LEDGER_DIALOGUE_REL
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def count_taught_self_study(root: Path) -> int:
    """Self-study rows landed on main: dialogue rows with the self-study source."""
    rows = count_jsonl_rows(root / LEDGER_DIALOGUE_REL)
    return sum(1 for r in rows
               if isinstance(r, dict) and (r.get("source") == LEDGER_SELF_STUDY_SOURCE
                                           or r.get("label") == "TAUGHT"))


def compute_ledger(root: Path, lived_turns: int, step: int) -> dict:
    """Build the ledger_accounting block for a promotion to `step`."""
    if type(lived_turns) is not int or lived_turns < 0:
        raise PromotePinError("refusing to write; lived turns is not a non-negative count")
    if type(step) is not int or step <= 0:
        raise PromotePinError("refusing to write; pin step is not a positive count")
    return {
        "S_lived": lived_turns,
        "S_taught_lessons": count_taught_lessons(root),
        "S_taught_self_study": count_taught_self_study(root),
        "R_pin": step,
    }


def previous_ledger(pin: dict) -> dict:
    """The previous promotion's ledger, or all zeros when none was recorded."""
    promotion = pin.get("promotion")
    ledger = promotion.get("ledger_accounting") if isinstance(promotion, dict) else None
    if not isinstance(ledger, dict):
        return {k: 0 for k in LEDGER_KEYS}
    return {k: (ledger[k] if type(ledger.get(k)) is int and ledger[k] >= 0 else 0)
            for k in LEDGER_KEYS}


def ledger_growth(previous: dict, current: dict) -> int:
    """Growth in lived+taught turns since the previous promotion (R_pin excluded)."""
    return sum(current[k] - previous[k] for k in LEDGER_KEYS if k != "R_pin")


def check_ledger_growth(previous: dict, current: dict) -> None:
    """Refuse a pin advance unless lived+taught turns grew since last time."""
    growth = ledger_growth(previous, current)
    if growth <= 0:
        raise PromotePinError(
            "refusing to advance the pin; ledger did not grow "
            f"(dS_lived={current['S_lived'] - previous['S_lived']}, "
            f"dS_taught_lessons={current['S_taught_lessons'] - previous['S_taught_lessons']}, "
            f"dS_taught_self_study={current['S_taught_self_study'] - previous['S_taught_self_study']})"
        )


def validate_ledger(ledger: dict, step: int) -> None:
    if not isinstance(ledger, dict) or set(ledger) != set(LEDGER_KEYS):
        raise PromotePinError("refusing to write; ledger_accounting keys are not the four counters")
    for key in LEDGER_KEYS:
        if type(ledger[key]) is not int or ledger[key] < 0:
            raise PromotePinError(f"refusing to write; ledger_accounting.{key} is not a non-negative count")
    if ledger["R_pin"] != step:
        raise PromotePinError("refusing to write; ledger_accounting.R_pin is not the new pin step")


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


def promote(tag: str, root: Path, fetch=fetch_bytes, lived_turns: int | None = None) -> dict:
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
    ledger = None
    if lived_turns is not None:
        try:
            current_pin = json.loads((root / PIN_REL).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PromotePinError("refusing to write; pin json unreadable") from exc
        ledger = compute_ledger(root, lived_turns, step)
        check_ledger_growth(previous_ledger(current_pin), ledger)
    write_fingerprint(root, step, model_sha, tag, asset_sha, ledger=ledger)
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


def write_fingerprint(root: Path, step: int, sha: str, tag: str, asset_sha: str,
                      ledger: dict | None = None) -> None:
    if type(step) is not int or SHA_RE.fullmatch(sha) is None or SHA_RE.fullmatch(asset_sha) is None:
        raise PromotePinError("refusing to write; fingerprint is not a step and two sha256 digests")
    if not tag.endswith(sha[:12]):
        raise PromotePinError("refusing to write; release tag does not match the checkpoint")
    if ledger is not None:
        validate_ledger(ledger, step)
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
    if ledger is not None:
        promotion["ledger_accounting"] = ledger
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
    parser.add_argument("--lived-turns", type=int, default=None,
                        help="live Talk turns (one per Zeref: line in the live Talk thread, counted "
                             "at promote time). Required with a release tag: the pin refuses to "
                             "advance unless the ledger grew, and S_lived cannot be counted from the repo.")
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    if sum((bool(args.release_tag), args.check, args.await_bridge)) != 1:
        parser.error("pass one release tag, or --check, or --await-bridge")
    if args.release_tag and args.lived_turns is None:
        parser.error("a promotion needs --lived-turns <count> (live Talk turns, counted at promote time)")
    root = (args.root or ROOT).resolve()
    try:
        if args.check:
            files_agree(root)
            print("PIN_FILES_AGREE")
        elif args.await_bridge:
            pin = json.loads((root / PIN_REL).read_text(encoding="utf-8"))
            poll_bridge(fetch_health, pin["checkpoint_sha256"])
        else:
            result = promote(args.release_tag, root, lived_turns=args.lived_turns)
            print(f"RAWRPHOS_PUBLIC_PIN={result['training_steps']} {result['checkpoint_sha256']}")
    except PromotePinError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
