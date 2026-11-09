"""Commit one owner exchange onto the canonical lived chain.

The heard line is written before the model runs. The spoken line is written
after, and only the delivered reply. Guest and visitor scopes never open the
owner file. The attachment is the recomputed one: the flag must be exactly
on, and ``verified`` must be True. Any other result writes nothing.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Callable, Mapping

from .hashutil import sha256_text
from .lived_attachment import host_attachment
from .lived_chain_public import diary_export_path
from .lived_events import (
    CANONICAL_SUBJECT,
    ActivationRejected,
    ChainRejected,
    IdentityRejected,
    SampleRejected,
)
from .lived_recall import recall_for_root
from .lived_state import LivedStore


def _allows_write(attachment: Mapping[str, Any] | None) -> bool:
    if os.environ.get("BEASTBOX_LIVED_BACKBONE", "off") != "on":
        return False
    if not isinstance(attachment, Mapping):
        return False
    if attachment.get("verified") is not True:
        return False
    return attachment.get("scope") == "owner" and attachment.get("subject_id") == CANONICAL_SUBJECT


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


def _current_attachment(root: Path) -> Mapping[str, Any] | None:
    if os.environ.get("BEASTBOX_LIVED_BACKBONE", "off") != "on":
        return None
    try:
        result = host_attachment(_export_entries(root))
    except (ActivationRejected, OSError, ValueError, TypeError):
        return None
    if not isinstance(result, Mapping) or result.get("verified") is not True:
        return None
    inner = result.get("attachment")
    if not isinstance(inner, Mapping) or not _allows_write(inner):
        return None
    return inner


def _host_fields(attachment: Mapping[str, Any]) -> dict[str, Any]:
    return {key: attachment[key] for key in (
        "schema", "subject_id", "scope", "basis", "origin_commitment", "prior_head", "verified",
    )}


def _as_text(produced: Any) -> str | None:
    if isinstance(produced, str):
        return produced
    if isinstance(produced, dict) and isinstance(produced.get("response"), str):
        return produced["response"]
    return None


def _blank(status: str, *, reply: str | None, generated: bool, receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "wrote": False,
        "status": status,
        "reply": reply,
        "generated": generated,
        "receipt": receipt,
        "recovered": False,
    }


def _owner_path(root: Path) -> Path:
    return Path(root) / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite"


def run_owner_exchange(
    root: str | Path,
    *,
    scope: str,
    heard: str,
    exchange_id: str,
    now_ms: int,
    generate: Callable[[], Any],
    model: str | None = None,
    delivered: bool = True,
    acknowledge: bool = True,
    unchosen: str | None = None,
) -> dict[str, Any]:
    """Append the heard line and, when delivered, only the chosen reply.

    ``unchosen`` is accepted so a two-draft turn can name the draft that must
    not be stored. It is never written.
    """
    del unchosen
    if scope != "owner":
        return _blank("isolated", reply=None, generated=False)
    attachment = _current_attachment(Path(root))
    if attachment is None:
        produced = generate()
        return _blank("skipped", reply=_as_text(produced), generated=True)
    path = _owner_path(Path(root))
    if path.is_symlink() or path.parent.is_symlink():
        produced = generate()
        return _blank("skipped", reply=_as_text(produced), generated=True)
    try:
        store = LivedStore.open(path, _host_fields(attachment))
    except (ActivationRejected, ChainRejected, IdentityRejected, SampleRejected, OSError, sqlite3.Error):
        produced = generate()
        return _blank(
            "unconfirmed", reply=_as_text(produced), generated=True,
            receipt={"schema": "lived-exchange-receipt-v1", "status": "unconfirmed", "exchange_id": exchange_id},
        )
    try:
        return _commit(
            store, heard=heard, exchange_id=exchange_id, now_ms=now_ms, generate=generate,
            model=model, delivered=delivered, acknowledge=acknowledge,
        )
    finally:
        store.close()


def _commit(
    store: LivedStore, *, heard: str, exchange_id: str, now_ms: int, generate: Callable[[], Any],
    model: str | None, delivered: bool, acknowledge: bool,
) -> dict[str, Any]:
    row = store.exchange_row(exchange_id)
    if row is not None and row.get("spoken_event_id"):
        receipt = store.exchange_receipt(str(row["spoken_event_id"]))
        receipt["acknowledged"] = bool(row.get("acknowledged"))
        return {
            "wrote": True, "status": "lived", "reply": store.exchange_reply(str(row["spoken_event_id"])),
            "generated": False, "receipt": receipt, "recovered": True,
        }
    if row is not None and row.get("failure_event_id"):
        receipt = store.exchange_receipt(str(row["failure_event_id"]))
        return {
            "wrote": True, "status": "failed", "reply": None, "generated": False,
            "receipt": receipt, "recovered": True,
        }
    if row is None or not row.get("heard_event_id"):
        store.begin_exchange(exchange_id=exchange_id, text=heard, now_ms=now_ms)
    if not delivered:
        try:
            receipt = store.fail_exchange(exchange_id=exchange_id, now_ms=now_ms)
        except sqlite3.Error:
            return _blank(
                "unconfirmed", reply=None, generated=False,
                receipt={"schema": "lived-exchange-receipt-v1", "status": "unconfirmed", "exchange_id": exchange_id},
            )
        return {
            "wrote": True, "status": "failed", "reply": None, "generated": False,
            "receipt": receipt, "recovered": False,
        }
    staged = store.staged_reply(exchange_id)
    generated = False
    if staged is not None:
        reply = staged["reply"]
        if model is None:
            model = staged.get("model")
    else:
        reply = _as_text(generate())
        generated = True
        if not isinstance(reply, str) or not reply.strip():
            try:
                receipt = store.fail_exchange(exchange_id=exchange_id, now_ms=now_ms)
            except sqlite3.Error:
                return _blank(
                    "unconfirmed", reply=reply, generated=True,
                    receipt={"schema": "lived-exchange-receipt-v1", "status": "unconfirmed", "exchange_id": exchange_id},
                )
            return {
                "wrote": True, "status": "failed", "reply": reply, "generated": True,
                "receipt": receipt, "recovered": False,
            }
        try:
            store.stage_exchange_reply(exchange_id, reply, model)
        except sqlite3.Error:
            return _blank(
                "unconfirmed", reply=reply, generated=True,
                receipt={"schema": "lived-exchange-receipt-v1", "status": "unconfirmed", "exchange_id": exchange_id},
            )
    try:
        receipt = store.finish_exchange(exchange_id=exchange_id, reply=reply, now_ms=now_ms, model=model)
    except sqlite3.Error:
        return _blank(
            "unconfirmed", reply=reply, generated=generated,
            receipt={"schema": "lived-exchange-receipt-v1", "status": "unconfirmed", "exchange_id": exchange_id},
        )
    if acknowledge:
        store.acknowledge_exchange(exchange_id)
        receipt = dict(receipt)
        receipt["acknowledged"] = True
    else:
        receipt = dict(receipt)
        receipt["acknowledged"] = False
    return {
        "wrote": True, "status": "lived", "reply": reply, "generated": generated,
        "receipt": receipt, "recovered": False,
    }


def speak_owner(root: str | Path, heard: str, generate: Callable[[], Any], *, now_ms: int) -> Any:
    """Owner chat hook. Flag-off and unverified attachments return the model result unchanged."""
    if _current_attachment(Path(root)) is None:
        return generate()
    exchange_id = _exchange_id_for(Path(root), heard)
    held: dict[str, Any] = {}

    def once() -> Any:
        if "value" not in held:
            held["recall"] = recall_for_root(Path(root), heard)
            held["value"] = generate()
        return held["value"]

    result = run_owner_exchange(
        root, scope="owner", heard=heard, exchange_id=exchange_id, now_ms=now_ms, generate=once,
    )
    if result["status"] == "skipped":
        return held.get("value", result["reply"])
    if result["recovered"]:
        recall = held.get("recall") or recall_for_root(Path(root), heard)
        return {
            "response": result["reply"],
            "lived_exchange": result["receipt"],
            "lived_recall": recall["receipt"],
            "recovered": True,
        }
    body = held.get("value")
    if not isinstance(body, dict):
        body = {"response": result["reply"]}
    else:
        body = dict(body)
    if result["receipt"] is not None:
        body["lived_exchange"] = result["receipt"]
    if "lived_recall" not in body and "recall" in held:
        body["lived_recall"] = held["recall"]["receipt"]
    return body


def _exchange_id_for(root: Path, text: str) -> str:
    digest = sha256_text(text)
    path = _owner_path(root)
    if not path.is_file():
        return sha256_text(f"lived-exchange-v1\nowner\nowner\n{text}\n0")[:32]
    attachment = _current_attachment(root)
    if attachment is None:
        return sha256_text(f"lived-exchange-v1\nowner\nowner\n{text}\n0")[:32]
    store = LivedStore.open(path, _host_fields(attachment))
    try:
        rows = store.db.execute(
            "SELECT exchange_id, acknowledged FROM lived_exchanges WHERE text_sha256=? ORDER BY exchange_id",
            (digest,),
        ).fetchall()
    finally:
        store.close()
    for row in rows:
        acknowledged = row["acknowledged"] if not isinstance(row, tuple) else row[1]
        exchange_id = row["exchange_id"] if not isinstance(row, tuple) else row[0]
        if not acknowledged:
            return str(exchange_id)
    return sha256_text(f"lived-exchange-v1\nowner\nowner\n{text}\n{len(rows)}")[:32]
