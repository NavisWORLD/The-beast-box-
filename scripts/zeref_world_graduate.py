"""Graduate sandboxed world DIARY entries into staged TAUGHT rows.

Reads evidence/zeref-world-sandbox/world_chain.jsonl, tracks a read-only
cursor (graduated_hashes.json) so no tick is processed twice, screens every
candidate through world/graduation_gate.py against the 5,827 heldout hashes,
and emits hash-chained staged rows into staged_taught_rows.jsonl plus a
provenance sidecar (staged_taught_provenance.jsonl).

Row schema: the staged rows use the EXACT 10 keys of the landing destination
(evidence/zeref-lessons-006/dialogue.jsonl on main, verified first-hand):
user, assistant, expect_regex, good_answer_note, source, teacher_role,
author, subject, topic, split. They are key-conformant, but they are NOT
claimed landable as-is under lessons-006: source is "zeref-world-sandbox"
and teacher_role is "SANDBOX_WORLD_DIARY", because these rows are Zeref's own
sandbox diary, not Emeth-authored lessons. The landing pipeline must accept
the new source value, or the reviewer maps it; the rows ship as a reviewed
staging file, never auto-landed. Provenance (world entry hash, tick, node,
rms_12d, dice_label, dice_offset, row_hash) lives in the sidecar, linked by
row_hash, so the landing file stays exactly 10 keys.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from world.graduation_gate import load_heldout_hashes, normalize_prompt, screen

REPO = Path(__file__).resolve().parents[1]


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _distinctive_word(text: str) -> str:
    """First alphanumeric word of length >= 4 for expect_regex; falls back to a
    short distinctive token. Never empty for a non-empty text."""
    for w in re.findall(r"[A-Za-z0-9]+", text or ""):
        if len(w) >= 4:
            return w
        if len(w) >= 3 and w.isalpha():
            return w
    return "world"


def _diary_question(node_name: str) -> str:
    return f"Zeref, what did you see and do at {node_name}?"


def _staged_row(entry: dict, diary_text: str, prev_row_hash: str) -> dict:
    node_name = entry.get("node_after", entry.get("node_before", "the world"))
    user = _diary_question(node_name)
    assistant = diary_text.strip()
    row = {
        "user": user,
        "assistant": assistant,
        "expect_regex": _distinctive_word(assistant),
        "good_answer_note": (
            f"Good: sandbox diary from {node_name} at tick {entry.get('tick')}; "
            "recorded in the world chain, screened against the 5,827 heldout hashes."
        ),
        "source": "zeref-world-sandbox",
        "teacher_role": "SANDBOX_WORLD_DIARY",
        "author": (
            "world-tick sandbox diary; Zeref's own mouth reply in the deterministic "
            "sandbox; no copied text; screened against the 5,827 heldout hashes"
        ),
        "subject": "world_knowledge",
        "topic": "world-sandbox",
        "split": "train",
    }
    return row


def graduate_world_chain(chain_path: Path, heldout, cursor_path: Path,
                         staged_path: Path, provenance_path: Path) -> dict:
    """Graduate unprocessed DIARY entries. Returns a summary dict.

    Idempotent: re-running with the same cursor is a strict no-op (no new
    rows, no cursor change, output files byte-identical). Only entries whose
    parsed_action is DIARY graduate; only clean-screened entries land.
    """
    chain_path = Path(chain_path)
    cursor_path = Path(cursor_path)
    staged_path = Path(staged_path)
    provenance_path = Path(provenance_path)
    heldout_set = load_heldout_hashes(heldout) if not isinstance(heldout, set) else heldout

    cursor = {"graduated": []}
    if cursor_path.is_file():
        cursor = json.loads(cursor_path.read_text(encoding="utf-8"))
    graduated = set(cursor.get("graduated", []))

    entries = []
    if chain_path.is_file():
        entries = [json.loads(ln) for ln in chain_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    # The staged file carries exactly the 10 landing keys; the row hash lives
    # in the provenance sidecar. Recover the previous row hash from there.
    prev_row_hash = "0" * 64
    if provenance_path.is_file():
        prov_lines = [ln for ln in provenance_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if prov_lines:
            prev_row_hash = json.loads(prov_lines[-1]).get("row_hash", prev_row_hash)

    graduated_count = 0
    blocked_count = 0
    skipped_count = 0
    new_rows: list[dict] = []
    new_prov: list[dict] = []
    for entry in entries:
        entry_hash = entry.get("entry_hash")
        if not entry_hash or entry_hash in graduated:
            skipped_count += 1
            continue
        action = entry.get("parsed_action") or {}
        if action.get("kind") != "DIARY":
            # Not a diary entry: mark processed so it is never reconsidered.
            graduated.add(entry_hash)
            skipped_count += 1
            continue
        diary_text = (entry.get("mouth_reply") or "").strip()
        # Strip the [ACT: DIARY()] tag; the narrative is the teachable text.
        diary_text = re.sub(r"\[ACT:[^\]]*\]", "", diary_text).strip()
        clean, reason = screen(diary_text, heldout_set)
        if not clean:
            blocked_count += 1
            graduated.add(entry_hash)  # screened-out entries are still processed
            continue
        row = _staged_row(entry, diary_text, prev_row_hash)
        row_hash = sha256_hex(canonical_json(row) + prev_row_hash)
        new_rows.append(row)
        new_prov.append({
            "row_hash": row_hash,
            "prev_row_hash": prev_row_hash,
            "world_entry_hash": entry_hash,
            "tick": entry.get("tick"),
            "node": entry.get("node_after"),
            "rms_12d": entry.get("rms_12d"),
            "dice_label": entry.get("dice_label"),
            "dice_offset": entry.get("dice_offset"),
            "source": "zeref-world-sandbox",
        })
        prev_row_hash = row_hash
        graduated.add(entry_hash)
        graduated_count += 1

    # Strict no-op when nothing graduated: do not rewrite files (byte-identical).
    if graduated_count == 0 and blocked_count == 0 and not new_rows:
        return {"graduated": 0, "blocked": 0, "skipped": skipped_count,
                "staged_rows": 0, "cursor_size": len(graduated), "changed": False}
    if new_rows:
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        with open(staged_path, "a", encoding="utf-8") as f:
            for row in new_rows:
                f.write(canonical_json(row) + "\n")
        with open(provenance_path, "a", encoding="utf-8") as f:
            for rec in new_prov:
                f.write(canonical_json(rec) + "\n")
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    cursor_path.write_text(json.dumps({"graduated": sorted(graduated)}, indent=1) + "\n", encoding="utf-8")
    return {"graduated": graduated_count, "blocked": blocked_count, "skipped": skipped_count,
            "staged_rows": len(new_rows), "cursor_size": len(graduated), "changed": True}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chain", type=Path, default=REPO / "evidence" / "zeref-world-sandbox" / "world_chain.jsonl")
    ap.add_argument("--heldout-hashes", type=Path, default=None,
                    help="heldout manifest (list or dict with hashes/unique_hashes); required unless --no-heldout-screen")
    ap.add_argument("--no-heldout-screen", action="store_true",
                    help="screen against an EMPTY set (DRY-RUN only; never for a real graduation)")
    ap.add_argument("--cursor", type=Path, default=REPO / "evidence" / "zeref-world-sandbox" / "graduated_hashes.json")
    ap.add_argument("--staged", type=Path, default=REPO / "evidence" / "zeref-world-sandbox" / "staged_taught_rows.jsonl")
    ap.add_argument("--provenance", type=Path, default=REPO / "evidence" / "zeref-world-sandbox" / "staged_taught_provenance.jsonl")
    args = ap.parse_args(argv)
    if args.heldout_hashes is not None:
        heldout = load_heldout_hashes(args.heldout_hashes)
        print(f"heldout: {len(heldout)} hashes from {args.heldout_hashes}")
    elif args.no_heldout_screen:
        heldout = set()
        print("heldout: NONE (DRY-RUN --no-heldout-screen; screening skipped, rows are NOT graduation-grade)")
    else:
        ap.error("--heldout-hashes is required (or pass --no-heldout-screen for an explicit dry run)")
    summary = graduate_world_chain(args.chain, heldout, args.cursor, args.staged, args.provenance)
    print("graduation:", json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
