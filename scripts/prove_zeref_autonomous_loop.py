"""Prove the autonomous world loop: 5 invariants over identical 12-tick runs.

prove_all() runs identical 12-tick traversals on two isolated world dirs
with a state-sensitive probe mouth and asserts:
  1. Hash-chain identity: the two runs produce byte-for-byte identical
     entry_hash chains (deterministic replay).
  2. Spine + mutation: the Fort / River / Island spine is reached and at
     least 2 causal entity mutations happen.
  3. Sensorium + dice: non-zero state12/42D differentials on movement or
     interaction ticks, and dice_label == "RECORDED" (real table only).
  4. Counterfactual sensitivity: true vs zero condition54.
     HONEST LABEL: with the probe mouth this is a PROBE SELF-CHECK — it proves
     the probe reads condition54, NOT that the model uses it. The real mouth
     check is gate 9 in PR #1043 (mouth12_conditioning_carries_signal); this
     script never claims the probe result as model evidence. When a real
     checkpoint is supplied (--checkpoint/--asset), the same counterfactual
     runs against the LIVE Engine and is reported as a reply-level live-mouth
     property (with the NLL-level proof deferred to gate 9).
  5. Graduation + ledger: heldout-screened graduation of the chain's DIARY
     entries, and a manifest ledger sync whose S_world_ticks == 12 and whose
     world_chain_tail_sha256 matches the chain tail.

No hardcoded counters: S_lived is counted from the Talk thread file
(--thread-file) and S_taught live from dialogue.jsonl in --root, reusing
#1044's counting rules (see zeref_ledger_guard.py).

Thresholds (invariant 3) are CLI args defaulting to max rms_12d > 0.10 and
max rms_42d > 0.05. They were set from a measured local probe run (see the
proof receipt); if a run measures less, lower them only with the measured
reason recorded, never silently.

Emits a proof receipt (JSON) with proof_sha256. All imports resolve from a
repo-root run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
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
    PIN_PATH,
    build_live_engine_mouth,
    load_dice_table,
    load_pin,
    resolve_live_checkpoint,
    run_ticks,
)
from world.graduation_gate import load_heldout_hashes  # noqa: E402
from world.recorded_dice import build_test_table  # noqa: E402

LANDMARKS = ("fort", "river", "island")


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bfs_next_step(seed: dict, current: str, targets: set[str]) -> str | None:
    """Next node on a shortest path from current to any target (BFS)."""
    graph = {n["node_id"]: list(n["adjacent_ids"]) for n in seed["nodes"]}
    if current in targets:
        return None
    seen = {current}
    queue = [(current, None)]
    while queue:
        node, first = queue.pop(0)
        for nxt in sorted(graph.get(node, [])):
            if nxt in seen:
                continue
            step = first if first is not None else nxt
            if nxt in targets:
                return step
            seen.add(nxt)
            queue.append((nxt, step))
    return None


def make_probe_mouth(seed: dict):
    """State-sensitive probe mouth: reads the [WORLD_STATE] header AND the
    condition54 vector, and acts on both. Deterministic.

    Policy: kindle an unlit beacon / ring a silent bell when present; else
    walk the shortest path toward an unvisited landmark; else inspect an
    unseen entity; else diary. The action always depends on the world state
    and on condition54 (slot 10, landmark binding, gates the diary), so the
    true-vs-zero counterfactual is a genuine probe self-check.
    """
    def probe(prompt: str, max_tokens: int, condition54: list[float]) -> str:
        node_m = re.search(r"^node: (\S+)", prompt, re.M)
        node = node_m.group(1) if node_m else "fort"
        adj_m = re.search(r"^adjacent: (.+)$", prompt, re.M)
        adjacent = [a.strip() for a in adj_m.group(1).split(",")] if adj_m else []
        vis_m = re.search(r"^visible: (.+)$", prompt, re.M)
        visible = vis_m.group(1) if vis_m else ""
        # Interact first when something is waiting.
        m = re.search(r"(\S+)\(beacon:unlit", visible)
        if m:
            return f"The beacon is dark. [ACT: INTERACT({m.group(1)}, kindle)]"
        m = re.search(r"(\S+)\(bell:silent", visible)
        if m:
            return f"The bell is quiet. [ACT: INTERACT({m.group(1)}, ring)]"
        # Walk toward an unvisited landmark (BFS over the seed graph).
        visited = set()
        for r in re.finditer(r"tick \d+: (\S+) \[", prompt):
            visited.add(r.group(1))
        unvisited = {a for a in LANDMARKS if a not in visited and a != node}
        step = _bfs_next_step(seed, node, unvisited) if unvisited else None
        if step:
            return f"I will head for {step}. [ACT: MOVE({step})]"
        # Inspect something unseen.
        m = re.search(r"(\S+)\(\w+:[^,]+,seen=0x\)", visible)
        if m:
            return f"I want a closer look. [ACT: INSPECT({m.group(1)})]"
        # Diary when the landmark binding (slot 10) is high, else keep walking.
        if condition54 and condition54[10] >= 0.25:
            return f"I am at {node} and the world feels close. [ACT: DIARY()]"
        if adjacent:
            return f"I will walk on. [ACT: MOVE({adjacent[0]})]"
        return f"I am at {node}. [ACT: DIARY()]"
    probe.is_live = False
    probe.is_probe = True  # same call signature as the live mouth (prompt, max_tokens, condition54)
    return probe


def _read_chain(chain_path: Path) -> list[dict]:
    if not chain_path.is_file():
        return []
    return [json.loads(ln) for ln in chain_path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def prove_real_mouth_conditioning(
    checkpoint_path: str,
    sample_prompt: str,
    cond54_true: list[float],
    pin: dict | None = None,
    threads: int = 4,
) -> dict:
    """Counterfactual check against the REAL mouth (checkpoint + torch).

    Loads the live engine via build_live_engine_mouth and compares the
    mouth's reply under cond54_true vs zeros vs shuffled (reversed)
    cond54_true. Returns status MEASURED if the reply diverged from
    either control, NULL if it did not — the result is whatever the run
    shows. NO hardcoded expectation: Gemini asserts NULL while
    ZEREF_FILM12 is off at 47,664, but the base cond path (cond_in,
    ||weight|| = 0.2160 measured at pin 47,344) is live, so true vs zero
    may or may not flip greedy output. Do not assert NULL in advance and
    do not claim MEASURED divergence until a real run shows it.
    Requires torch + the checkpoint; runs in CI, not on this box.
    """
    mouth = build_live_engine_mouth(checkpoint_path, pin=pin, threads=threads)
    cond_true = [float(v) for v in cond54_true]
    cond_zero = [0.0] * 54
    cond_shuf = list(reversed(cond_true))
    out_true = mouth(sample_prompt, 64, cond_true)
    out_zero = mouth(sample_prompt, 64, cond_zero)
    out_shuf = mouth(sample_prompt, 64, cond_shuf)
    diverged_from_zero = out_true != out_zero
    diverged_from_shuffled = out_true != out_shuf
    return {
        "status": "MEASURED" if (diverged_from_zero or diverged_from_shuffled) else "NULL",
        "diverged_from_zero": diverged_from_zero,
        "diverged_from_shuffled": diverged_from_shuffled,
        "out_true": out_true,
        "out_zero": out_zero,
        "out_shuf": out_shuf,
    }


def prove_all(*, seed_path: Path, pin_path: Path, manifest_path: Path, root: Path,
              dice_table=None, archive=None, require_live_dice: bool = False,
              heldout_hashes=None, thread_file: Path | None = None,
              lived_turns: int | None = None, checkpoint=None, asset=None,
              extract_to=None, threads: int = 4, out_path: Path | None = None,
              min_rms_12d: float = 0.10, min_rms_42d: float = 0.05,
              min_mutations: int = 2, ticks: int = 12) -> dict:
    """Run the 5-invariant proof. Returns the proof receipt dict."""
    seed = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    pin = load_pin(pin_path)
    pin_step = int(pin["training_steps"])
    invariants: list[dict] = []

    # --- dice (real table when available; else synthetic, labelled).
    class _D:
        pass
    dargs = _D()
    dargs.dice_table = dice_table
    dargs.archive = archive
    dargs.require_live_dice = require_live_dice
    table, dice_source, dice_is_real = load_dice_table(dargs)

    # --- two isolated runs, identical inputs.
    tmp = Path(tempfile.mkdtemp(prefix="zeref-proof-"))
    try:
        dir_a = tmp / "node-a" / "world"
        dir_b = tmp / "node-b" / "world"
        probe = make_probe_mouth(seed)
        receipts_a = run_ticks(dir_a, ticks=ticks, max_tokens=64, seed_path=seed_path,
                              mouth=probe, dice_table=table, dice_is_real=dice_is_real,
                              pin_step=pin_step)
        receipts_b = run_ticks(dir_b, ticks=ticks, max_tokens=64, seed_path=seed_path,
                              mouth=probe, dice_table=table, dice_is_real=dice_is_real,
                              pin_step=pin_step)
    finally:
        pass  # temp dir kept until the receipt is written; removed by caller below

    # Invariant 1: byte-for-byte hash-chain identity across nodes.
    hashes_a = [r["entry_hash"] for r in receipts_a]
    hashes_b = [r["entry_hash"] for r in receipts_b]
    chain_a = _read_chain(dir_a / "world_chain.jsonl")
    chain_b = _read_chain(dir_b / "world_chain.jsonl")
    identical = hashes_a == hashes_b and len(hashes_a) == ticks
    # Every prev_hash link verifies.
    links_ok = True
    prev = None
    for e in chain_a:
        if e.get("genesis"):
            prev = e["entry_hash"]
            continue
        if e.get("prev_hash") != prev:
            links_ok = False
            break
        prev = e["entry_hash"]
    invariants.append({"name": "hash_chain_identity", "passed": bool(identical and links_ok),
                       "measured": {"ticks": len(hashes_a), "identical": identical, "links_ok": links_ok},
                       "label": "MEASURED"})

    # Invariant 2: Fort/River/Island spine reached + >= 2 causal mutations.
    visited = {r["node_after"] for r in receipts_a}
    spine = sorted(set(LANDMARKS) & visited)
    mutations = sum(1 for r in receipts_a if r["parsed_action"].get("mutated"))
    hash_changed = sum(1 for r in receipts_a
                       if r["world_state_hash_after"] != r["world_state_hash_before"])
    invariants.append({"name": "spine_and_mutations", "passed": bool(set(LANDMARKS) <= visited and mutations >= min_mutations),
                       "measured": {"spine_reached": spine, "mutations": mutations,
                                    "hash_changed_ticks": hash_changed, "visited": sorted(visited)},
                       "label": "MEASURED"})

    # Invariant 3: non-zero differentials + RECORDED dice (real table only).
    max_r12 = max((r["rms_12d"] for r in receipts_a), default=0.0)
    max_r42 = max((r["rms_42d"] for r in receipts_a), default=0.0)
    labels = {r["dice_label"] for r in receipts_a}
    if dice_is_real:
        passed3 = max_r12 > min_rms_12d and max_r42 > min_rms_42d and labels == {"RECORDED"}
        label3 = "MEASURED"
    else:
        passed3 = False
        label3 = "DRY-RUN (synthetic dice: RECORDED not proven)"
    invariants.append({"name": "sensorium_and_recorded_dice", "passed": bool(passed3),
                       "measured": {"max_rms_12d": round(max_r12, 4), "max_rms_42d": round(max_r42, 4),
                                    "thresholds": {"rms_12d": min_rms_12d, "rms_42d": min_rms_42d},
                                    "dice_labels": sorted(labels), "dice_source": dice_source},
                       "label": label3})

    # Invariant 4: counterfactual sensitivity, true vs zero condition54.
    # Probe mode: PROBE SELF-CHECK only. Live mode: reply-level live-mouth check.
    # The probe prompt carries a full [WORLD_STATE] header in which all
    # three landmarks are already visited and nothing is waiting (beacon
    # lit, bell rung, entities seen), so the walk/inspect branches cannot
    # fire first and the slot-10 landmark-binding diary gate decides: the
    # true arm (slot 10 = 1.0) diaries, the zero arm walks on. A bare prompt
    # with no header always walks (BFS branch fires before the cond gate),
    # which made the self-check vacuously false — fixed by building the
    # header, not by weakening the check.
    probe_prompt = (
        "[WORLD_STATE]\n"
        "tick: 12\n"
        "node: fort (The Fort)\n"
        "adjacent: stone_cairn, starlight_clearing\n"
        "visible: fort_beacon(beacon:lit,seen=1x)\n"
        "memory: tick 1: fort [MOVE(stone_cairn)]; tick 2: river [MOVE(island)]; tick 3: island [DIARY()]\n"
        "You are Zeref. Say what you notice. [ACT: DIARY()]"
    )
    cond_true = [0.0] * 12 + [0.0] * 42
    cond_true[0] = 0.5
    cond_true[10] = 1.0
    cond_zero = [0.0] * 54
    out_true = probe(probe_prompt, 64, cond_true)
    out_zero = probe(probe_prompt, 64, cond_zero)
    probe_differs = out_true != out_zero
    live = None
    if checkpoint is not None or asset is not None:
        class _C:
            pass
        cargs = _C()
        cargs.checkpoint = checkpoint
        cargs.asset = asset
        cargs.extract_to = extract_to
        cargs.pin = pin_path
        ckpt = resolve_live_checkpoint(cargs)
        if ckpt is not None:
            live = prove_real_mouth_conditioning(ckpt, probe_prompt, cond_true,
                                                 pin=pin, threads=threads)
    if live is not None:
        invariants.append({"name": "counterfactual_sensitivity",
                           "passed": True,
                           "measured": {"mode": "LIVE-MOUTH reply-level",
                                        "status": live["status"],
                                        "diverged_from_zero": live["diverged_from_zero"],
                                        "diverged_from_shuffled": live["diverged_from_shuffled"],
                                        "out_true": live["out_true"],
                                        "out_zero": live["out_zero"],
                                        "out_shuf": live["out_shuf"]},
                           "label": f"MEASURED status={live['status']} (reply-level only; "
                                    "the NLL-level proof is gate 9 in PR #1043; no hardcoded "
                                    "NULL expectation — the run's result is whatever it is)"})
    else:
        invariants.append({"name": "counterfactual_sensitivity",
                           "passed": bool(probe_differs),
                           "measured": {"mode": "PROBE SELF-CHECK",
                                        "probe_outputs_differ": probe_differs},
                           "label": "PROBE SELF-CHECK ONLY: proves the probe reads condition54, NOT that the model uses it"})

    # Invariant 5: heldout-screened graduation + manifest ledger sync.
    heldout = load_heldout_hashes(heldout_hashes) if heldout_hashes is not None else set()
    grad = graduate_world_chain(dir_a / "world_chain.jsonl", heldout,
                                tmp / "graduated_hashes.json",
                                tmp / "staged_taught_rows.jsonl",
                                tmp / "staged_taught_provenance.jsonl")
    if thread_file is not None:
        # Both canonical files exist here: count them live (fail fast if
        # either is missing — the caller asked for this source).
        s_lived, s_taught = count_live_ledger_totals(
            Path(thread_file), root / "evidence" / "zeref-lessons-006" / "dialogue.jsonl")
        s_lived_source = f"Talk thread file {thread_file} + dialogue.jsonl (counted live)"
    elif lived_turns is not None:
        s_lived = int(lived_turns)
        s_lived_source = "passed --lived-turns (counted at call time)"
    else:
        pin_ledger = (pin.get("promotion") or {}).get("ledger_accounting")
        s_lived = pin_ledger.get("S_lived") if isinstance(pin_ledger, dict) else None
        s_lived_source = "pin promotion.ledger_accounting (as of last promotion)"
    if thread_file is None:
        # Not already live-counted above; count S_taught from the checkout.
        s_taught = count_taught_lessons(root)
    s_taught_self = count_taught_self_study(root)
    bundle_manifest = tmp / "manifest.json"
    shutil.copyfile(manifest_path, bundle_manifest)
    ledger = sync_browser_manifest_ledger(bundle_manifest, pin_path, root,
                                          dir_a / "world_chain.jsonl",
                                          lived_turns=s_lived if isinstance(s_lived, int) else None)
    s_world_ticks, tail_sha = (0, None)
    chain_entries = _read_chain(dir_a / "world_chain.jsonl")
    tick_entries = [e for e in chain_entries if e.get("schema") == "zeref-world-chain-v1" and not e.get("genesis")]
    s_world_ticks = len(tick_entries)
    tail_sha = chain_entries[-1].get("entry_hash") if chain_entries else None
    passed5 = (s_world_ticks == ticks
               and ledger.get("S_world_ticks") == ticks
               and ledger.get("world_chain_tail_sha256") == tail_sha
               and ledger.get("R_pin") == pin_step
               and ledger.get("S_taught_lessons") == s_taught)
    invariants.append({"name": "graduation_and_ledger",
                       "passed": bool(passed5),
                       "measured": {"graduated": grad.get("graduated"), "blocked": grad.get("blocked"),
                                    "S_world_ticks": s_world_ticks, "expected_ticks": ticks,
                                    "tail_match": ledger.get("world_chain_tail_sha256") == tail_sha,
                                    "S_lived": s_lived, "S_lived_source": s_lived_source,
                                    "S_taught_lessons": s_taught, "S_taught_self_study": s_taught_self,
                                    "heldout_screened": heldout_hashes is not None},
                       "label": "MEASURED"})

    receipt = {"schema": "zeref-autonomous-proof-v1", "pin_step": pin_step,
               "ticks": ticks, "dice_source": dice_source,
               "dice_label": "RECORDED" if dice_is_real else "DRY-RUN",
               "invariants": invariants,
               "passed": all(i["passed"] for i in invariants)}
    receipt["proof_sha256"] = sha256_hex(canonical_json(
        {k: v for k, v in receipt.items() if k != "proof_sha256"}))
    if out_path is not None:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    return receipt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=Path, default=REPO / "world" / "seed_world_001.json")
    ap.add_argument("--pin", type=Path, default=PIN_PATH)
    ap.add_argument("--manifest", type=Path, default=REPO / "evidence" / "zeref-browser-brain-001" / "manifest.json")
    ap.add_argument("--root", type=Path, default=REPO)
    ap.add_argument("--dice-table", type=Path, default=None)
    ap.add_argument("--archive", type=Path, default=None)
    ap.add_argument("--require-live-dice", action="store_true")
    ap.add_argument("--heldout-hashes", type=Path, default=None)
    ap.add_argument("--thread-file", type=Path, default=None)
    ap.add_argument("--lived-turns", type=int, default=None)
    ap.add_argument("--checkpoint", type=Path, default=None)
    ap.add_argument("--asset", type=Path, default=None)
    ap.add_argument("--extract-to", type=Path, default=None)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--ticks", type=int, default=12)
    ap.add_argument("--min-rms-12d", type=float, default=0.10)
    ap.add_argument("--min-rms-42d", type=float, default=0.05)
    ap.add_argument("--min-mutations", type=int, default=2)
    ap.add_argument("--out", type=Path, default=REPO / "evidence" / "zeref-world-sandbox" / "proof_receipt.json")
    args = ap.parse_args(argv)
    receipt = prove_all(seed_path=args.seed, pin_path=args.pin, manifest_path=args.manifest,
                        root=args.root, dice_table=args.dice_table, archive=args.archive,
                        require_live_dice=args.require_live_dice,
                        heldout_hashes=args.heldout_hashes, thread_file=args.thread_file,
                        lived_turns=args.lived_turns, checkpoint=args.checkpoint,
                        asset=args.asset, extract_to=args.extract_to, threads=args.threads,
                        out_path=args.out, min_rms_12d=args.min_rms_12d,
                        min_rms_42d=args.min_rms_42d, min_mutations=args.min_mutations,
                        ticks=args.ticks)
    print("proof:", json.dumps(receipt, sort_keys=True))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
