#!/usr/bin/env python3
"""Choose a Zeref 006 training parent whose recorded lineage reaches the public pin.

The newest zeref-006-cycle release at a cycle can be a sibling whose
parent_checkpoint_sha256 never leads back to the pin. A release qualifies only
when its own gate record accepted it, its tarball sha and model sha match the
record, and walking each release's recorded parent sha reaches the pin. The
caller falls back to the pin when this prints no tag.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

TAG_RE = re.compile(r"^zeref-006-cycle-(\d+)-([0-9a-f]+)$")


def release_record_ok(rec):
    """Own record only: accepted gate, and the bytes match what was recorded."""
    if rec.get("accepted") is not True or rec.get("gate_accepted") is not True:
        return False
    sha = rec.get("checkpoint_sha256")
    if not isinstance(sha, str) or not sha:
        return False
    if rec.get("model_sha256") != sha or rec.get("approval_checkpoint_sha256") != sha:
        return False
    recorded = rec.get("recorded_tarball_sha256")
    if not recorded or rec.get("tarball_sha256") != recorded:
        return False
    if rec.get("metadata_parent_sha256") != rec.get("parent_checkpoint_sha256"):
        return False
    if rec.get("approval_parent_sha256") != rec.get("parent_checkpoint_sha256"):
        return False
    tag = TAG_RE.fullmatch(rec.get("tag") or "")
    if tag is None or not sha.startswith(tag.group(2)):
        return False
    return True


def index_by_sha(releases, pin_sha):
    by = {}
    for rec in releases:
        sha = rec.get("checkpoint_sha256")
        if not sha or sha == pin_sha:
            continue
        prev = by.get(sha)
        if prev is None or (not release_record_ok(prev) and release_record_ok(rec)):
            by[sha] = rec
    return by


def chain_reaches_pin(sha, pin_sha, by_sha, seen=None):
    """Walk recorded parent shas. The pin sha itself is the successful end."""
    if not sha or not pin_sha:
        return False
    if sha == pin_sha:
        return True
    if seen is None:
        seen = set()
    if sha in seen:
        return False
    seen.add(sha)
    rec = by_sha.get(sha)
    if rec is None or not release_record_ok(rec):
        return False
    return chain_reaches_pin(rec.get("parent_checkpoint_sha256"), pin_sha, by_sha, seen)


def select_training_parent(releases, pin_sha):
    """Highest qualifying cycle, then the newest. None means fall back to the pin."""
    by_sha = index_by_sha(releases, pin_sha)
    qualifiers = []
    for rec in by_sha.values():
        if not release_record_ok(rec):
            continue
        if chain_reaches_pin(rec.get("parent_checkpoint_sha256"), pin_sha, by_sha):
            qualifiers.append(rec)
    if not qualifiers:
        return None
    qualifiers.sort(key=lambda rec: (-int(rec.get("cycle") or 0), int(rec.get("list_index") if rec.get("list_index") is not None else 10**9)))
    return qualifiers[0]


def _recorded_sha(text):
    line = text.strip().splitlines()[0] if text.strip() else ""
    return line.split()[0] if line else ""


def _gate_accepted(report):
    if report.get("accepted_as_next_training_parent") is not True:
        return False
    gate = report.get("gate")
    return isinstance(gate, dict) and bool(gate) and all(value is True for value in gate.values())


def record_from_tree(tree, tarball, recorded_tarball_sha, tag, cycle, list_index):
    checkpoint = tree / "accepted-checkpoint"
    meta = json.loads((checkpoint / "metadata.json").read_text())
    approval = json.loads((tree / "approval.json").read_text())
    report = json.loads((tree / "report.json").read_text())
    model_sha = hashlib.sha256((checkpoint / "model.safetensors").read_bytes()).hexdigest()
    tarball_sha = hashlib.sha256(tarball.read_bytes()).hexdigest()
    parent = meta.get("parent_checkpoint_sha256")
    return {
        "tag": tag,
        "cycle": cycle,
        "list_index": list_index,
        "checkpoint_sha256": meta.get("checkpoint_sha256"),
        "parent_checkpoint_sha256": parent,
        "metadata_parent_sha256": parent,
        "approval_checkpoint_sha256": approval.get("checkpoint_sha256"),
        "approval_parent_sha256": approval.get("parent_checkpoint_sha256"),
        "accepted": approval.get("approved") is True,
        "gate_accepted": _gate_accepted(report),
        "tarball_sha256": tarball_sha,
        "recorded_tarball_sha256": recorded_tarball_sha,
        "model_sha256": model_sha,
    }


def _list_tags(repo):
    raw = subprocess.check_output(
        ["gh", "release", "list", "--repo", repo, "-L", "300", "--json", "tagName"],
        text=True,
    )
    found = []
    for index, row in enumerate(json.loads(raw)):
        match = TAG_RE.fullmatch(row.get("tagName") or "")
        if match is None:
            continue
        found.append({"tag": row["tagName"], "cycle": int(match.group(1)), "prefix": match.group(2), "list_index": index})
    return found


def _fetch_record(info, work, repo):
    dest = work / info["tag"]
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        ["gh", "release", "download", info["tag"], "--repo", repo, "-D", str(dest), "--clobber"],
        stdout=subprocess.DEVNULL,
    )
    tarballs = sorted(dest.glob("*.tar.gz"))
    sha_files = sorted(dest.glob("*.sha256"))
    if len(tarballs) != 1 or len(sha_files) != 1:
        raise ValueError("release assets are not one tarball plus one sha256")
    recorded = _recorded_sha(sha_files[0].read_text())
    check = subprocess.run(["sha256sum", "-c", sha_files[0].name], cwd=dest, capture_output=True, text=True)
    if check.returncode != 0:
        raise ValueError("tarball sha256 file does not match the tarball")
    tree = dest / "tree"
    tree.mkdir(exist_ok=True)
    with tarfile.open(tarballs[0]) as archive:
        archive.extractall(tree)
    return record_from_tree(tree, tarballs[0], recorded, info["tag"], info["cycle"], info["list_index"])


def choose_tag(repo, pin_sha, pin_cycle, pin_tag, work):
    tags = _list_tags(repo)
    by_prefix = {}
    for info in tags:
        by_prefix.setdefault(info["prefix"], []).append(info)
    records = []
    loaded = set()

    def load(info):
        if info["tag"] in loaded:
            return
        loaded.add(info["tag"])
        try:
            rec = _fetch_record(info, work, repo)
        except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError, tarfile.TarError, KeyError) as exc:
            print("ZEREF_006_RESUME_REJECTED=" + json.dumps({"tag": info["tag"], "reason": type(exc).__name__}), file=sys.stderr, flush=True)
            return
        records.append(rec)
        print("ZEREF_006_RESUME_SEEN=" + json.dumps({"tag": rec["tag"], "cycle": rec["cycle"], "checkpoint_sha256": rec["checkpoint_sha256"], "parent_checkpoint_sha256": rec["parent_checkpoint_sha256"], "accepted": rec["accepted"], "gate_accepted": rec["gate_accepted"]}), file=sys.stderr, flush=True)

    for info in tags:
        if info["cycle"] > pin_cycle and info["tag"] != pin_tag:
            load(info)
    for _ in range(32):
        known = {rec["checkpoint_sha256"] for rec in records}
        missing = []
        for rec in records:
            parent = rec.get("parent_checkpoint_sha256")
            if parent and parent != pin_sha and parent not in known and parent not in missing:
                missing.append(parent)
        if not missing:
            break
        for parent in missing:
            matched = False
            for info in by_prefix.get(parent[:12], []):
                load(info)
                if any(rec.get("checkpoint_sha256") == parent for rec in records):
                    matched = True
                    break
            if not matched:
                print("ZEREF_006_RESUME_REJECTED=" + json.dumps({"parent_checkpoint_sha256": parent, "reason": "no release for parent sha"}), file=sys.stderr, flush=True)
    by_sha = index_by_sha(records, pin_sha)
    for rec in records:
        local = release_record_ok(rec)
        reaches = bool(local and chain_reaches_pin(rec.get("parent_checkpoint_sha256"), pin_sha, by_sha))
        print("ZEREF_006_RESUME_LINEAGE=" + json.dumps({"tag": rec["tag"], "record_ok": local, "qualifies": reaches}), file=sys.stderr, flush=True)
    return select_training_parent(records, pin_sha)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pin-sha", required=True)
    parser.add_argument("--pin-cycle", required=True, type=int)
    parser.add_argument("--pin-tag", required=True)
    parser.add_argument("--work", required=True)
    args = parser.parse_args(argv)
    if re.fullmatch(r"[0-9a-f]{64}", args.pin_sha) is None:
        raise SystemExit("pin sha is not 64 hex")
    chosen = choose_tag(args.repo, args.pin_sha, args.pin_cycle, args.pin_tag, Path(args.work))
    if chosen is None:
        print("ZEREF_006_RESUME_SELECTED=" + json.dumps({"tag": None, "fallback": "pin"}), file=sys.stderr, flush=True)
        return 0
    print("ZEREF_006_RESUME_SELECTED=" + json.dumps({"tag": chosen["tag"], "checkpoint_sha256": chosen["checkpoint_sha256"]}), file=sys.stderr, flush=True)
    print(chosen["tag"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
