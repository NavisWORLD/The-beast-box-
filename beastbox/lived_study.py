"""Paced study on the owner chain.

A confused flag, or a speak-time retrieval that finds nothing already lived or
taught, appends a study turn. The pace is one turn per minute of the injected
clock. The mouth reads a local catalog of public-domain, open-license, or
original records. The lesson is a short narration. The passage stays out of
the chain and out of the prompt.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .lived_attachment import host_attachment
from .lived_chain_public import diary_export_path
from .lived_events import (
    CANONICAL_SUBJECT,
    ActivationRejected,
    ChainRejected,
    backbone_selected,
    IdentityRejected,
    SampleRejected,
)
from .lived_state import LivedStore

GAP_MS = 60_000
SCHEMA = "lived-study-receipt-v1"
ALLOWED_LICENSES = frozenset({
    "CC BY-SA 4.0",
    "CC BY 4.0",
    "CC BY-SA 3.0",
    "CC0",
    "CC0-1.0",
    "MIT",
    "public-domain",
    "public domain",
    "Public Domain",
    "original",
})
_EXCLUDED = ("heldout", "held-out", "held_out", "private", "transcript")


def _tokens(text: str) -> set[str]:
    return {part for part in text.casefold().split() if part}


def _topic(query: str) -> str:
    cleaned = " ".join(str(query).split())
    return cleaned[:200]


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


def _open_store(root: Path) -> LivedStore | None:
    path = root / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite"
    if not path.is_file() or path.is_symlink():
        return None
    try:
        checked = host_attachment(_export_entries(root))
    except (ActivationRejected, OSError, ValueError, TypeError):
        return None
    if not isinstance(checked, Mapping) or checked.get("verified") is not True:
        return None
    inner = checked.get("attachment")
    if not isinstance(inner, Mapping):
        return None
    try:
        return LivedStore.open(path, inner)
    except (ActivationRejected, ChainRejected, IdentityRejected, SampleRejected, OSError, sqlite3.Error):
        return None


def _load_catalog(root: Path, catalog: list[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
    if catalog is not None:
        return list(catalog)
    path = root / "study-catalog.json"
    if path.is_symlink() or not path.is_file():
        return []
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(loaded, dict):
        return []
    entries = loaded.get("entries")
    if not isinstance(entries, list):
        return []
    return [item for item in entries if isinstance(item, Mapping)]


def _excluded(entry: Mapping[str, Any]) -> bool:
    blob = " ".join(str(entry.get(key) or "") for key in ("id", "title", "question", "source")).casefold()
    if any(part in blob for part in _EXCLUDED):
        return True
    title = str(entry.get("title") or "")
    if "<" in title or ">" in title:
        return True
    return False


def choose_entry(catalog: list[Mapping[str, Any]], query: str) -> Mapping[str, Any] | None:
    words = _tokens(query)
    best: Mapping[str, Any] | None = None
    best_key: tuple | None = None
    for entry in catalog:
        license_name = entry.get("license")
        if license_name not in ALLOWED_LICENSES or _excluded(entry):
            continue
        title = str(entry.get("title") or "")
        question = str(entry.get("question") or "")
        overlap = len(words & (_tokens(title) | _tokens(question)))
        if overlap <= 0:
            continue
        ident = str(entry.get("id") or "")
        key = (-overlap, ident)
        if best_key is None or key < best_key:
            best_key = key
            best = entry
    return best


def narrate(entry: Mapping[str, Any]) -> str:
    title = " ".join(str(entry.get("title") or "this").split())[:120]
    license_name = str(entry["license"])
    return (
        f"I studied {title}. I put the idea in my own words and kept the source label. "
        f"License {license_name}."
    )


def _source_label(entry: Mapping[str, Any]) -> str:
    ident = " ".join(str(entry.get("id") or "local").split())[:80]
    return f"knowledge-bank:{ident}"[:300]


def _hits(events: list[Mapping[str, Any]], query: str) -> bool:
    words = _tokens(query)
    exact = _topic(query)
    for body in events:
        if body.get("kind") == "exchange" and body.get("label") == "RECORDED" and isinstance(body.get("text"), str):
            if body["text"].strip() == exact:
                continue
            if words & _tokens(body["text"]):
                return True
        if body.get("kind") == "study_lesson" and isinstance(body.get("narration"), str):
            if words & (_tokens(body["narration"]) | _tokens(str(body.get("topic") or ""))):
                return True
    return False


def _request_event_id(store: LivedStore, topic: str) -> str | None:
    folded = topic.casefold()
    rows = store.db.execute(
        "SELECT event_id, payload FROM lived_events ORDER BY sequence"
    ).fetchall()
    found = None
    for row in rows:
        payload = row["payload"] if not isinstance(row, tuple) else row[1]
        event_id = row["event_id"] if not isinstance(row, tuple) else row[0]
        body = json.loads(payload)
        if isinstance(body, dict) and body.get("kind") == "study_request" and str(body.get("topic") or "").casefold() == folded:
            found = str(event_id)
    return found


def _write_lesson(store: LivedStore, topic: str, chosen: Mapping[str, Any], now_ms: int, request_id: str | None, written: list[str]) -> None:
    narration = narrate(chosen)
    passage = chosen.get("text")
    if isinstance(passage, str) and passage and passage in narration:
        return
    lesson_receipt = store.append_study_lesson(
        topic=topic,
        narration=narration,
        source=_source_label(chosen),
        license=str(chosen["license"]),
        now_ms=now_ms,
    )
    written.append("study_lesson")
    store.append_study_arc(
        stage="studied",
        topic=topic,
        now_ms=now_ms,
        request_event_id=request_id,
        lesson_event_id=lesson_receipt["event_id"],
    )
    written.append("studied")


def _lesson_event_id(store: LivedStore, topic: str) -> str | None:
    folded = topic.casefold()
    rows = store.db.execute(
        "SELECT event_id, payload FROM lived_events ORDER BY sequence"
    ).fetchall()
    found = None
    for row in rows:
        payload = row["payload"] if not isinstance(row, tuple) else row[1]
        event_id = row["event_id"] if not isinstance(row, tuple) else row[0]
        body = json.loads(payload)
        if isinstance(body, dict) and body.get("kind") == "study_lesson" and str(body.get("topic") or "").casefold() == folded:
            found = str(event_id)
    return found


def _lesson_for(events: list[Mapping[str, Any]], topic: str) -> Mapping[str, Any] | None:
    folded = topic.casefold()
    found = None
    for body in events:
        if body.get("kind") == "study_lesson" and str(body.get("topic") or "").casefold() == folded:
            found = body
    return found


def _answered(events: list[Mapping[str, Any]], topic: str) -> bool:
    folded = topic.casefold()
    return any(
        body.get("kind") == "study_arc"
        and body.get("stage") == "answered"
        and str(body.get("topic") or "").casefold() == folded
        for body in events
    )


def _open_question(events: list[Mapping[str, Any]], topic: str) -> bool:
    folded = topic.casefold()
    asked = any(
        body.get("kind") == "study_request" and str(body.get("topic") or "").casefold() == folded
        for body in events
    )
    return asked and not _answered(events, topic)


def _last_study_ms(events: list[Mapping[str, Any]]) -> int | None:
    latest = None
    for body in events:
        if body.get("kind") not in ("study_request", "study_lesson", "study_arc"):
            continue
        stamp = body.get("admitted_at_ms")
        if type(stamp) is int and (latest is None or stamp > latest):
            latest = stamp
    return latest


def _receipt(reason: str, *, wrote: bool, topic: str = "", events: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "wrote": wrote,
        "reason": reason,
        "topic": topic,
        "events": list(events or []),
    }


def study_on_speak(
    root: str | Path,
    query: str,
    now_ms: int,
    *,
    confused: bool = False,
    catalog: list[Mapping[str, Any]] | None = None,
    scope: str = "owner",
) -> dict[str, Any]:
    if scope != "owner":
        return _receipt("isolated", wrote=False)
    if not backbone_selected(os.environ.get("BEASTBOX_LIVED_BACKBONE", "on")):
        return _receipt("off", wrote=False)
    if type(now_ms) is not int or now_ms < 0:
        return _receipt("clock", wrote=False)
    topic = _topic(query)
    if not topic:
        return _receipt("empty", wrote=False)
    base = Path(root)
    store = _open_store(base)
    if store is None:
        return _receipt("unavailable", wrote=False)
    try:
        events = store.events()
        before = [float(item) for item in store.read_lived_snapshot(store.scope)["state12"]]
        last = _last_study_ms(events)
        if last is not None and now_ms < last + GAP_MS:
            return _receipt("paced", wrote=False, topic=topic)
        lesson = _lesson_for(events, topic)
        hit = _hits(events, topic)
        written: list[str] = []
        feelings = store.read_lived_snapshot(store.scope).get("feelings")
        if confused is not True and isinstance(feelings, Mapping) and feelings.get("confused") is True:
            confused = True
        if lesson is not None and not _answered(events, topic):
            if confused is True:
                store.append_study_arc(stage="confused", topic=topic, now_ms=now_ms)
                written.append("confused")
            lesson_id = _lesson_event_id(store, topic)
            store.append_study_arc(
                stage="answered", topic=topic, now_ms=now_ms, lesson_event_id=lesson_id,
            )
            written.append("answered")
        elif _open_question(events, topic):
            chosen = choose_entry(_load_catalog(base, catalog), topic)
            if chosen is None:
                return _receipt("open", wrote=False, topic=topic)
            request_id = _request_event_id(store, topic)
            _write_lesson(store, topic, chosen, now_ms, request_id, written)
        elif hit and confused is not True:
            return _receipt("quiet", wrote=False, topic=topic)
        elif confused is True or not hit:
            if confused is True:
                store.append_study_arc(stage="confused", topic=topic, now_ms=now_ms)
                written.append("confused")
            request = store.append_study_request(topic=topic, now_ms=now_ms)
            written.append("study_request")
            store.append_study_arc(
                stage="asked", topic=topic, now_ms=now_ms, request_event_id=request["event_id"],
            )
            written.append("asked")
            chosen = choose_entry(_load_catalog(base, catalog), topic)
            if chosen is not None:
                _write_lesson(store, topic, chosen, now_ms, request["event_id"], written)
        else:
            return _receipt("quiet", wrote=False, topic=topic)
        after = [float(item) for item in store.read_lived_snapshot(store.scope)["state12"]]
        if after != before:
            written.append("state-changed")
        if "answered" in written:
            reason = "recalled"
        elif "study_lesson" in written:
            reason = "studied"
        else:
            reason = "asked"
        return _receipt(reason, wrote=True, topic=topic, events=written)
    finally:
        store.close()
