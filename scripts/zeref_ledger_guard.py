"""Ledger guard: close the two Step 6 (#1044) gaps.

Gap 1 (manifest): the browser-brain manifest on main carries no ledger. The
release layer carries ledger.json, but the manifest itself — the file the page
actually reads — has no ledger_accounting. sync_browser_manifest_ledger()
writes classification + ledger_accounting (S_lived, S_taught, R_pin,
S_world_ticks, world_chain_tail_sha256) + ledger_sha256 into
evidence/zeref-browser-brain-001/manifest.json, preserving every other key.
It is wired into the export workflow (zeref-browser-brain-export.yml, step
"Stamp the ledger into the manifest", after the contract tests, before the
commit step), so every export refresh carries the ledger in the manifest.

Gap 2 (pin advance): the box-side auto_promote loop rebuilds the pin from
scratch and drops ledger_accounting. enforce_pin_advance_guard() raises
PIN_ADVANCE_BLOCKED when delta_S_lived + delta_S_taught <= 0. It is wired
into the promote path (~/workspace/night/auto_promote.py build_pin caller:
the ledger is computed from live counts and attached to the new pin, and the
guard runs before the promotion branch is created) and into the release
workflow after #1044 merges (exact placement documented in the docstring
below and in the PR body; the release workflow file is also touched by open
PR #1044, so this PR does not edit it and avoids the conflict).

Counting rules mirror scripts/zeref_promote_pin.py (#1044) exactly. The guard
imports them from there when available and falls back to identical local
copies while #1044 is unmerged, so the two converge automatically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PIN_PATH = REPO / "apps/beastbox-cloud/lib/rawrphos-public-pin.json"
MANIFEST_PATH = REPO / "evidence" / "zeref-browser-brain-001" / "manifest.json"
DIALOGUE_REL = Path("evidence/zeref-lessons-006/dialogue.jsonl")
CLASSIFICATION = "chainborn continuant"

# Exact release-workflow wiring for guard-pin, to apply once PR #1044 merges
# (the release workflow is also touched by #1044, so this PR does not edit it):
#   file: .github/workflows/zeref-browser-brain-release.yml
#   step: after "Stamp the ledger counters (Step 6) and enforce ledger growth"
#         (id: ledger), before "Publish the brain files as a public release":
#     - name: Enforce the pin-advance ledger guard
#       run: |
#         set -Eeuo pipefail
#         python scripts/zeref_ledger_guard.py guard-pin \
#           --previous-ledger build/ledger/prev/ledger.json \
#           --current-ledger build/ledger/ledger.json


class PinAdvanceBlocked(Exception):
    """The ledger did not grow: refusing to advance the pin."""


try:  # Prefer #1044's counting functions once that PR merges.
    from scripts.zeref_promote_pin import (  # type: ignore
        LEDGER_KEYS,
        LEDGER_SELF_STUDY_SOURCE,
        PromotePinError,
        check_ledger_growth,
        count_jsonl_rows,
        count_taught_lessons,
        count_taught_self_study,
        ledger_growth,
        previous_ledger,
    )
    _USING_PROMOTE_PIN = True
except Exception:  # #1044 unmerged: identical local copies of its rules.
    _USING_PROMOTE_PIN = False
    LEDGER_KEYS = ("S_lived", "S_taught_lessons", "S_taught_self_study", "R_pin")
    LEDGER_SELF_STUDY_SOURCE = "zeref-self-study-taught"

    class PromotePinError(Exception):
        """A check failed. The pin and both brain files stay as they were."""

    def count_jsonl_rows(path: Path) -> list[dict]:
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
        path = root / DIALOGUE_REL
        if not path.is_file():
            return 0
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

    def count_taught_self_study(root: Path) -> int:
        rows = count_jsonl_rows(root / DIALOGUE_REL)
        return sum(1 for r in rows
                   if isinstance(r, dict) and (r.get("source") == LEDGER_SELF_STUDY_SOURCE
                                               or r.get("label") == "TAUGHT"))

    def previous_ledger(pin: dict) -> dict:
        promotion = pin.get("promotion")
        ledger = promotion.get("ledger_accounting") if isinstance(promotion, dict) else None
        if not isinstance(ledger, dict):
            return {k: 0 for k in LEDGER_KEYS}
        return {k: (ledger[k] if type(ledger.get(k)) is int and ledger[k] >= 0 else 0)
                for k in LEDGER_KEYS}

    def ledger_growth(previous: dict, current: dict) -> int:
        return sum(current[k] - previous[k] for k in LEDGER_KEYS if k != "R_pin")

    def check_ledger_growth(previous: dict, current: dict) -> None:
        growth = ledger_growth(previous, current)
        if growth <= 0:
            raise PromotePinError(
                "refusing to advance the pin; ledger did not grow "
                f"(dS_lived={current['S_lived'] - previous['S_lived']}, "
                f"dS_taught_lessons={current['S_taught_lessons'] - previous['S_taught_lessons']}, "
                f"dS_taught_self_study={current['S_taught_self_study'] - previous['S_taught_self_study']})"
            )


def count_lived_turns(thread_file: Path) -> int:
    """Live Talk turns: one turn per `Zeref:` line in the live Talk thread.

    The thread is not in the repo; the caller counts it at promote time (the
    box loop counts its local thread file). No hardcoded count, ever.
    """
    if not Path(thread_file).is_file():
        raise ValueError(f"Talk thread file not found: {thread_file}")
    return sum(1 for line in Path(thread_file).read_text(encoding="utf-8").splitlines()
               if line.startswith("Zeref:"))


def count_live_ledger_totals(lived_chain_path: Path, taught_jsonl_path: Path) -> tuple[int, int]:
    """Live-counted (S_lived, S_taught) from the two canonical files.

    lived_chain_path is the Talk thread file (one lived turn per `Zeref:`
    line, the #1044 rule); taught_jsonl_path is dialogue.jsonl (non-empty
    lines, the #1044 rule). Raises FileNotFoundError if either file is
    missing — callers that cannot see the thread file (e.g. a GitHub runner)
    must NOT call this; they read S_lived from the pin's ledger_accounting
    (counted at promote time on the box) and count S_taught live from the
    checkout instead.

    CORRECTION to the pasted draft: it said "non-empty lines for S_lived",
    but the thread file interleaves Cory's lines with Zeref's, so non-empty
    lines would double-count. S_lived is `Zeref:` lines only, per #1044.
    """
    lived_chain_path = Path(lived_chain_path)
    taught_jsonl_path = Path(taught_jsonl_path)
    if not lived_chain_path.is_file():
        raise FileNotFoundError(f"lived chain (Talk thread) not found: {lived_chain_path}")
    if not taught_jsonl_path.is_file():
        raise FileNotFoundError(f"taught file not found: {taught_jsonl_path}")
    s_lived = count_lived_turns(lived_chain_path)
    s_taught = sum(1 for line in taught_jsonl_path.read_text(encoding="utf-8").splitlines()
                   if line.strip())
    return s_lived, s_taught


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_chain_stats(world_chain_path: Path | None) -> tuple[int | None, str | None]:
    """(S_world_ticks, world_chain_tail_sha256) from the sandbox chain, or (None, None)."""
    if world_chain_path is None or not Path(world_chain_path).is_file():
        return None, None
    lines = [ln for ln in Path(world_chain_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    entries = [json.loads(ln) for ln in lines]
    ticks = [e for e in entries if e.get("schema") == "zeref-world-chain-v1" and not e.get("genesis")]
    if not entries:
        return 0, None
    return len(ticks), entries[-1].get("entry_hash")


def sync_browser_manifest_ledger(manifest_path: Path = MANIFEST_PATH, pin_path: Path = PIN_PATH,
                                 root: Path = REPO, world_chain_path: Path | None = None,
                                 lived_turns: int | None = None) -> dict:
    """Write classification + ledger_accounting + ledger_sha256 into the manifest.

    S_lived comes from the pin file's promotion.ledger_accounting (counted from
    the live Talk thread at promote time) unless --lived-turns overrides it
    with a fresh count. S_taught is counted live from dialogue.jsonl in the
    checkout. S_world_ticks / world_chain_tail_sha256 come from the sandbox
    chain when it is supplied, else null (labelled, not invented).
    Preserves every other manifest key; updates provenance pin fields from the
    pin file. Returns the ledger dict.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    pin = json.loads(Path(pin_path).read_text(encoding="utf-8"))
    pin_ledger = (pin.get("promotion") or {}).get("ledger_accounting")
    if lived_turns is not None:
        s_lived = int(lived_turns)
    elif isinstance(pin_ledger, dict) and type(pin_ledger.get("S_lived")) is int:
        s_lived = pin_ledger["S_lived"]
    else:
        s_lived = None  # legacy pin: unknown, not zero
    s_world_ticks, tail_sha = _read_chain_stats(world_chain_path)
    ledger = {
        "S_lived": s_lived,
        "S_taught_lessons": count_taught_lessons(root),
        "S_taught_self_study": count_taught_self_study(root),
        "R_pin": int(pin["training_steps"]),
        "S_world_ticks": s_world_ticks,
        "world_chain_tail_sha256": tail_sha,
    }
    manifest["classification"] = CLASSIFICATION
    manifest["ledger_accounting"] = ledger
    manifest["ledger_sha256"] = sha256_hex(canonical_json(ledger))
    prov = manifest.setdefault("provenance", {})
    prov["training_steps"] = int(pin["training_steps"])
    prov["checkpoint_sha256"] = pin["checkpoint_sha256"]
    prov["release_tag"] = pin["promotion"]["release_tag"]
    prov["release_asset_sha256"] = pin["promotion"]["release_asset_sha256"]
    Path(manifest_path).write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return ledger


def _unwrap_ledger_file(path: Path) -> dict:
    """A ledger file is either the bare ledger dict or a wrapper with a
    'ledger_accounting' key (the release workflow's ledger.json shape)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("ledger_accounting"), dict):
        return data["ledger_accounting"]
    if isinstance(data, dict):
        return data
    raise ValueError(f"{path} holds no ledger dict")


def enforce_pin_advance_guard(previous: dict, current: dict) -> int:
    """Raise PIN_ADVANCE_BLOCKED unless lived+taught turns grew. Returns growth.

    previous/current are ledger_accounting dicts ({S_lived, S_taught_lessons,
    S_taught_self_study, R_pin}); a missing or null S_lived (legacy pin) counts
    as 0 in the delta, and the caller must label it legacy.
    """
    prev = {k: (previous.get(k) if type(previous.get(k)) is int else 0) for k in LEDGER_KEYS}
    cur = {k: (current.get(k) if type(current.get(k)) is int else 0) for k in LEDGER_KEYS}
    growth = ledger_growth(prev, cur)
    if growth <= 0:
        raise PinAdvanceBlocked(
            "PIN_ADVANCE_BLOCKED: ledger did not grow "
            f"(dS_lived={cur['S_lived'] - prev['S_lived']}, "
            f"dS_taught_lessons={cur['S_taught_lessons'] - prev['S_taught_lessons']}, "
            f"dS_taught_self_study={cur['S_taught_self_study'] - prev['S_taught_self_study']})"
        )
    return growth


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sync-manifest", help="write the ledger into the browser manifest")
    s.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    s.add_argument("--pin", type=Path, default=PIN_PATH)
    s.add_argument("--root", type=Path, default=REPO)
    s.add_argument("--world-chain", type=Path, default=None)
    s.add_argument("--lived-turns", type=int, default=None)
    g = sub.add_parser("guard-pin", help="refuse a pin advance unless the ledger grew")
    g.add_argument("--previous-ledger", type=Path, required=True)
    g.add_argument("--current-ledger", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.command == "sync-manifest":
        ledger = sync_browser_manifest_ledger(args.manifest, args.pin, args.root,
                                              args.world_chain, args.lived_turns)
        print("manifest ledger:", json.dumps(ledger, sort_keys=True))
        return 0
    prev = _unwrap_ledger_file(args.previous_ledger)
    cur = _unwrap_ledger_file(args.current_ledger)
    try:
        growth = enforce_pin_advance_guard(prev, cur)
    except PinAdvanceBlocked as exc:
        print(str(exc))
        return 2
    print(f"ledger growth: +{growth} (advance allowed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
