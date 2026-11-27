"""Autonomous pulse: one scheduled round of the world loop, end to end.

run_pulse(): world ticks (live mouth + recorded dice) -> heldout-safe
graduation -> manifest ledger sync -> a read-only snapshot bundle in
public/live_telemetry/ (world_state.json, world_chain.jsonl, manifest.json,
pulse_summary.json) that the public page fetches by raw URL from the
zeref/world-sandbox-log branch.

No hardcoded counters anywhere: S_lived is counted from the Talk thread file
(--thread-file) or passed as --lived-turns, else read live from the pin
file's promotion.ledger_accounting and labelled as of the last promotion.
S_taught is counted live from evidence/zeref-lessons-006/dialogue.jsonl in
the checkout, reusing #1044's counting rules (see zeref_ledger_guard.py).

Dry-run discipline (flaw 4 fix): a pulse with no real checkpoint or no real
recorded dice table REFUSES to touch the chain unless --allow-dry-run is
passed, and a dry-run pulse ticks into a TEMPORARY world dir and labels every
receipt DRY-RUN, never RECORDED. Scheduled runs appending synthetic ticks to
the chain are forbidden. The pulse workflow never passes --allow-dry-run and
passes --require-live-dice, so a missing checkpoint or dice table fails the
run loudly instead of silently dry-running.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.zeref_ledger_guard import (  # noqa: E402
    count_lived_turns,
    count_live_ledger_totals,
    count_taught_lessons,
    count_taught_self_study,
    sync_browser_manifest_ledger,
)
from scripts.zeref_world_graduate import graduate_world_chain  # noqa: E402
from scripts.zeref_world_tick import (  # noqa: E402
    build_live_engine_mouth,
    load_dice_table,
    load_pin,
    resolve_live_checkpoint,
    run_ticks,
)
from world.graduation_gate import load_heldout_hashes  # noqa: E402

PIN_PATH = REPO / "apps/beastbox-cloud/lib/rawrphos-public-pin.json"
DEFAULT_WORLD_DIR = REPO / "evidence" / "zeref-world-sandbox"
DEFAULT_SEED = REPO / "world" / "seed_world_001.json"
DEFAULT_BUNDLE_DIR = REPO / "public" / "live_telemetry"


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chain_tail(chain_path: Path) -> tuple[int, str | None]:
    if not chain_path.is_file():
        return 0, None
    lines = [ln for ln in chain_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ticks = [json.loads(ln) for ln in lines if json.loads(ln).get("schema") == "zeref-world-chain-v1"
             and not json.loads(ln).get("genesis")]
    if not lines:
        return 0, None
    return len(ticks), json.loads(lines[-1]).get("entry_hash")


def run_pulse(*, world_dir: Path, bundle_dir: Path, seed_path: Path, pin_path: Path,
              ticks: int = 12, max_tokens: int = 64, threads: int = 4,
              checkpoint=None, asset=None, extract_to=None,
              dice_table=None, archive=None, require_live_dice: bool = True,
              allow_dry_run: bool = False, heldout_hashes=None,
              thread_file: Path | None = None, lived_turns: int | None = None,
              run_id: str = "local") -> dict:
    """Run one autonomous pulse. Returns the pulse summary dict."""
    world_dir = Path(world_dir)
    bundle_dir = Path(bundle_dir)
    pin = load_pin(pin_path)
    pin_step = int(pin["training_steps"])

    # --- dice: real recorded table or refuse (dry-run only into a temp dir).
    class _DiceArgs:
        pass
    dargs = _DiceArgs()
    dargs.dice_table = dice_table
    dargs.archive = archive
    dargs.require_live_dice = require_live_dice
    table, dice_source, dice_is_real = load_dice_table(dargs)
    if not dice_is_real and not allow_dry_run:
        raise ValueError("no real recorded dice table; pass --allow-dry-run for an explicit dry run (temp dir only)")

    # --- mouth: live Engine or refuse (dry-run only into a temp dir).
    class _CkptArgs:
        pass
    cargs = _CkptArgs()
    cargs.checkpoint = checkpoint
    cargs.asset = asset
    cargs.extract_to = extract_to
    cargs.pin = pin_path
    live_checkpoint = resolve_live_checkpoint(cargs)
    if live_checkpoint is not None:
        mouth = build_live_engine_mouth(live_checkpoint, pin, threads=threads)
        mouth_label = "LIVE"
    elif allow_dry_run:
        from scripts.zeref_world_tick import default_dry_run_mouth
        mouth = default_dry_run_mouth
        mouth_label = "DRY-RUN"
    else:
        raise ValueError("no checkpoint resolved; pass --allow-dry-run for an explicit dry run (temp dir only)")

    # --- ticks: live pulses write the real chain; dry runs use a temp dir.
    tick_dir = world_dir
    tmp = None
    if not dice_is_real or mouth_label == "DRY-RUN":
        tmp = Path(tempfile.mkdtemp(prefix="zeref-pulse-dryrun-"))
        tick_dir = tmp / "world"
    receipts = run_ticks(tick_dir, ticks=ticks, max_tokens=max_tokens, seed_path=seed_path,
                        mouth=mouth, dice_table=table, dice_is_real=dice_is_real,
                        pin_step=pin_step,
                        pending_study_path=tick_dir / "pending_study_queries.jsonl",
                        diary_path=tick_dir / "world_diary.jsonl")
    if tmp is not None:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- graduation (heldout-safe) on the real chain only.
    grad = {"graduated": 0, "blocked": 0, "skipped": 0, "staged_rows": 0, "changed": False}
    if dice_is_real and mouth_label == "LIVE":
        heldout = load_heldout_hashes(heldout_hashes) if heldout_hashes is not None else set()
        if heldout_hashes is None:
            raise ValueError("live pulse needs --heldout-hashes for heldout-safe graduation")
        grad = graduate_world_chain(world_dir / "world_chain.jsonl", heldout,
                                    world_dir / "graduated_hashes.json",
                                    world_dir / "staged_taught_rows.jsonl",
                                    world_dir / "staged_taught_provenance.jsonl")

    # --- counts (no hardcoded counters): lived from the thread, taught live.
    # count_live_ledger_totals counts BOTH from the canonical files when the
    # caller can see them; the pin-ledger fallback below is for CI, where
    # the Talk thread file does not exist in the checkout (see the pulse
    # workflow comments). Never call count_live_ledger_totals without the
    # thread file — it raises FileNotFoundError by design.
    if thread_file is not None:
        s_lived, s_taught = count_live_ledger_totals(
            Path(thread_file), REPO / "evidence" / "zeref-lessons-006" / "dialogue.jsonl")
        s_lived_source = f"Talk thread file {thread_file} + dialogue.jsonl (counted live)"
    elif lived_turns is not None:
        s_lived = int(lived_turns)
        s_lived_source = "passed --lived-turns (counted at call time)"
    else:
        pin_ledger = (pin.get("promotion") or {}).get("ledger_accounting")
        s_lived = pin_ledger.get("S_lived") if isinstance(pin_ledger, dict) else None
        s_lived_source = "pin promotion.ledger_accounting (as of last promotion)"
    if thread_file is None:
        s_taught = count_taught_lessons(REPO)
    s_taught_self = count_taught_self_study(REPO)

    # --- manifest ledger sync into the bundle (copy of the landed manifest).
    bundle_dir.mkdir(parents=True, exist_ok=True)
    manifest_src = REPO / "evidence" / "zeref-browser-brain-001" / "manifest.json"
    bundle_manifest = bundle_dir / "manifest.json"
    shutil.copyfile(manifest_src, bundle_manifest)
    ledger = sync_browser_manifest_ledger(bundle_manifest, pin_path, REPO,
                                          world_dir / "world_chain.jsonl",
                                          lived_turns=s_lived if isinstance(s_lived, int) else None)
    # sync already wrote ledger["S_lived"] = s_lived when it is an int; the
    # manifest's ledger_sha256 covers exactly the ledger that was written.

    # --- snapshot bundle (read-only copies for the page).
    for name in ("world_state.json", "world_chain.jsonl"):
        src = world_dir / name
        if src.is_file():
            shutil.copyfile(src, bundle_dir / name)
    s_world_ticks, tail_sha = _chain_tail(world_dir / "world_chain.jsonl")
    summary = {
        "schema": "zeref-pulse-summary-v1",
        "run_id": str(run_id),
        "pin_step": pin_step,
        "mode": "LIVE" if (dice_is_real and mouth_label == "LIVE") else "DRY-RUN",
        "mouth": mouth_label,
        "dice_label": "RECORDED" if dice_is_real else "DRY-RUN",
        "dice_source": dice_source,
        "ticks": len(receipts),
        "nodes_visited": sorted({r["node_after"] for r in receipts}),
        "mutations": sum(1 for r in receipts if r["parsed_action"].get("mutated")),
        "dice_intervened": sum(1 for r in receipts if r["dice_intervened"]),
        "graduated_rows": grad.get("graduated", 0),
        "blocked_rows": grad.get("blocked", 0),
        "S_lived": s_lived,
        "S_lived_source": s_lived_source,
        "S_taught_lessons": s_taught,
        "S_taught_self_study": s_taught_self,
        "S_world_ticks": s_world_ticks,
        "world_chain_tail_sha256": tail_sha,
        "manifest_ledger_sha256": sha256_hex(canonical_json(ledger)),
    }
    (bundle_dir / "pulse_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n",
                                                   encoding="utf-8")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticks", type=int, default=12)
    ap.add_argument("--max-tokens", type=int, default=64)
    ap.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    ap.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE_DIR)
    ap.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--pin", type=Path, default=PIN_PATH)
    ap.add_argument("--checkpoint", type=Path, default=None)
    ap.add_argument("--asset", type=Path, default=None)
    ap.add_argument("--extract-to", type=Path, default=None)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--dice-table", type=Path, default=None)
    ap.add_argument("--archive", type=Path, default=None)
    ap.add_argument("--require-live-dice", action="store_true", default=True)
    ap.add_argument("--allow-dry-run", action="store_true")
    ap.add_argument("--heldout-hashes", type=Path, default=None)
    ap.add_argument("--thread-file", type=Path, default=None)
    ap.add_argument("--lived-turns", type=int, default=None)
    ap.add_argument("--run-id", default="local")
    args = ap.parse_args(argv)
    summary = run_pulse(world_dir=args.world_dir, bundle_dir=args.bundle_dir,
                        seed_path=args.seed, pin_path=args.pin, ticks=args.ticks,
                        max_tokens=args.max_tokens, threads=args.threads,
                        checkpoint=args.checkpoint, asset=args.asset,
                        extract_to=args.extract_to, dice_table=args.dice_table,
                        archive=args.archive, require_live_dice=args.require_live_dice,
                        allow_dry_run=args.allow_dry_run,
                        heldout_hashes=args.heldout_hashes,
                        thread_file=args.thread_file, lived_turns=args.lived_turns,
                        run_id=args.run_id)
    print("pulse:", json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
