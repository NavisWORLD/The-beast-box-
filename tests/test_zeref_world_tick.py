"""Acceptance tests for the sandboxed world-tick runner (5 invariants).

All 5 tests run locally against a deterministic stub/probe mouth (no torch on
this box); the real-engine integration is CI-verified (the tick workflow runs
the live Engine on a runner). The dice table used here is a full-size
SYNTHETIC table for the draw-formula checks; the real recorded table is
proven by the archive build (sha match, see the PR report) and by the
workflow's sha-verified load. Nothing in these tests appends to the real
chain: every run uses a temporary world dir.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from scripts.prove_zeref_autonomous_loop import make_probe_mouth
from scripts.zeref_autonomous_pulse import CORY_ONLY_ACTIONS, can_autonomous_run_execute
from scripts.zeref_syndicate_pulse import assemble_story_context_from_taught, decode_state12_b64, encode_state12_b64
from scripts.zeref_world_tick import canonical_json, run_ticks
from world.action_actuator import QUANTUM_SHOTS_N
from world.recorded_dice import (
    TABLE_BITS,
    build_test_table,
    draw_52,
    load_table_bytes,
    state12_hex,
    turn_seed,
)
from world.sensorium_bridge import ambient_fields, build_active_sense_payload, compute_condition54

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "world" / "seed_world_001.json"
PIN_STEP = 47664


def _seed_dict():
    return json.loads(SEED.read_text(encoding="utf-8"))


def _stub_mouth(seed):
    """Probe mouth wrapped to emit malformed text on tick 3 (fallback test)."""
    probe = make_probe_mouth(seed)

    def stub(prompt: str, max_tokens: int, condition54: list[float]) -> str:
        m = re.search(r"^tick: (\d+)", prompt, re.M)
        tick = int(m.group(1)) if m else 0
        if tick == 3:
            return "the wind sings and the stones are humming, no action, just feeling"
        return probe(prompt, max_tokens, condition54)

    stub.is_probe = True
    return stub


def _full_synthetic_table() -> bytes:
    return build_test_table(n_bits=TABLE_BITS)


def test_hash_chain_integrity_and_deterministic_replay(tmp_path):
    """Invariant 1: two identical 5-tick sandboxes produce byte-identical
    entry_hash chains and every prev_hash link verifies."""
    seed = _seed_dict()
    table = _full_synthetic_table()
    mouth_a = _stub_mouth(seed)
    mouth_b = _stub_mouth(seed)
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    ra = run_ticks(dir_a, ticks=5, max_tokens=64, seed_path=SEED, mouth=mouth_a,
                  dice_table=table, dice_is_real=True, pin_step=PIN_STEP)
    rb = run_ticks(dir_b, ticks=5, max_tokens=64, seed_path=SEED, mouth=mouth_b,
                  dice_table=table, dice_is_real=True, pin_step=PIN_STEP)
    assert [r["entry_hash"] for r in ra] == [r["entry_hash"] for r in rb]
    assert len(ra) == 5 == len(rb)
    chain = [json.loads(ln) for ln in (dir_a / "world_chain.jsonl").read_text().splitlines() if ln.strip()]
    prev = None
    for e in chain:
        if e.get("genesis"):
            prev = e["entry_hash"]
            continue
        assert e["prev_hash"] == prev
        assert e["entry_hash"] == hashlib.sha256(
            canonical_json({k: v for k, v in e.items() if k != "entry_hash"}).encode()).hexdigest()
        prev = e["entry_hash"]


def test_sensorium_contract_compliance(tmp_path):
    """Invariant 2: every tick's condition54 is (54,), finite, in [-1, 1],
    with non-zero state12 differentials on movement or interaction."""
    seed = _seed_dict()
    nodes = {n["node_id"]: n for n in seed["nodes"]}
    prev = ambient_fields(nodes["fort"], 0)
    curr = ambient_fields(nodes["river"], 1)
    cond, s12, r12, r42, m42 = compute_condition54(
        prev, curr, None, {"kind": "MOVE", "mutated": False}, {"current_node": "river"})
    assert len(cond) == 54
    assert all(isinstance(x, float) and x == x and abs(x) <= 1.0 for x in cond)
    assert len(s12) == 12 and m42 == 1
    assert r12 > 0  # moving fort -> river changes the fields
    # A full run: receipts carry non-zero differentials on movement ticks.
    table = _full_synthetic_table()
    receipts = run_ticks(tmp_path / "w", ticks=10, max_tokens=64, seed_path=SEED,
                        mouth=_stub_mouth(seed), dice_table=table, dice_is_real=True,
                        pin_step=PIN_STEP)
    moved = [r for r in receipts if r["node_after"] != r["node_before"]]
    assert moved, "the stub never moved"
    assert any(r["rms_12d"] > 0 for r in moved)
    assert all(0.0 <= r["rms_12d"] <= 1.0 and 0.0 <= r["rms_42d"] <= 1.0 for r in receipts)


def test_quantum_dice_invariant(tmp_path):
    """Invariant 3: every draw uses the 11,354,112-shot table (mod (N - 52)),
    records dice_offset, and labels RECORDED (real table path).

    The draw formula is proven here on a full-size table; the table's
    provenance (parity bits from the real archive, pinned sha) is proven by
    the archive build (TABLE_SHA256 match, see the PR report) and by
    load_table_bytes, which refuses a wrong-sha table.
    """
    assert QUANTUM_SHOTS_N == 11354112 == TABLE_BITS
    table = _full_synthetic_table()
    assert len(table) * 8 == TABLE_BITS
    seed = turn_seed("a" * 64, 7, "river", state12_hex([0.1] * 12))
    value, pos = draw_52(table, seed)
    assert 0 <= pos < TABLE_BITS - 52
    assert 0 <= value < 2 ** 52
    # A wrong-sha table is refused by the loader (temp file below).
    bad = bytearray(table)
    bad[0] ^= 0xFF
    bad_path = tmp_path / "bad.bin"
    bad_path.write_bytes(bytes(bad))
    with pytest.raises(ValueError):
        load_table_bytes(bad_path)
    # Tiny parity check: parity bits are exactly the xor of 5 outcome bits.
    from world.recorded_dice import parity_bit
    assert parity_bit("00000") == 0 and parity_bit("00001") == 1 and parity_bit("11111") == 1
    # Receipts from a real-table run carry the offset and the RECORDED label.
    seed_d = _seed_dict()
    receipts = run_ticks(tmp_path / "w2", ticks=3, max_tokens=64, seed_path=SEED,
                        mouth=_stub_mouth(seed_d), dice_table=table, dice_is_real=True,
                        pin_step=PIN_STEP)
    for r in receipts:
        assert r["dice_label"] == "RECORDED"
        assert 0 <= r["dice_offset"] < TABLE_BITS - 52


def test_anti_loop_and_causal_mutation(tmp_path):
    """Invariant 4: over 10 ticks Zeref visits >= 3 distinct nodes, executes
    at least one state-mutating INTERACT that changes the world hash, and
    never crashes on malformed mouth action text (tick 3 is garbage)."""
    seed = _seed_dict()
    table = _full_synthetic_table()
    receipts = run_ticks(tmp_path / "w", ticks=10, max_tokens=64, seed_path=SEED,
                        mouth=_stub_mouth(seed), dice_table=table, dice_is_real=True,
                        pin_step=PIN_STEP)
    assert len(receipts) == 10  # no crash on the malformed tick-3 reply
    assert len({r["node_after"] for r in receipts}) >= 3
    interacts = [r for r in receipts if r["parsed_action"].get("kind") == "INTERACT"
                 and r["parsed_action"].get("mutated")]
    assert interacts, "no state-mutating INTERACT happened"
    assert any(r["world_state_hash_after"] != r["world_state_hash_before"] for r in interacts)
    # The malformed tick fell back to the dice (dice_intervened True).
    assert receipts[2]["dice_intervened"] is True


def test_zero_pollution_isolation(tmp_path):
    """Invariant 5: the runner writes ONLY inside the world dir it is given.
    The pin, the Talk thread, the heldout manifest and the landing destination
    are never touched (verified by git when a checkout is present)."""
    seed = _seed_dict()
    table = _full_synthetic_table()
    pin_before = (REPO / "apps/beastbox-cloud/lib/rawrphos-public-pin.json").read_bytes() \
        if (REPO / "apps/beastbox-cloud/lib/rawrphos-public-pin.json").is_file() else None
    world_dir = tmp_path / "sandbox"
    run_ticks(world_dir, ticks=3, max_tokens=64, seed_path=SEED,
             mouth=_stub_mouth(seed), dice_table=table, dice_is_real=True, pin_step=PIN_STEP)
    # Everything the runner wrote lives under the given world dir.
    assert (world_dir / "world_state.json").is_file()
    assert (world_dir / "world_chain.jsonl").is_file()
    if pin_before is not None:
        assert (REPO / "apps/beastbox-cloud/lib/rawrphos-public-pin.json").read_bytes() == pin_before
    if (REPO / ".git").is_dir():
        protected = re.compile(
            r"^(models/rawrphos/architecture/model\.py"
            r"|apps/beastbox-cloud/lib/rawrphos-public-pin\.json"
            r"|evidence/zeref-lessons-006/dialogue\.jsonl"
            r"|evidence/zeref-self-study/"
            r"|evidence/zeref-qrec-002/"
            r"|scripts/zeref_talk_github\.py"
            r"|\.github/workflows/talk-to-zeref\.yml)$")
        out = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                             capture_output=True, text=True, check=True).stdout
        touched = [ln[3:] for ln in out.splitlines() if ln.strip()]
        bad = [p for p in touched if protected.match(p)]
        assert not bad, f"protected files touched: {bad}"


def test_permalink_state12_round_trip_within_quantization_error():
    """Permalink replay is LOSSY (8-bit quantization): encode then decode
    returns values within +-1/255 of the originals, never exact."""
    original = [0.0, 0.5, -0.5, 1.0, -1.0, 0.123, -0.987, 0.05, -0.05, 0.75, -0.25, 0.333]
    token = encode_state12_b64(original)
    assert len(token) == 16  # 12 bytes -> 16 base64url chars, padding stripped
    decoded = decode_state12_b64(token)
    assert len(decoded) == 12
    for a, b in zip(original, decoded):
        assert abs(a - b) <= 1.0 / 255 + 1e-9
    assert decoded != original  # lossy by construction, never exact


def test_permalink_param_is_c12_q8_on_both_ends(tmp_path):
    """The c12_q8 rename must be consistent on both ends: the generator
    (replay_url) emits c12_q8= + precision=8bit_quantized_12d_only, the
    token in that URL decodes back within quantization error, and the feed
    item carries the precision label. The hydrator
    (public/zeref-door-permalink.js, NavisWORLD repo) reads c12_q8 — the
    param name is asserted here on the generator side and by reading the
    JS source on the hydrator side (JS cannot run in pytest)."""
    from scripts.zeref_syndicate_pulse import PRECISION, replay_url
    original = [0.25, -0.5, 0.0, 0.75, -0.25, 0.1, -0.1, 0.5, -0.75, 0.0, 0.33, -0.33]
    url = replay_url(47664, "fort", original, 12345, "abcdef0123456789")
    assert "c12_q8=" in url
    assert "c12=" not in url.replace("c12_q8=", "")
    assert "precision=8bit_quantized_12d_only" in url
    assert url.startswith("https://navisworld.github.io/NavisWORLD/?")
    token = url.split("c12_q8=")[1].split("&")[0]
    decoded = decode_state12_b64(token)
    for a, b in zip(original, decoded):
        assert abs(a - b) <= 1.0 / 255 + 1e-9
    assert PRECISION == "8bit_quantized_12d_only"
    js = (REPO.parents[1] / "deliverables" / "navisworld-public" / "public" / "zeref-door-permalink.js")
    # The hydrator file lives outside the repo (deliverable, not committed);
    # assert the param name there when the deliverable is present.
    if js.is_file():
        src = js.read_text(encoding="utf-8")
        assert 'params.get("c12_q8")' in src
        assert "m42: 0" in src or "m42 = 0" in src
        assert "8-bit quantized 12D approximation (42D zeroed" in src


def test_active_sense_payload_off_feed_is_none():
    assert build_active_sense_payload("light", "MEASURED", {}) is None
    assert build_active_sense_payload("light", "MEASURED", None) is None


def test_active_sense_payload_modes_and_values():
    payload = build_active_sense_payload("light", "MEASURED", {"brightness": 0.7, "hue": 0.2})
    assert payload == {"source_kind": "light", "mode": "MEASURED",
                       "values": {"brightness": 0.7, "hue": 0.2}}
    assert build_active_sense_payload("sky", "DERIVED", {"light_flux": 0.5})["mode"] == "DERIVED"
    with pytest.raises(ValueError):
        build_active_sense_payload("light", "SIMULATED", {"brightness": 0.5})
    with pytest.raises(ValueError):
        build_active_sense_payload("", "MEASURED", {"brightness": 0.5})


def test_story_context_uses_real_taught_schema():
    rows = [
        {"user": "What is the napping?", "assistant": "The napping is there are multiple different types.",
         "origin": "https://en.wikipedia.org/wiki/Nap", "license": "CC-BY-SA-4.0",
         "source": "zeref-self-study-taught", "label": "TAUGHT", "mode": "chat"},
        {"user": "What is the river?", "assistant": "The river is a natural flowing watercourse.",
         "origin": "https://en.wiktionary.org/wiki/river", "license": "CC-BY-SA-4.0",
         "source": "zeref-self-study-taught", "label": "TAUGHT", "mode": "chat"},
        {"user": "What is the moon?", "assistant": "", "origin": "https://en.wikipedia.org/wiki/Moon",
         "license": "CC-BY-SA-4.0", "source": "zeref-self-study-taught", "label": "TAUGHT", "mode": "chat"},
        {"user": "What is the sun?", "assistant": "The sun is a star.",
         "origin": "", "license": "CC-BY-SA-4.0", "source": "zeref-self-study-taught", "label": "TAUGHT", "mode": "chat"},
    ]
    got = assemble_story_context_from_taught(rows, max_items=3)
    assert [r["user"] for r in got] == ["What is the napping?", "What is the river?"]
    # A selector keyed on a "text" field (as first drafted) would select
    # nothing from real rows, which carry "assistant" instead.
    assert assemble_story_context_from_taught(rows, max_items=1)[0]["user"] == "What is the river?"


def test_ownership_guard():
    assert CORY_ONLY_ACTIONS == {"keys", "money", "name", "merges", "flags",
                                 "gate", "pin", "accounts", "kids", "cases"}
    assert can_autonomous_run_execute("chain") is True
    assert can_autonomous_run_execute("diary") is True
    assert can_autonomous_run_execute("proposals") is True
    for action in ("keys", "money", "name", "merges", "flags", "gate", "pin", "accounts", "kids", "cases"):
        assert can_autonomous_run_execute(action) is False
