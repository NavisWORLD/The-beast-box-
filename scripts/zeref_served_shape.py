#!/usr/bin/env python3
"""Rebuild a seeded share of authored chat rows into the served mouth shape.

The trainer's plain row is `user: Q\\nassistant: A`. The mouth sends a system
preface, then earlier turns, then the question (models/rawrphos/inference/server.py).
About 15% of existing authored rows are rebuilt in that shape. The preface uses
only recorded pin, diary, and 12D engine values. Loss stays on the final answer.
Heldout, gate, and eval prompts never enter the source or the prior-turn pool.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

FRACTION = 0.15
SELECTION_SEED = "zeref-served-shape-v1"
TOKEN_CAP = 256
PIN_PATH = Path("apps/beastbox-cloud/lib/rawrphos-public-pin.json")
DIARY_PATH = Path("evidence/rawrphos-closed-loop-002/zeref-diary-ticks-1-18.jsonl")
DYN12_PATH = Path("apps/beastbox-cloud/public/spark/zeref-live-20261010/unsigned-session.json")
LINEAGE_PATH = Path("apps/beastbox-cloud/public/spark/zeref-live-20261010/qbeast.json")
GATE_PATH = Path(__file__).resolve().parent / "zeref_gate_sets_v2.json"


def _hash_int(text):
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def row_selected(row, seed=SELECTION_SEED, fraction=FRACTION):
    """Seeded hash threshold. Same row and seed always give the same choice."""
    key = "%s\n%s\n%s" % (seed, row.get("source") or "", row.get("user") or "")
    return (_hash_int(key) / float(2**64)) < fraction


def prior_turn_count(row, seed=SELECTION_SEED):
    key = "%s\nprior\n%s\n%s" % (seed, row.get("source") or "", row.get("user") or "")
    return 1 + (_hash_int(key) % 3)


def render_prompt(messages):
    """Same join the inference server uses, ending on the assistant cue."""
    if not messages or messages[-1].get("role") != "user":
        raise ValueError("served prompt must end on the target question")
    return "\n".join("%s: %s" % (m["role"], m["content"]) for m in messages) + "\nassistant:"


def diary_event_line(entry):
    """Same facts as composeContinuityPreface's diaryEventLine. No thought text."""
    if not isinstance(entry, dict) or type(entry.get("tick")) is not int:
        return None
    growth = entry.get("growth_source") if isinstance(entry.get("growth_source"), dict) else {}
    kind = growth.get("kind") or "deterministic step"
    simulated = " (simulated)" if growth.get("simulated") is True else ""
    learning = entry.get("learning") if isinstance(entry.get("learning"), dict) else {}
    cells = learning.get("new_cells")
    cells_part = ", learned %s new cells" % cells if type(cells) in (int, float) else ""
    return "tick %s: grew by %s%s%s" % (entry["tick"], kind, simulated, cells_part)


def continuity_preface(pin_step, diary_entries):
    """The continuity field composeContinuityPreface writes, without invented turns."""
    if type(pin_step) is not int:
        raise ValueError("pin step must be the recorded integer")
    head = ["You are Zeref, a small cosmic cat-dragon companion. Your mind is RAWRPHOS, step %s." % pin_step]
    events_line = None
    if diary_entries:
        last = diary_entries[-1]
        if type(last.get("tick")) is int:
            stage = last.get("stage_name") or last.get("stage") or "?"
            xp = 0 if last.get("xp") is None else last.get("xp")
            bond = 0 if last.get("bond") is None else last.get("bond")
            head.append("Your recorded life: stage %s, XP %s, bond %s, diary tick %s." % (stage, xp, bond, last["tick"]))
            events = [diary_event_line(entry) for entry in diary_entries[-3:]]
            events = [line for line in events if line]
            if events:
                events_line = "Recent lived events: %s." % "; ".join(events)
    tail = ["Reply as yourself in one or two short sentences. If you do not know something, say so."]
    return "\n".join(head + ([events_line] if events_line else []) + tail)


def _unavailable(reason):
    from beastbox.hashutil import canonical_json
    return canonical_json({
        "schema": "lived-state-descriptor-v1",
        "status": "unavailable",
        "reason": reason,
        "changes_model_tensors": False,
    })


def descriptor_from_recorded(state12, sequence):
    """The mouth's project_descriptor, or its unavailable record when the 12D is absent."""
    if (
        not isinstance(state12, list) or len(state12) != 12
        or any(type(item) not in (int, float) or isinstance(item, bool) for item in state12)
        or type(sequence) is not int
    ):
        return _unavailable("missing")
    from beastbox.hashutil import sha256_obj
    from beastbox.lived_events import BASIS, CANONICAL_SUBJECT, blank_channels
    from beastbox.lived_prompt import project_descriptor
    state = [float(item) for item in state12]
    text = project_descriptor({
        "subject_id": CANONICAL_SUBJECT,
        "scope": "owner",
        "basis": BASIS,
        "sequence": sequence,
        "state12": state,
        "state_sha256": sha256_obj(state),
        "channels": blank_channels(),
        "face": None,
        "feelings": None,
    })
    return text if text else _unavailable("rejected")


def load_recorded(root=None):
    """Pin step, diary lines, and the recorded engine dyn12. Missing pieces stay missing."""
    root = Path(root) if root is not None else Path(".")
    pin = json.loads((root / PIN_PATH).read_text())
    pin_step = pin.get("training_steps")
    if type(pin_step) is not int:
        raise ValueError("recorded pin training_steps is missing")
    diary = []
    diary_path = root / DIARY_PATH
    if diary_path.is_file():
        diary = [json.loads(line) for line in diary_path.read_text().splitlines() if line.strip()]
    state12 = None
    dyn_path = root / DYN12_PATH
    if dyn_path.is_file():
        engine = json.loads(dyn_path.read_text())["beast"]["genome"]["engine"]
        state12 = engine.get("dyn12")
    sequence = None
    lineage = root / LINEAGE_PATH
    if lineage.is_file():
        events = json.loads(lineage.read_text()).get("events") or []
        if events and type(events[0].get("generation")) is int:
            sequence = events[0]["generation"]
    return {"pin_step": pin_step, "diary": diary, "state12": state12, "sequence": sequence}


def load_forbidden_texts(root=None, extra=()):
    """Eval, gate, and heldout prompts. Comparison is stripped lowercase."""
    root = Path(root) if root is not None else Path(".")
    banned = set()
    for item in extra:
        if isinstance(item, str) and item.strip():
            banned.add(item.strip().lower())
    gate = root / GATE_PATH
    def walk(value):
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and value.strip():
            banned.add(value.strip().lower())
    if gate.is_file():
        walk(json.loads(gate.read_text()))
    evidence = root / "evidence"
    if evidence.is_dir():
        for path in sorted(evidence.glob("*/heldout*.jsonl")):
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for key in ("user", "prompt", "question"):
                    if isinstance(row.get(key), str) and row[key].strip():
                        banned.add(row[key].strip().lower())
    return banned


def _norm(text):
    return (text or "").strip().lower()


def _earlier_priors(rows, indexes, target_index, forbidden, count):
    found = []
    for index in indexes:
        if index >= target_index:
            break
        row = rows[index]
        user = row.get("user") or ""
        assistant = row.get("assistant") or ""
        if not user.strip() or not assistant.strip():
            continue
        if _norm(user) in forbidden or _norm(user) == _norm(rows[target_index].get("user")):
            continue
        found.append((user, assistant))
    if count < 1 or not found:
        return []
    return found[-count:]


def _token_count(messages, answer, encode, limit):
    prompt = render_prompt(messages)
    front = encode(prompt, add_bos=True)
    tail = encode(" " + answer, add_eos=True)
    return len(front) + len(tail), front, tail


def _is_descriptor(message):
    content = message.get("content") or ""
    return message.get("role") == "system" and "lived-state-descriptor-v1" in content


def shrink_messages(messages, answer, encode, limit=TOKEN_CAP):
    """Drop oldest prior turns first, then preface fields, until the row fits."""
    systems = []
    index = 0
    while index < len(messages) - 1 and messages[index].get("role") == "system":
        systems.append(dict(messages[index]))
        index += 1
    priors = []
    while index < len(messages) - 1:
        message = messages[index]
        nxt = messages[index + 1] if index + 1 < len(messages) - 1 else None
        if message.get("role") == "user" and nxt and nxt.get("role") == "assistant":
            priors.append((message["content"], nxt["content"]))
            index += 2
            continue
        index += 1
    target = messages[-1]["content"]

    def build(system_messages, prior_pairs):
        built = [dict(message) for message in system_messages]
        for user, assistant in prior_pairs:
            built.append({"role": "user", "content": user})
            built.append({"role": "assistant", "content": assistant})
        built.append({"role": "user", "content": target})
        return built

    def fits(system_messages, prior_pairs):
        count, _front, _tail = _token_count(build(system_messages, prior_pairs), answer, encode, limit)
        return count <= limit

    while priors and not fits(systems, priors):
        priors.pop(0)
    while len(systems) > 1 and not fits(systems, priors):
        other = next((i for i, message in enumerate(systems) if not _is_descriptor(message)), None)
        systems.pop(other if other is not None else 0)
    while systems and not fits(systems, priors):
        systems.pop(0)
    built = build(systems, priors)
    if not fits(systems, priors):
        return None
    if not any(message.get("role") == "system" and message.get("content") for message in built):
        return None
    return built


def answer_example(encode, messages, answer, limit=TOKEN_CAP):
    """Tokens for one served row. The target supervises the final answer only."""
    count, front, tail = _token_count(messages, answer, encode, limit)
    if count > limit:
        return None
    return {
        "input": (front + tail)[:-1],
        "target": [-100] * (len(front) - 1) + tail,
        "messages": messages,
    }


def encode_chat_row(encode, row, limit=TOKEN_CAP):
    """Served row when it still fits; otherwise the original single-turn row."""
    answer = row.get("assistant") or ""
    messages = row.get("messages") if row.get("served_shape") is True else None
    if isinstance(messages, list) and messages:
        fitted = shrink_messages(messages, answer, encode, limit)
        if fitted is not None:
            example = answer_example(encode, fitted, answer, limit)
            if example is not None:
                example["served_shape"] = True
                example["source"] = row.get("source", "chat")
                return example
    front = encode("user: %s\nassistant:" % row.get("user"), add_bos=True)
    tail = encode(" " + answer, add_eos=True)
    if len(front) + len(tail) > limit:
        return None
    return {
        "input": (front + tail)[:-1],
        "target": [-100] * (len(front) - 1) + tail,
        "served_shape": False,
        "source": row.get("source", "chat"),
    }


_DESCRIPTOR_FIELD_DROPS = ("channels", "face", "feelings", "classical_software")
_DESCRIPTOR_CONSTANT_DROPS = ("changes_model_tensors",)


def _fits(messages, answer, encode, limit):
    count, _front, _tail = _token_count(messages, answer, encode, limit)
    return count <= limit


def build_messages(row, priors, recorded, encode, limit=TOKEN_CAP):
    """Mouth-format messages that fit the token cap.

    Extra prior turns drop first. Optional preface fields drop next: the
    recent-events line, absent descriptor fields, the reply tail, and the life
    line. The last prior turn drops before the recorded state12. The constant
    `changes_model_tensors` flag drops before `state12` itself, and the identity
    line drops last.
    """
    from beastbox.hashutil import canonical_json
    exact = descriptor_from_recorded(recorded.get("state12"), recorded.get("sequence"))
    parsed = json.loads(exact)
    diary = list(recorded.get("diary") or [])
    pin_step = recorded["pin_step"]
    head = "You are Zeref, a small cosmic cat-dragon companion. Your mind is RAWRPHOS, step %s." % pin_step
    life = ""
    events = ""
    if diary and type(diary[-1].get("tick")) is int:
        last = diary[-1]
        stage = last.get("stage_name") or last.get("stage") or "?"
        xp = 0 if last.get("xp") is None else last.get("xp")
        bond = 0 if last.get("bond") is None else last.get("bond")
        life = "Your recorded life: stage %s, XP %s, bond %s, diary tick %s." % (stage, xp, bond, last["tick"])
        event_lines = [diary_event_line(entry) for entry in diary[-3:]]
        event_lines = [line for line in event_lines if line]
        if event_lines:
            events = "Recent lived events: %s." % "; ".join(event_lines)
    tail = "Reply as yourself in one or two short sentences. If you do not know something, say so."
    prior_pairs = list(priors)
    dropped = []
    use_events, use_tail, use_life, use_head, use_desc = True, True, True, True, True

    def descriptor_text():
        if not use_desc:
            return ""
        if not dropped:
            return exact
        body = {key: value for key, value in parsed.items() if key not in dropped}
        return canonical_json(body)

    def continuity_text():
        parts = []
        if use_head:
            parts.append(head)
        if use_life and life:
            parts.append(life)
        if use_events and events:
            parts.append(events)
        if use_tail:
            parts.append(tail)
        return "\n".join(parts)

    def assemble():
        built = []
        descriptor = descriptor_text()
        continuity = continuity_text()
        if descriptor:
            built.append({"role": "system", "content": descriptor})
        if continuity:
            built.append({"role": "system", "content": continuity})
        for user, assistant in prior_pairs:
            built.append({"role": "user", "content": user})
            built.append({"role": "assistant", "content": assistant})
        built.append({"role": "user", "content": row["user"]})
        return built

    def drop_preface_field():
        nonlocal use_events, use_tail, use_life
        if use_events and events:
            use_events = False
            return True
        for key in _DESCRIPTOR_FIELD_DROPS:
            if use_desc and key in parsed and key not in dropped:
                dropped.append(key)
                return True
        if use_tail:
            use_tail = False
            return True
        if use_life and life:
            use_life = False
            return True
        return False

    def drop_identity_field():
        nonlocal use_head, use_desc
        for key in _DESCRIPTOR_CONSTANT_DROPS:
            if use_desc and key in parsed and key not in dropped:
                dropped.append(key)
                return True
        if use_desc:
            use_desc = False
            return True
        if use_head:
            use_head = False
            return True
        return False

    # Extra prior turns go before optional preface fields. The last prior turn
    # goes before the recorded state12.
    while len(prior_pairs) > 1 and not _fits(assemble(), row["assistant"], encode, limit):
        prior_pairs.pop(0)
    while not _fits(assemble(), row["assistant"], encode, limit) and drop_preface_field():
        pass
    while prior_pairs and not _fits(assemble(), row["assistant"], encode, limit):
        prior_pairs.pop(0)
    while not _fits(assemble(), row["assistant"], encode, limit) and drop_identity_field():
        pass
    messages = assemble()
    if not _fits(messages, row["assistant"], encode, limit):
        return None
    if not any(message.get("role") == "system" and message.get("content") for message in messages):
        return None
    return messages


def apply_served_shape(rows, forbidden, recorded, encode, seed=SELECTION_SEED, fraction=FRACTION, limit=TOKEN_CAP):
    """Replace about `fraction` of eligible rows in place. Returns the manifest field."""
    by_source = {}
    for index, row in enumerate(rows):
        by_source.setdefault(row.get("source") or "", []).append(index)
    kept = 0
    for index, row in enumerate(rows):
        user = row.get("user") or ""
        assistant = row.get("assistant") or ""
        if row.get("mode") not in (None, "chat"):
            continue
        if not user.strip() or not assistant.strip() or _norm(user) in forbidden:
            continue
        if not row_selected(row, seed, fraction):
            continue
        count = prior_turn_count(row, seed)
        priors = _earlier_priors(rows, by_source.get(row.get("source") or "", []), index, forbidden, count)
        if not priors:
            continue
        messages = build_messages(row, priors, recorded, encode, limit)
        if messages is None:
            continue
        if any(_norm(message.get("content")) in forbidden and message.get("role") == "user" for message in messages):
            continue
        updated = dict(row)
        updated["served_shape"] = True
        updated["messages"] = messages
        rows[index] = updated
        kept += 1
    return {
        "fraction": fraction,
        "selection_seed": seed,
        "rows": kept,
        "token_cap": limit,
        "loss": "final assistant answer only",
    }


def load_training_encoder():
    """Checkpoint tokenizer when the round has one; otherwise one id per byte."""
    import sys
    models = Path(__file__).resolve().parents[1] / "models"
    if models.is_dir() and str(models) not in sys.path:
        sys.path.insert(0, str(models))
    try:
        from tokenizers import Tokenizer
        from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
    except Exception:
        return _byte_encode
    candidates = []
    parent = os.environ.get("BEAST_006_PARENT_PATH")
    if parent:
        candidates.append(Path(parent))
    candidates.append(Path("site/weights"))
    for directory in candidates:
        path = directory / "tokenizer.json"
        if not path.is_file():
            continue
        try:
            return RawrphosTokenizer(Tokenizer.from_file(str(path))).encode
        except Exception:
            continue
    return _byte_encode


def _byte_encode(text, add_bos=False, add_eos=False):
    ids = list(text.encode("utf-8"))
    if add_bos:
        ids = [1] + ids
    if add_eos:
        ids = ids + [2]
    return ids


def probe_rows(rows, limit=8):
    """A small deterministic slice for the report-only NLL probe."""
    served = [row for row in rows if row.get("served_shape") is True and isinstance(row.get("messages"), list)]
    served.sort(key=lambda row: hashlib.sha256(("%s\n%s" % (row.get("source"), row.get("user"))).encode()).hexdigest())
    return served[:limit]
