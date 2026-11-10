"""What the owner mouth reads from the lived chain at speak time.

Recorded lines are LIVED. Study lessons are TAUGHT. LIVED is placed first.
The prompt keeps a short window. The chain is not trimmed. The receipt names
the entries, their hashes, the state hash, and the two drift layers.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .hashutil import canonical_json, sha256_text
from .lived_attachment import host_attachment
from .lived_chain_public import diary_export_path
from .lived_events import (
    CANONICAL_SUBJECT,
    ActivationRejected,
    ChainRejected,
    IdentityRejected,
    SampleRejected,
)
from .lived_state import LivedStore

WINDOW = 4
TEXT_WINDOW = 160
SCHEMA = "lived-recall-receipt-v1"
DRIFT_LAYERS = {
    "root": {"measurements": "RECORDED", "clock": "SIMULATED"},
    "living": {"sight": "DERIVED", "face": "ESTIMATE", "pulse": "ESTIMATE"},
}


def _empty(state_sha256: str | None = None) -> dict[str, Any]:
    return {
        "prompt": "",
        "receipt": {
            "schema": SCHEMA,
            "state_sha256": state_sha256,
            "entries": [],
            "drift": DRIFT_LAYERS,
        },
    }


def _tokens(text: str) -> set[str]:
    return {part for part in text.lower().split() if part}


def _rank(items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    words = _tokens(query)
    def key(item: dict[str, Any]) -> tuple:
        overlap = len(words & _tokens(item["text"]))
        return (-overlap, -int(item["sequence"]), item["event_id"])
    return sorted(items, key=key)[:WINDOW]


def recall_events(events: list[Mapping[str, Any]], query: str, state_sha256: str | None) -> dict[str, Any]:
    lived: list[dict[str, Any]] = []
    taught: list[dict[str, Any]] = []
    for body in events:
        event_id = body.get("_event_id")
        if not isinstance(event_id, str):
            event_id = sha256_text(canonical_json({key: value for key, value in body.items() if key != "_event_id"}))
        if body.get("kind") == "exchange" and body.get("label") == "RECORDED" and isinstance(body.get("text"), str):
            lived.append({
                "event_id": event_id,
                "kind": "LIVED",
                "label": "RECORDED",
                "sequence": int(body["sequence"]),
                "text": body["text"],
                "sha256": sha256_text(body["text"]),
            })
        elif body.get("kind") == "study_lesson" and body.get("label") == "TAUGHT" and isinstance(body.get("narration"), str):
            taught.append({
                "event_id": event_id,
                "kind": "TAUGHT",
                "label": "TAUGHT",
                "sequence": int(body["sequence"]),
                "text": body["narration"],
                "sha256": sha256_text(body["narration"]),
            })
    chosen = _rank(lived, query) + _rank(taught, query)
    lines = [f"{item['kind']}: {item['text'][:TEXT_WINDOW]}" for item in chosen]
    prompt = ""
    if lines:
        prompt = "FABRIC:\n" + "\n".join(lines) + "\n"
    return {
        "prompt": prompt,
        "receipt": {
            "schema": SCHEMA,
            "state_sha256": state_sha256,
            "entries": [
                {"event_id": item["event_id"], "kind": item["kind"], "label": item["label"], "sha256": item["sha256"]}
                for item in chosen
            ],
            "drift": DRIFT_LAYERS,
        },
    }


def _export_entries(root: Path) -> list[dict[str, Any]] | None:
    path = diary_export_path(root)
    if path.is_symlink() or not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    entries: list[dict[str, Any]] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(entry, dict):
            return None
        entries.append(entry)
    return entries or None


def recall_for_root(root: str | Path, query: str) -> dict[str, Any]:
    base = Path(root)
    path = base / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite"
    if not path.is_file() or path.is_symlink():
        return _empty()
    try:
        checked = host_attachment(_export_entries(base))
    except (ActivationRejected, OSError, ValueError, TypeError):
        return _empty()
    if not isinstance(checked, Mapping) or checked.get("verified") is not True:
        return _empty()
    inner = checked.get("attachment")
    if not isinstance(inner, Mapping):
        return _empty()
    try:
        store = LivedStore.open(path, inner)
    except (ActivationRejected, ChainRejected, IdentityRejected, SampleRejected, OSError, sqlite3.Error):
        return _empty()
    try:
        snap = store.read_lived_snapshot(store.scope)
        rows = store.db.execute(
            "SELECT event_id, payload FROM lived_events ORDER BY sequence"
        ).fetchall()
        loaded = []
        for row in rows:
            body = json.loads(row["payload"] if not isinstance(row, tuple) else row[1])
            if isinstance(body, dict):
                body["_event_id"] = row["event_id"] if not isinstance(row, tuple) else row[0]
                loaded.append(body)
        return recall_events(loaded, query, snap.get("state_sha256"))
    finally:
        store.close()
