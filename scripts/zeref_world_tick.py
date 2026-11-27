"""Sandboxed world-tick runner: N autonomous ticks of Zeref exploring his world.

Each tick: read the world state, compute condition54 (state12 + 42D) from the
world transition, call the pinned mouth (live Engine when a checkpoint
resolves, otherwise a deterministic dry-run mouth), parse the action, arbitrate
with the RECORDED quantum dice, mutate the world, and append a hash-chained
receipt to evidence/zeref-world-sandbox/world_chain.jsonl. The chain is
append-only; the Talk thread, S_lived / S_taught on main, R_pin and the heldout
hashes are never touched here.

Live engine (verified first-hand on main, 2026-11-26): the import is
`from rawrphos.inference.engine import Engine` (scripts/zeref_talk_github.py
L130) and the constructor is
`Engine(checkpoint, max_new_tokens=256, threads=threads,
expected_sha256=pin["checkpoint_sha256"])` (talk script L139-140), with the
checkpoint the extracted accepted-checkpoint dir. The paste's
`from engine import Engine` / `Engine(checkpoint_path, max_new_tokens=64, ...)`
was wrong and is NOT used here. engine.complete(prompt, max_tokens=...,
condition54=...) forwards condition54 into the model (engine.py tokens() L51).

Checkpoint resolution: --checkpoint (extracted dir) first, then
$ZEREF_PIN_CHECKPOINT, then --asset (release tarball, sha-verified against the
pin and extracted like the talk script). If nothing resolves, the runner falls
back to the deterministic dry-run mouth and labels every receipt DRY-RUN
(dice_label "DRY-RUN", never RECORDED). --require-live-dice refuses to run
unless a real dice table is loaded (exactly QUANTUM_SHOTS_N bits): scheduled
runs must never append synthetic ticks to the chain.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from world.action_actuator import (  # noqa: E402
    QUANTUM_SHOTS_N,
    apply_action,
    build_world_prompt,
    compute_dice,
    detect_oscillation,
    dice_pick,
    parse_action,
    valid_actions,
)
from world.recorded_dice import (  # noqa: E402
    DICE_LABEL,
    build_table_from_archive,
    build_test_table,
    draw_52_on_bits,
    load_table_bytes,
    state12_hex,
    turn_seed,
)
from world.sensorium_bridge import ambient_fields, compute_condition54  # noqa: E402

PIN_PATH = REPO / "apps/beastbox-cloud/lib/rawrphos-public-pin.json"
DEFAULT_WORLD_DIR = REPO / "evidence" / "zeref-world-sandbox"
DEFAULT_SEED = REPO / "world" / "seed_world_001.json"
CHAIN_SCHEMA = "zeref-world-chain-v1"


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_pin(path: Path = PIN_PATH) -> dict:
    pin = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("training_steps", "checkpoint_sha256"):
        if key not in pin:
            raise ValueError(f"pin missing {key}")
    return pin


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_live_checkpoint(args) -> Path | None:
    """Resolve an extracted checkpoint dir: --checkpoint, $ZEREF_PIN_CHECKPOINT,
    or --asset (tarball, sha-verified against the pin, extracted). None = dry run."""
    if args.checkpoint:
        p = Path(args.checkpoint)
        if (p / "model.safetensors").is_file():
            return p
        raise ValueError(f"--checkpoint {p} has no model.safetensors")
    env = os.environ.get("ZEREF_PIN_CHECKPOINT")
    if env:
        p = Path(env)
        if (p / "model.safetensors").is_file():
            return p
        raise ValueError(f"$ZEREF_PIN_CHECKPOINT {p} has no model.safetensors")
    if args.asset:
        pin = load_pin(args.pin)
        asset = Path(args.asset)
        got = sha256_file(asset)
        if got != pin["promotion"]["release_asset_sha256"]:
            raise ValueError(f"release asset sha {got} does not match the pin; refusing to run")
        dest = Path(args.extract_to or (REPO / "build" / "zeref-world" / "pin"))
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(asset, "r:gz") as tf:
            tf.extractall(dest, filter="data")
        ckpt = dest / "accepted-checkpoint"
        if not (ckpt / "model.safetensors").is_file():
            raise RuntimeError("release asset has no accepted-checkpoint/model.safetensors")
        return ckpt
    return None


def build_live_engine_mouth(checkpoint_path: Path, pin: dict, threads: int = 4):
    """Live mouth: Engine.complete(prompt, max_tokens, condition54=cond54).

    Real constructor (talk script L139-140): Engine(checkpoint,
    max_new_tokens=256, threads=threads, expected_sha256=pin[checkpoint_sha256]).
    Identity is verified against the pin before any generation.
    """
    from rawrphos.inference.engine import Engine

    engine = Engine(str(checkpoint_path), max_new_tokens=256, threads=threads,
                    expected_sha256=pin["checkpoint_sha256"])
    if engine.metadata["checkpoint_sha256"] != pin["checkpoint_sha256"]:
        raise RuntimeError("identity check failed: loaded checkpoint is not the pin")

    def mouth(prompt: str, max_tokens: int, condition54: list[float]) -> str:
        return engine.complete(prompt, max_tokens=max_tokens, condition54=condition54)

    mouth.is_live = True
    mouth.engine = engine
    return mouth


def default_dry_run_mouth(state: dict, tick: int):
    """Deterministic dry-run mouth (no checkpoint): a fixed policy over the
    visible world, so a dry run is replayable. Used ONLY when no checkpoint
    resolves; every receipt it produces is labelled DRY-RUN."""
    from world.action_actuator import _node

    node = _node(state, state["node"])
    beacons = [e for e in node.get("entities", []) if e["kind"] == "beacon" and e["state"] == "unlit"]
    if beacons:
        return f"I see the {beacons[0]['entity_id']} waiting dark. [ACT: INTERACT({beacons[0]['entity_id']}, kindle)]"
    bells = [e for e in node.get("entities", []) if e["kind"] == "bell" and e["state"] == "silent"]
    if bells and tick % 3 == 0:
        return f"The {bells[0]['entity_id']} is quiet. [ACT: INTERACT({bells[0]['entity_id']}, ring)]"
    if tick % 5 == 0:
        return f"I am at {node['name']} and the world is wide. [ACT: DIARY()]"
    adjacent = sorted(node["adjacent_ids"])
    prev = (state.get("memory", {}).get("recent_nodes") or [None])[-1]
    choices = [t for t in adjacent if t != prev] or adjacent
    return f"I will walk on to {choices[0]}. [ACT: MOVE({choices[0]})]"


def _load_json(path: Path, default):
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _init_world_state(seed_path: Path, pin_step: int) -> dict:
    seed = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    nodes = seed["nodes"]
    return {
        "schema": "zeref-world-state-v1",
        "seed": seed.get("seed", "zeref-world-001"),
        "tick": 0,
        "node": seed.get("start_node", "fort"),
        "nodes": nodes,
        "memory": {"current_node": seed.get("start_node", "fort"),
                   "adjacent_ids": [],
                   "visited_nodes": [seed.get("start_node", "fort")],
                   "recent": [], "recent_nodes": [seed.get("start_node", "fort")],
                   "confusion_residual": 0.0},
        "hebbian": [[0.0] * 12 for _ in range(12)],
        "counters": {"S_world_ticks": 0, "S_world_mutations": 0},
        "pin_step": pin_step,
    }


def _genesis_hash(seed_path: Path, pin_step: int) -> str:
    seed_sha = sha256_file(Path(seed_path))
    return sha256_hex(canonical_json({"schema": "zeref-world-chain-genesis-v1",
                                      "seed_sha256": seed_sha, "pin_step": pin_step}))


def _read_chain_tail(chain_path: Path):
    """Return (prev_hash, entries). Empty chain -> (None, [])."""
    if not chain_path.is_file():
        return None, []
    lines = [ln for ln in chain_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    entries = [json.loads(ln) for ln in lines]
    if not entries:
        return None, []
    return entries[-1]["entry_hash"], entries


def load_dice_table(args) -> tuple[bytes | None, str, bool]:
    """Return (table_bytes_or_None, source_label, is_real).

    --dice-table (sha-verified .bin) first, then --archive (build + verify),
    else a SYNTHETIC test table (is_real False). --require-live-dice raises
    unless a real table loaded.
    """
    if args.dice_table:
        table = load_table_bytes(Path(args.dice_table))
        return table, f"table:{Path(args.dice_table).name}", True
    if args.archive:
        table = build_table_from_archive(Path(args.archive))
        return table, f"archive:{Path(args.archive).name}", True
    if args.require_live_dice:
        raise ValueError("--require-live-dice: no --dice-table or --archive supplied; refusing synthetic dice")
    return build_test_table(), "synthetic-test-table", False


def run_ticks(world_dir: Path, *, ticks: int, max_tokens: int, seed_path: Path,
             mouth, dice_table, dice_is_real: bool, pin_step: int,
             pending_study_path: Path | None = None,
             diary_path: Path | None = None) -> list[dict]:
    """Execute N autonomous ticks, appending hash-chained receipts. Returns them."""
    world_dir = Path(world_dir)
    world_dir.mkdir(parents=True, exist_ok=True)
    state_path = world_dir / "world_state.json"
    chain_path = world_dir / "world_chain.jsonl"
    state = _load_json(state_path, None)
    if state is None:
        state = _init_world_state(seed_path, pin_step)
    prev_hash, _entries = _read_chain_tail(chain_path)
    if prev_hash is None:
        genesis = {"tick": 0, "entry_hash": _genesis_hash(seed_path, pin_step),
                   "schema": CHAIN_SCHEMA, "genesis": True, "pin_step": pin_step}
        with open(chain_path, "a", encoding="utf-8") as f:
            f.write(canonical_json(genesis) + "\n")
        prev_hash = genesis["entry_hash"]

    receipts = []
    prev_fields = None
    prev_prev_fields = None
    dice_label = DICE_LABEL if dice_is_real else "DRY-RUN"
    for n in range(ticks):
        tick = int(state["tick"]) + 1
        node_before = state["node"]
        curr_fields = ambient_fields(
            next(x for x in state["nodes"] if x["node_id"] == node_before), tick)
        if prev_fields is None:
            prev_fields = ambient_fields(
                next(x for x in state["nodes"] if x["node_id"] == node_before), tick - 1)
        last_action = state.get("last_action")
        condition54, state12, rms_12d, rms_42d, m42 = compute_condition54(
            prev_fields, curr_fields, prev_prev_fields, last_action, state["memory"])
        state["last_state12"] = state12
        raw_prompt, effective_prompt = build_world_prompt(state, tick)
        if getattr(mouth, "is_live", False) or getattr(mouth, "is_probe", False):
            reply = mouth(effective_prompt, max_tokens, condition54)
        else:
            reply = mouth(state, tick)
        parsed = parse_action(reply)
        # Recorded-dice draw for this turn (real table) or synthetic fallback.
        if dice_is_real:
            dice_value, dice_offset, _seed = compute_dice(
                dice_table, prev_hash, tick, node_before, state12)
        else:
            dice_value, dice_offset = draw_52_on_bits(
                dice_table, len(dice_table) * 8,
                turn_seed(prev_hash, tick, node_before, state12_hex(state12)))
        # Anti-loop: oscillating between the same two nodes for >= 3 ticks.
        recent_nodes = list(state.get("memory", {}).get("recent_nodes", []))
        dice_intervened = False
        if detect_oscillation(recent_nodes + [node_before]):
            candidates = valid_actions(state)
            move_candidates = [c for c in candidates
                               if c["kind"] == "MOVE" and c["node"] != recent_nodes[-1]]
            if move_candidates:
                parsed = dice_pick(move_candidates, dice_value)
                dice_intervened = True
        result = apply_action(state, parsed, dice_value=dice_value, tick=tick,
                              pending_study_path=pending_study_path, diary_path=diary_path)
        dice_intervened = dice_intervened or result["dice_intervened"]
        new_state = result["state"]
        if result["applied"]["kind"] == "DIARY":
            result["applied"] = dict(result["applied"], text=reply)
            # Re-run the diary append with the mouth text attached.
            if diary_path is not None:
                diary_path.parent.mkdir(parents=True, exist_ok=True)
                rec = {"tick": tick, "node": new_state["node"], "text": reply.strip(),
                       "hebbian_step": {"eta": 0.01, "lambda": 0.001}}
                with open(diary_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, sort_keys=True) + "\n")
        new_state["tick"] = tick
        new_state["last_action"] = dict(result["applied"], mutated=result["mutated"])
        new_state["counters"]["S_world_ticks"] = int(new_state["counters"].get("S_world_ticks", 0)) + 1
        if result["mutated"]:
            new_state["counters"]["S_world_mutations"] = int(new_state["counters"].get("S_world_mutations", 0)) + 1
        world_hash_before = sha256_hex(canonical_json(
            {"nodes": state["nodes"], "node": node_before, "tick": tick - 1}))
        world_hash_after = sha256_hex(canonical_json(
            {"nodes": new_state["nodes"], "node": new_state["node"], "tick": tick}))
        receipt = {
            "schema": CHAIN_SCHEMA,
            "tick": tick,
            "prev_hash": prev_hash,
            "pin_step": pin_step,
            "node_before": node_before,
            "node_after": new_state["node"],
            "world_state_hash_before": world_hash_before,
            "world_state_hash_after": world_hash_after,
            "state12": [round(float(x), 6) for x in state12],
            "condition54": [round(float(x), 6) for x in condition54],
            "rms_12d": round(float(rms_12d), 6),
            "rms_42d": round(float(rms_42d), 6),
            "m42": m42,
            "dice_offset": dice_offset,
            "dice_label": dice_label,
            "raw_prompt_sha256": sha256_hex(raw_prompt),
            "effective_prompt_sha256": sha256_hex(effective_prompt),
            "parsed_action": dict(result["applied"], mutated=result["mutated"]),
            "dice_intervened": bool(dice_intervened),
            "mouth_reply": reply,
            "sandbox_counters": dict(new_state["counters"]),
        }
        receipt["entry_hash"] = sha256_hex(canonical_json(receipt))
        with open(chain_path, "a", encoding="utf-8") as f:
            f.write(canonical_json(receipt) + "\n")
        state_path.write_text(json.dumps(new_state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        prev_prev_fields = prev_fields
        prev_fields = curr_fields
        prev_hash = receipt["entry_hash"]
        state = new_state
        receipts.append(receipt)
    return receipts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticks", type=int, default=10)
    ap.add_argument("--max-tokens", type=int, default=64)
    ap.add_argument("--world-dir", type=Path, default=DEFAULT_WORLD_DIR)
    ap.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--pin", type=Path, default=PIN_PATH)
    ap.add_argument("--checkpoint", type=Path, default=None,
                    help="already-extracted accepted-checkpoint dir")
    ap.add_argument("--asset", type=Path, default=None,
                    help="release tarball (sha-verified against the pin, extracted)")
    ap.add_argument("--extract-to", type=Path, default=None)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--dice-table", type=Path, default=None,
                    help="prebuilt quantum-dice-table.bin (sha-verified)")
    ap.add_argument("--archive", type=Path, default=None,
                    help="public archive JSONL (table built + sha-verified)")
    ap.add_argument("--require-live-dice", action="store_true",
                    help="raise unless a real recorded dice table is loaded")
    args = ap.parse_args(argv)

    pin = load_pin(args.pin)
    pin_step = int(pin["training_steps"])
    dice_table, dice_source, dice_is_real = load_dice_table(args)
    print(f"dice: {dice_source} real={dice_is_real} label={'RECORDED' if dice_is_real else 'DRY-RUN'}")
    checkpoint = resolve_live_checkpoint(args)
    if checkpoint is not None:
        mouth = build_live_engine_mouth(checkpoint, pin, threads=args.threads)
        print(f"mouth: LIVE Engine at pin {pin_step} sha {pin['checkpoint_sha256'][:12]}")
    else:
        mouth = default_dry_run_mouth
        print("mouth: DRY-RUN (no checkpoint resolved; receipts labelled DRY-RUN)")
    receipts = run_ticks(args.world_dir, ticks=args.ticks, max_tokens=args.max_tokens,
                        seed_path=args.seed, mouth=mouth, dice_table=dice_table,
                        dice_is_real=dice_is_real, pin_step=pin_step,
                        pending_study_path=args.world_dir / "pending_study_queries.jsonl",
                        diary_path=args.world_dir / "world_diary.jsonl")
    print(f"ticks: {len(receipts)} nodes: {sorted({r['node_after'] for r in receipts})} "
          f"mutations: {sum(1 for r in receipts if r['parsed_action'].get('mutated'))} "
          f"dice_intervened: {sum(1 for r in receipts if r['dice_intervened'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
