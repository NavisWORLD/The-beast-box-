"""Graduation tests: seed-graph shape + the idempotent heldout-screened pipeline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.zeref_world_graduate import graduate_world_chain
from world.graduation_gate import normalize_prompt, prompt_hash

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "world" / "seed_world_001.json"

LANDING_KEYS = {"user", "assistant", "expect_regex", "good_answer_note", "source",
                "teacher_role", "author", "subject", "topic", "split"}


def test_seed_world_graph_is_strongly_connected_and_symmetric():
    """12 nodes, anchors present, symmetric edges, single connected component,
    no dead ends, fields in [0, 1]."""
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    nodes = {n["node_id"]: n for n in seed["nodes"]}
    assert len(nodes) == 12
    for anchor in ("fort", "river", "island"):
        assert anchor in nodes, f"anchor {anchor} missing"
    for node_id, node in nodes.items():
        assert node["adjacent_ids"], f"{node_id} is a dead end"
        assert len(node["adjacent_ids"]) >= 2, f"{node_id} has degree < 2"
        for target in node["adjacent_ids"]:
            assert node_id in nodes[target]["adjacent_ids"], \
                f"edge {node_id} -> {target} is not symmetric"
        for ch, v in node["fields"].items():
            assert 0.0 <= v <= 1.0, f"{node_id}.{ch} out of range"
        for e in node["entities"]:
            assert {"entity_id", "kind", "state", "stones", "inspected_count"} <= set(e)
    # Single connected component (BFS from the Fort reaches all 12).
    seen = set()
    stack = ["fort"]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(nodes[cur]["adjacent_ids"])
    assert seen == set(nodes), f"disconnected nodes: {set(nodes) - seen}"


def _chain_entry(tick, kind, text, entry_hash):
    return {"schema": "zeref-world-chain-v1", "tick": tick, "entry_hash": entry_hash,
            "prev_hash": "0" * 64, "pin_step": 47664, "node_before": "fort",
            "node_after": "river", "state12": [0.0] * 12, "rms_12d": 0.1,
            "rms_42d": 0.05, "m42": 1, "dice_offset": 0, "dice_label": "RECORDED",
            "parsed_action": {"kind": kind}, "mouth_reply": text}


def test_graduation_pipeline_is_idempotent_and_screens_heldout(tmp_path):
    """One clean DIARY graduates, one heldout-colliding entry is blocked,
    re-running is a strict no-op."""
    clean_text = "I stood at the river and the bell rang twice in the cold light."
    colliding_text = "What is the capital of France?"
    heldout = {prompt_hash(colliding_text)}
    chain_path = tmp_path / "world_chain.jsonl"
    entries = [
        _chain_entry(1, "DIARY", clean_text, "a" * 64),
        _chain_entry(2, "DIARY", colliding_text, "b" * 64),
        _chain_entry(3, "MOVE", "walking on", "c" * 64),
    ]
    chain_path.write_text("\n".join(json.dumps(e, sort_keys=True) for e in entries) + "\n")
    cursor = tmp_path / "graduated_hashes.json"
    staged = tmp_path / "staged_taught_rows.jsonl"
    prov = tmp_path / "staged_taught_provenance.jsonl"

    first = graduate_world_chain(chain_path, heldout, cursor, staged, prov)
    assert first["graduated"] == 1
    assert first["blocked"] == 1
    assert first["changed"] is True
    rows = [json.loads(ln) for ln in staged.read_text().splitlines()]
    assert len(rows) == 1
    assert set(rows[0].keys()) == LANDING_KEYS  # exactly the 10 landing keys
    assert rows[0]["source"] == "zeref-world-sandbox"  # honest provenance, not lessons-006
    assert clean_text in rows[0]["assistant"]
    prov_rows = [json.loads(ln) for ln in prov.read_text().splitlines()]
    assert len(prov_rows) == 1
    assert prov_rows[0]["world_entry_hash"] == "a" * 64
    assert prov_rows[0]["dice_label"] == "RECORDED"
    cursor_bytes = cursor.read_bytes()
    staged_bytes = staged.read_bytes()
    prov_bytes = prov.read_bytes()

    second = graduate_world_chain(chain_path, heldout, cursor, staged, prov)
    assert second["graduated"] == 0 and second["blocked"] == 0
    assert second["changed"] is False
    assert cursor.read_bytes() == cursor_bytes
    assert staged.read_bytes() == staged_bytes
    assert prov.read_bytes() == prov_bytes
