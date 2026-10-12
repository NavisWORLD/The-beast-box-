#!/usr/bin/env python3
"""Zeref experience bridge: canonical zeref-experience/v1 records -> RAWRPHOS
training examples.

Mirrors apps/beastbox-cloud/lib/zeref/experience-record.mjs (same canonical
JSON + SHA-256, so Python verifies hashes written by Node and vice versa).

Rules enforced here (fail closed):
  * every record keeps its ORIGIN; simulations can never claim game progress;
  * quantum / recorded-IBM records are provenance/state inputs, never actions;
  * private scopes (private_interaction, microphone, chat) are excluded unless
    the owner approved that exact scope;
  * records of another QBEAST identity are excluded unless an APPROVED
    identity association exists (none does today: see docs/identity);
  * every training example carries its label kind (computed_reward,
    imitation_target, heuristic_target, human_feedback) so they are never mixed
    up in reports.
"""
from __future__ import annotations
import hashlib, json, math

SCHEMA = "zeref-experience/v1"
ORIGINS = ("live_browser", "original_native_rom", "deterministic_pocket_simulation",
           "azure_rigetti_qvm_simulation", "ibm_recorded_historical")
ACTION_ORIGINS = ("live_browser", "original_native_rom", "deterministic_pocket_simulation")
PRIVATE = {"private_interaction", "microphone", "chat"}
LABEL_KINDS = ("observed_outcome", "computed_reward", "heuristic_target", "imitation_target", "human_feedback")
POCKET_KEYS = ("UP", "DOWN", "LEFT", "RIGHT", "WAIT")
NATIVE_KEYS = ("UP", "DOWN", "LEFT", "RIGHT", "A", "B", "WAIT")


def canonical_json(v) -> str:
    """Byte-compatible with public/spark/genome.mjs canonicalJson for the values we emit."""
    if v is None or isinstance(v, bool):
        return json.dumps(v)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if isinstance(v, float):
            if not math.isfinite(v):
                raise ValueError("nonfinite number")
            if v == int(v) and abs(v) < 1e15:
                return str(int(v))
            s = repr(v)
            if "e" in s:
                raise ValueError("exponent float not allowed in records: " + s)
            return s
        return str(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ",".join(canonical_json(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + canonical_json(v[k]) for k in sorted(v)) + "}"
    raise TypeError("unsupported " + type(v).__name__)


def record_hash(rec: dict) -> str:
    body = {k: v for k, v in rec.items() if k != "hash"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def r4(v):
    return None if v is None else round(float(v) * 1e4) / 1e4


def make_record(*, qbeast_id, origin, observation, action=None, outcome=None, reward=None, memory=None,
                labels=(), source=None, prev=None, episode=None, step=None, decision=None,
                consent=None) -> dict:
    consent = consent or {"scope": "public_game_event", "owner_approved": False}
    if origin not in ORIGINS:
        raise ValueError("unknown origin")
    if origin in ACTION_ORIGINS and (not action or action.get("key") not in NATIVE_KEYS):
        raise ValueError("action origin needs a legal key")
    if origin not in ACTION_ORIGINS and action:
        raise ValueError("state-input origin cannot carry an action")
    for l in labels:
        if l["kind"] not in LABEL_KINDS:
            raise ValueError("unknown label kind")
    rec = {"schema": SCHEMA, "qbeast_id": qbeast_id, "origin": origin,
           "simulated": origin in ("deterministic_pocket_simulation", "azure_rigetti_qvm_simulation"),
           "real_game_progress": False,
           "consent": {"scope": consent["scope"], "owner_approved": bool(consent["owner_approved"])},
           "episode": episode, "step": step, "observation": observation, "decision": decision,
           "action": action, "outcome": outcome,
           "reward": None if reward is None else {"kind": reward["kind"], "value": r4(reward["value"]), "rule": str(reward.get("rule", ""))},
           "memory": memory,
           "labels": [{"kind": l["kind"], "value": l.get("value"), "by": str(l.get("by", ""))} for l in labels],
           "source": {"ref": str((source or {}).get("ref", "")), "sha256": (source or {}).get("sha256")},
           "prev_hash": prev, "hash": ""}
    rec["hash"] = record_hash(rec)
    return rec


def verify_stream(records) -> dict:
    prev = None
    for i, r in enumerate(records):
        if r.get("schema") != SCHEMA:
            return {"ok": False, "reason": "schema", "index": i}
        if r.get("origin") not in ORIGINS:
            return {"ok": False, "reason": "origin", "index": i}
        if r.get("prev_hash") != prev:
            return {"ok": False, "reason": "chain", "index": i}
        if record_hash(r) != r.get("hash"):
            return {"ok": False, "reason": "hash", "index": i}
        if r.get("simulated") and r.get("real_game_progress"):
            return {"ok": False, "reason": "simulation-claims-game-progress", "index": i}
        prev = r["hash"]
    return {"ok": True, "head": prev, "count": len(records)}


def training_eligible(rec, identity, approved_scopes=(), approved_associations=()) -> tuple[bool, str]:
    if rec["origin"] not in ACTION_ORIGINS:
        return False, "state-input origin (quantum/recorded) is provenance, not a training action"
    scope = rec["consent"]["scope"]
    if scope in PRIVATE and not (rec["consent"]["owner_approved"] and scope in approved_scopes):
        return False, "private scope without explicit owner approval"
    if rec["qbeast_id"] != identity and not any(
            a.get("subject") == rec["qbeast_id"] and a.get("object") == identity and a.get("status") == "APPROVED"
            for a in approved_associations):
        return False, "different identity and no APPROVED association"
    return True, "eligible"


# ----------------------------- native ROM adapter -----------------------------

def native_rows_to_records(rows, manifest, qbeast_id):
    """Experiment-006-format native capture rows -> original_native_rom records.
    The action label is the scripted teacher's (imitation_target). No reward:
    the capture explicitly says reward_is_not_native_progress."""
    out, prev = [], None
    for r in rows:
        if r.get("teacher") != "OBSERVATION_CONDITIONED_SCRIPTED_HEURISTIC_NOT_HUMAN_NOT_MODEL":
            raise ValueError("unknown native teacher")
        if r.get("reward_is_not_native_progress") is not True:
            raise ValueError("native row asserts game progress")
        obs = {k: r["before"][k] for k in ("brightness", "contrast", "dominant", "frameChange")}
        after = {k: r["after"][k] for k in ("brightness", "contrast", "dominant", "frameChange")}
        rec = make_record(qbeast_id=qbeast_id, origin="original_native_rom", episode=r["episode"], step=r["step"],
                          observation={"screen": obs, "source": "native-emulator-display"},
                          decision={"policy": "scripted-teacher"}, action={"key": r["action"]},
                          outcome={"kind": "controller_ack", "observed": True, "ack_sha256": r["native_ack_digest"], "screen_after": after},
                          labels=[{"kind": "observed_outcome", "value": "controller_ack", "by": "native-emulator"},
                                  {"kind": "imitation_target", "value": r["action"], "by": "scripted-teacher"}],
                          source={"ref": "native capture " + str(manifest.get("teacher_cycle_offset")), "sha256": manifest.get("jsonl_sha256")},
                          prev=prev)
        out.append(rec)
        prev = rec["hash"]
    return out


# ------------------------------- prompts -------------------------------

def native_prompt(screen) -> str:
    """Byte-identical to Experiment 004/006 prompts so native skill is comparable."""
    o = screen
    return (f"User: Native screen numerical signals: brightness {o['brightness']}/100, "
            f"contrast {o['contrast']}/100, dominant {o['dominant']}, "
            f"frame-change {o['frameChange']}/100. Propose one cautious game key. "
            "Reply exactly ACTION: UP, DOWN, LEFT, RIGHT, A, B, or WAIT. "
            "No object recognition.\nAssistant: ")


def pocket_prompt(obs, memory: bool = True) -> str:
    """Only what the Beast can perceive: grid edges, and (with memory) which
    neighbour cells it has already visited and which it LEARNED are rifts by
    bumping into them. Unlearned rifts are invisible."""
    nb = obs["neighbors"]; groups = {"new": [], "visited": [], "rift": [], "wall": [], "open": []}
    for k in ("UP", "DOWN", "LEFT", "RIGHT"):
        n = nb[k]
        if n["kind"] == "wall":
            groups["wall"].append(k)
        elif not memory:
            groups["open"].append(k)
        elif n["kind"] == "rift-known":
            groups["rift"].append(k)
        elif n["visits"] == 0:
            groups["new"].append(k)
        else:
            groups["visited"].append(k)
    j = lambda g: " ".join(groups[g]) or "none"
    # Instruction first, perception last (nearest the reply).
    if memory:
        body = (f"Wall: {j('wall')}. Learned rift: {j('rift')}. Visited: {j('visited')}. "
                f"Nearest unexplored via: {obs.get('frontier') or 'none'}. New ground: {j('new')}.")
    else:
        body = f"Wall: {j('wall')}. Open: {j('open')}."
    return "User: Pocket step. Reply exactly ACTION: UP, DOWN, LEFT, RIGHT, or WAIT. " + body + "\nAssistant: "


def valid_action(text, keys=NATIVE_KEYS):
    s = (text or "").strip()
    return s[len("ACTION: "):] if s.startswith("ACTION: ") and s[len("ACTION: "):] in keys else None


# ------------------------------- examples -------------------------------

def pocket_examples(records, identity, *, gamma=0.7, horizon=3, threshold=0.5, memory=True,
                    approved_scopes=(), approved_associations=()):
    """Outcome-selected pocket examples. For each step, the n-step discounted
    computed reward G = sum_j gamma^j r_{t+j} (same episode, j<horizon). A step is
    a positive example only if it was not a bump and G > threshold, i.e. the
    action actually led the Beast to new ground soon after. Target = the action
    the Beast really took (label kind computed_reward). Returns (examples, audit)."""
    by_ep, audit = {}, {"seen": 0, "excluded": {}, "positives": 0}
    for r in records:
        audit["seen"] += 1
        ok, why = training_eligible(r, identity, approved_scopes, approved_associations)
        if not ok or r["origin"] == "original_native_rom" or not r.get("reward"):
            key = why if not ok else "not a pocket step"
            audit["excluded"][key] = audit["excluded"].get(key, 0) + 1
            continue
        by_ep.setdefault(r["episode"], []).append(r)
    out = []
    for ep, rs in by_ep.items():
        rs.sort(key=lambda r: r["step"])
        for i, r in enumerate(rs):
            # Bumps never become targets, and neither does WAIT (resting did not
            # move the Beast, so later new ground is not its consequence).
            if r["outcome"]["kind"] in ("rift", "wall", "rested"):
                continue
            g = sum((gamma ** j) * rs[i + j]["reward"]["value"] for j in range(horizon) if i + j < len(rs))
            if g > threshold:
                out.append({"prompt": pocket_prompt(r["observation"], memory), "target": "ACTION: " + r["action"]["key"],
                            "label_kind": "computed_reward", "origin": r["origin"], "record": r["hash"],
                            "behavior_policy": r["decision"]["policy"], "return": round(g, 4)})
    audit["positives"] = len(out)
    return out, audit


def native_examples(records, identity, episodes):
    out = []
    for r in records:
        ok, _ = training_eligible(r, identity)
        if ok and r["origin"] == "original_native_rom" and r["episode"] in episodes:
            out.append({"prompt": native_prompt(r["observation"]["screen"]), "target": "ACTION: " + r["action"]["key"],
                        "label_kind": "imitation_target", "origin": r["origin"], "record": r["hash"]})
    return out
