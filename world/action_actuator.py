"""Finite action actuator and recorded quantum dice tie-breaker (Module C).

Zeref's mouth is a 64-token SPEAK channel. This module gives him a compact,
deterministic action vocabulary alongside it, parsed from a structured
`[ACT: ...]` prefix or resolved by recorded-dice fallback. Every draw uses
the 11,354,112-shot RECORDED table (world.recorded_dice), never live quantum,
never Math.random.

Action vocabulary:
  MOVE(<adjacent_node_id>)     travel along a valid edge; invalid edges refuse
                               safely and fall back to a dice-selected edge.
  INSPECT(<entity_id>)         increment inspected_count on an entity at the
                               current node; surfaces its attributes next tick.
  INTERACT(<entity_id>, <verb>) mutate an entity: kindle / extinguish (beacon),
                               ring (bell), stack_stone (cairn). Produces an
                               immediate causal sensory delta on tick t+1.
  STUDY(<query>)               emit a read-only study request the existing
                               keyless self-study pipeline can consume under
                               its 3600s cooldown and 5,827-hash heldout screen.
  DIARY()                      append a consolidated narrative entry and run one
                               bounded sandbox Hebbian update/decay step.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from world.recorded_dice import QUANTUM_SHOTS_N, draw_52, state12_hex, turn_seed

# Re-exported so scripts can import the shot count from this module.
__all__ = ["QUANTUM_SHOTS_N", "build_world_prompt", "parse_action", "valid_actions",
           "apply_action", "detect_oscillation", "VALID_VERBS"]

VALID_VERBS = {
    "kindle": ("beacon", "unlit", "lit"),
    "extinguish": ("beacon", "lit", "unlit"),
    "ring": ("bell", "silent", "ringing"),
    "stack_stone": ("cairn", None, None),  # stones int + 1, state stays "stacked"
}

ACT_RE = re.compile(
    r"\[ACT:\s*(MOVE|INSPECT|INTERACT|STUDY|DIARY)\s*(?:\(\s*(.*?)\s*\))?\s*\]",
    re.IGNORECASE,
)


def _node(state: dict, node_id: str) -> dict:
    for n in state["nodes"]:
        if n["node_id"] == node_id:
            return n
    raise ValueError(f"unknown node {node_id!r}")


def _entity(node: dict, entity_id: str) -> dict | None:
    for e in node.get("entities", []):
        if e["entity_id"] == entity_id:
            return e
    return None


def build_world_prompt(state: dict, tick: int) -> tuple[str, str]:
    """Return (raw_prompt, effective_prompt).

    raw_prompt is the base frame (who Zeref is, where he is). effective_prompt
    prepends a compact [WORLD_STATE] header: node, adjacent_ids,
    visible_entities, and a 3-slot rolling spatial/motif memory of the last 2
    ticks, so fort + river + island links persist across turns. Both sha256s
    are recorded in the receipt.
    """
    node = _node(state, state["node"])
    mem = state.get("memory", {})
    recent = mem.get("recent", [])[-2:]
    mem_lines = []
    for r in recent:
        mem_lines.append(f"tick {r.get('tick')}: {r.get('node')} [{r.get('action', '?')}]")
    memory_text = "; ".join(mem_lines) if mem_lines else "no earlier ticks"
    entities_text = ", ".join(
        f"{e['entity_id']}({e['kind']}:{e['state']}"
        + (f",stones={e['stones']}" if e["kind"] == "cairn" else "")
        + f",seen={e['inspected_count']}x)"
        for e in node.get("entities", [])
    ) or "none"
    header = (
        "[WORLD_STATE]\n"
        f"tick: {tick}\n"
        f"node: {node['node_id']} ({node['name']})\n"
        f"adjacent: {', '.join(node['adjacent_ids'])}\n"
        f"visible: {entities_text}\n"
        f"memory: {memory_text}\n"
        "You may act with [ACT: MOVE(<node>)] [ACT: INSPECT(<entity>)] "
        "[ACT: INTERACT(<entity>, <verb>)] [ACT: STUDY(<query>)] [ACT: DIARY()] "
        "or just speak.\n"
    )
    raw_prompt = (
        "You are Zeref, a small black cosmic cat-dragon exploring your world. "
        f"You are at {node['name']}. "
        "Say what you notice and what you want to do, in your own words."
    )
    return raw_prompt, header + raw_prompt


def parse_action(reply: str) -> dict | None:
    """Parse the first [ACT: ...] tag from a mouth reply. Malformed text -> None.

    Never raises on malformed input: the dice fallback handles the None case.
    """
    if not isinstance(reply, str):
        return None
    m = ACT_RE.search(reply)
    if not m:
        return None
    kind = m.group(1).upper()
    args = (m.group(2) or "").strip()
    if kind == "MOVE":
        target = args.strip().strip("\"'")
        return {"kind": "MOVE", "node": target} if target else None
    if kind == "INSPECT":
        target = args.strip().strip("\"'")
        return {"kind": "INSPECT", "entity": target} if target else None
    if kind == "INTERACT":
        parts = [p.strip().strip("\"'") for p in args.split(",")]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return None
        return {"kind": "INTERACT", "entity": parts[0], "verb": parts[1].lower()}
    if kind == "STUDY":
        query = args.strip().strip("\"'")
        return {"kind": "STUDY", "query": query} if query else None
    if kind == "DIARY":
        return {"kind": "DIARY"}
    return None


def valid_actions(state: dict) -> list[dict]:
    """All currently valid actions at the current node, in deterministic order."""
    node = _node(state, state["node"])
    out: list[dict] = []
    for target in sorted(node["adjacent_ids"]):
        out.append({"kind": "MOVE", "node": target})
    for e in node.get("entities", []):
        out.append({"kind": "INSPECT", "entity": e["entity_id"]})
    for e in node.get("entities", []):
        for verb, (kind, _from, _to) in sorted(VALID_VERBS.items()):
            if e["kind"] != kind:
                continue
            if verb == "stack_stone":
                out.append({"kind": "INTERACT", "entity": e["entity_id"], "verb": verb})
            elif e["state"] == _from:
                out.append({"kind": "INTERACT", "entity": e["entity_id"], "verb": verb})
    return out


def _is_valid(state: dict, action: dict) -> bool:
    node = _node(state, state["node"])
    kind = action.get("kind")
    if kind == "MOVE":
        return action.get("node") in node["adjacent_ids"]
    if kind == "INSPECT":
        return _entity(node, action.get("entity", "")) is not None
    if kind == "INTERACT":
        e = _entity(node, action.get("entity", ""))
        if e is None:
            return False
        spec = VALID_VERBS.get(action.get("verb", ""))
        if spec is None or e["kind"] != spec[0]:
            return False
        if action["verb"] == "stack_stone":
            return True
        return e["state"] == spec[1]
    if kind == "STUDY":
        return bool((action.get("query") or "").strip())
    if kind == "DIARY":
        return True
    return False


def detect_oscillation(recent_nodes: list[str]) -> bool:
    """True when Zeref has oscillated between the same two nodes for >= 3 ticks.

    Pattern A,B,A (3 ticks) or longer alternating runs. The dice then breaks
    the tie by forcing a different edge.
    """
    if len(recent_nodes) < 3:
        return False
    last = recent_nodes[-4:]
    # Alternating A,B,A,B... over the last 3+ ticks, exactly 2 distinct nodes.
    if len(set(last[-3:])) == 2 and last[-1] == last[-3] and last[-1] != last[-2]:
        return True
    return False


def dice_pick(candidates: list, dice_value: int):
    """Deterministic selection from a candidate list by a 52-bit dice draw."""
    if not candidates:
        raise ValueError("no candidates to pick from")
    return candidates[dice_value % len(candidates)]


def apply_action(state: dict, action: dict | None, *, dice_value: int, tick: int,
                 pending_study_path: Path | None = None,
                 diary_path: Path | None = None) -> dict:
    """Apply an action to a deep-copied world state.

    Returns {"state": new_state, "applied": action_dict, "mutated": bool,
    "dice_intervened": bool, "note": str}. Invalid or absent actions fall back
    to a dice-selected valid action (dice_intervened True). STUDY appends a
    read-only request file; DIARY appends a narrative entry and runs one
    bounded sandbox Hebbian step on the sandbox state.
    """
    import copy

    new = copy.deepcopy(state)
    node = _node(new, new["node"])
    dice_intervened = False
    note = ""

    if action is None or not _is_valid(new, action):
        candidates = valid_actions(new)
        action = dice_pick(candidates, dice_value)
        dice_intervened = True
        note = "mouth emitted no valid [ACT:] tag; dice selected a valid action"

    kind = action["kind"]
    mutated = False
    if kind == "MOVE":
        target = action["node"]
        if target not in node["adjacent_ids"]:
            # Refuse the invalid edge safely: dice-select a valid one.
            action = dice_pick(
                [{"kind": "MOVE", "node": t} for t in sorted(node["adjacent_ids"])], dice_value)
            target = action["node"]
            dice_intervened = True
            note = "invalid edge refused; dice selected a valid edge"
        new["node"] = target
        new.setdefault("memory", {}).setdefault("visited_nodes", [])
        if target not in new["memory"]["visited_nodes"]:
            new["memory"]["visited_nodes"].append(target)
    elif kind == "INSPECT":
        e = _entity(node, action["entity"])
        if e is None:
            action = dice_pick(valid_actions(new), dice_value)
            dice_intervened = True
            note = "unknown entity; dice selected a valid action"
            return apply_action(new, action, dice_value=dice_value, tick=tick,
                                pending_study_path=pending_study_path, diary_path=diary_path)
        e["inspected_count"] = int(e.get("inspected_count", 0)) + 1
        mutated = True
        action = dict(action, inspected_count=e["inspected_count"])
    elif kind == "INTERACT":
        e = _entity(node, action["entity"])
        spec = VALID_VERBS[action["verb"]]
        if action["verb"] == "stack_stone":
            e["stones"] = int(e.get("stones", 0)) + 1
        else:
            e["state"] = spec[2]
        mutated = True
    elif kind == "STUDY":
        if pending_study_path is not None:
            pending_study_path.parent.mkdir(parents=True, exist_ok=True)
            rec = {"tick": tick, "node": new["node"], "query": action["query"],
                   "source": "zeref-world-sandbox",
                   "note": "consume under the self-study 3600s cooldown and 5,827-hash heldout screen; never bypass Loop 3 rate limits"}
            with open(pending_study_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
        new.setdefault("memory", {})["confusion_residual"] = 0.5
    elif kind == "DIARY":
        hebb = new.setdefault("hebbian", [[0.0] * 12 for _ in range(12)])
        s = new.get("last_state12") or [0.0] * 12
        eta, lam = 0.01, 0.001
        for i in range(12):
            for j in range(12):
                hebb[i][j] = min(1.0, max(-1.0, hebb[i][j] + eta * s[i] * s[j] - lam * hebb[i][j]))
        # The narrative entry itself is appended by the runner (run_ticks), which
        # holds the mouth reply text; this branch only runs the Hebbian step, so
        # a DIARY action writes exactly one diary record per tick.

    # Rolling 3-slot memory of the last 2 ticks (spatial/motif links persist).
    mem = new.setdefault("memory", {})
    mem["current_node"] = new["node"]
    mem["adjacent_ids"] = list(_node(new, new["node"])["adjacent_ids"])
    mem.setdefault("recent", []).append({"tick": tick, "node": new["node"], "action": kind})
    mem["recent"] = mem["recent"][-3:]
    mem.setdefault("recent_nodes", []).append(new["node"])
    mem["recent_nodes"] = mem["recent_nodes"][-8:]
    if "confusion_residual" not in mem:
        mem["confusion_residual"] = 0.0
    return {"state": new, "applied": action, "mutated": mutated,
            "dice_intervened": dice_intervened, "note": note}


def compute_dice(table: bytes, prev_chain_hash: str, tick: int, node_id: str,
                 state12: list[float]) -> tuple[int, int, str]:
    """Recorded-dice draw for one world turn -> (dice_value, dice_offset, seed_hex).

    seed = sha256(f"{prev_chain_hash}:{tick}:{node_id}:{state12_hex}").
    """
    seed = turn_seed(prev_chain_hash, tick, node_id, state12_hex(state12))
    value, offset = draw_52(table, seed)
    return value, offset, seed
