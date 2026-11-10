"""Recompute the lived-backbone attachment. Do not trust a configured hash.

The diary walk uses the diary entry hash: canonical JSON, then SHA-256.
The bb-deada969 walk uses the existing QBEAST hash_object. verified is true
only when both walks match the claims. This module does not write the diary,
the lineage file, or a lived store, and it does not change the activation flag.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from .hashutil import canonical_qbeast
from .lived_events import BASIS, CANONICAL_SUBJECT, activation_enabled

DIARY_SUBJECT = "bb-7f9c2a03"
LINEAGE_SUBJECT = "bb-deada969"
DIARY_HEAD = "d444fbae0a1bb52ac189a457a40014ffade40c1db49d558c77b8cfc96bdb97f3"
DIARY_ENTRY_COUNT = 636
LINEAGE_GENESIS = "c39f7838e9a151b2a664fad92b1d2108ab70fb4ef335a023686790769a32aae0"
LINEAGE_HEAD = "d51430d0b0d77867eaf30d67cf1e73ba3f286458d9f302468223c7f065ccfb7b"
ASSOCIATION = "bb-7f9c2a03 as display persona of bb-deada969"
EVIDENCE_VERDICT = "UNVERIFIED"
PRIOR_ENV = "BEASTBOX_LIVED_PRIOR_HEAD"
ORIGIN_ENV = "BEASTBOX_LIVED_ORIGIN_COMMITMENT"
DIARY_SCHEMA = "zeref-diary/v1"
JOINING_SCHEMA = "lived-joining-entry-v1"

_CANONICAL = None
_HASH_OBJECT = None


def _qbeast():
    global _CANONICAL, _HASH_OBJECT
    if _HASH_OBJECT is None:
        from .companion_local.spark_bridge import spark_path

        spark = str(spark_path())
        if spark not in sys.path:
            sys.path.insert(0, spark)
        from qbeast_file import canonical, hash_object

        _CANONICAL = canonical
        _HASH_OBJECT = hash_object
    return _CANONICAL, _HASH_OBJECT


def _entry_hash(entry: Mapping[str, Any]) -> str:
    # The vendored QBEAST canonical (beastbox.hashutil) is byte-identical to
    # spark-beasts/qbeast_file.canonical and needs no generator tree, so the
    # diary walk also recomputes inside the owner-bridge image.
    rest = {key: entry[key] for key in entry if key != "hash"}
    return hashlib.sha256(canonical_qbeast(rest).encode()).hexdigest()


def _lineage_path() -> Path:
    return Path(__file__).resolve().parents[1] / "apps/beastbox-cloud/public/spark/zeref-live-20261010/qbeast.json"


def _empty(reason: str) -> dict[str, Any]:
    return {
        "verified": False,
        "reason": reason,
        "attachment": None,
        "joining_entry": None,
        "diary_head": None,
        "genesis": None,
        "lineage_head": None,
    }


def walk_diary(entries: list[Mapping[str, Any]] | None, claimed_prior_head: str) -> tuple[bool, str, str | None]:
    if not entries:
        return False, "missing-diary", None
    canonical_prev = None
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            return False, "broken-link", None
        if entry.get("beast_id") != DIARY_SUBJECT:
            return False, "subject-mismatch", None
        if entry.get("schema") != DIARY_SCHEMA or entry.get("tick") != index + 1:
            return False, "broken-link", None
        if entry.get("prev_hash") != canonical_prev:
            return False, "broken-link", None
        if _entry_hash(entry) != entry.get("hash"):
            return False, "tampered-entry", None
        canonical_prev = entry.get("hash")
    if canonical_prev != claimed_prior_head:
        return False, "wrong-prior-head", None
    return True, "", canonical_prev


def walk_lineage(
    snapshot: Mapping[str, Any] | None,
    claimed_origin: str,
    claimed_head: str | None = None,
) -> tuple[bool, str, str | None, str | None]:
    if not isinstance(snapshot, Mapping) or not isinstance(snapshot.get("profile"), Mapping):
        return False, "missing-lineage", None, None
    if snapshot["profile"].get("id") != LINEAGE_SUBJECT:
        return False, "subject-mismatch", None, None
    public_state = snapshot.get("public_state")
    progress = snapshot.get("progress")
    events = snapshot.get("events")
    if (
        not isinstance(public_state, Mapping)
        or not isinstance(progress, Mapping)
        or not isinstance(events, list)
        or not events
    ):
        return False, "broken-link", None, None
    _canonical, hash_object = _qbeast()
    genesis = hash_object({
        "domain": "genesis",
        "profile": snapshot["profile"],
        "public_state": public_state,
        "progress": progress,
    })
    if genesis != claimed_origin:
        return False, "wrong-genesis", genesis, None
    if not isinstance(events[0], Mapping) or events[0].get("parent") != genesis:
        return False, "wrong-genesis", genesis, None
    body = {key: snapshot[key] for key in snapshot if key != "digest"}
    if hash_object(body) != snapshot.get("digest"):
        return False, "tampered-entry", genesis, None
    head = genesis
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            return False, "broken-link", genesis, None
        if event.get("generation") != index + 1 or event.get("parent") != head or event.get("kind") != "memory":
            return False, "broken-link", genesis, None
        expected = hash_object({
            "domain": "event",
            "generation": event["generation"],
            "parent": event["parent"],
            "proposal_id": event["proposal_id"],
            "kind": event["kind"],
            "payload": event["payload"],
        })
        if event.get("hash") != expected:
            return False, "tampered-entry", genesis, None
        head = event["hash"]
    if head != snapshot.get("lineage_head") or (claimed_head is not None and head != claimed_head):
        return False, "wrong-lineage-head", genesis, head
    return True, "", genesis, head


def build_joining_entry(
    *,
    diary_head: str = DIARY_HEAD,
    genesis: str = LINEAGE_GENESIS,
    lineage_head: str = LINEAGE_HEAD,
    diary_entries: int = DIARY_ENTRY_COUNT,
) -> dict[str, Any]:
    """First going-forward entry. Returned in memory; nothing is written."""
    body = {
        "schema": JOINING_SCHEMA,
        "kind": "joining",
        "predecessor": diary_head,
        "prev_hash": diary_head,
        "continues_from_diary_head": diary_head,
        "diary_subject": DIARY_SUBJECT,
        "diary_entries": diary_entries,
        "deada969_genesis": genesis,
        "deada969_lineage_head": lineage_head,
        "lineage_subject": LINEAGE_SUBJECT,
        "association": ASSOCIATION,
        "owner_approved": "owner-approved",
        "evidence_verdict": EVIDENCE_VERDICT,
    }
    body["hash"] = _entry_hash(body)
    return body


def recompute_across_seam(
    diary_entries: list[Mapping[str, Any]],
    lineage: Mapping[str, Any],
    joining_entry: Mapping[str, Any],
) -> dict[str, Any]:
    diary_ok, diary_reason, diary_head = walk_diary(diary_entries, str(joining_entry.get("predecessor")))
    lineage_ok, lineage_reason, genesis, lineage_head = walk_lineage(
        lineage,
        str(joining_entry.get("deada969_genesis")),
        str(joining_entry.get("deada969_lineage_head")),
    )
    hash_ok = _entry_hash(joining_entry) == joining_entry.get("hash")
    linked = (
        diary_head is not None
        and joining_entry.get("prev_hash") == diary_head
        and joining_entry.get("continues_from_diary_head") == diary_head
        and joining_entry.get("predecessor") == diary_head
        and joining_entry.get("deada969_genesis") == genesis
        and joining_entry.get("deada969_lineage_head") == lineage_head
        and joining_entry.get("evidence_verdict") == EVIDENCE_VERDICT
        and joining_entry.get("association") == ASSOCIATION
        and joining_entry.get("diary_subject") == DIARY_SUBJECT
        and joining_entry.get("lineage_subject") == LINEAGE_SUBJECT
        and joining_entry.get("diary_entries") == len(diary_entries)
    )
    if not diary_ok:
        reason = diary_reason
    elif not lineage_ok:
        reason = lineage_reason
    elif not hash_ok:
        reason = "tampered-entry"
    elif not linked:
        reason = "broken-link"
    else:
        reason = ""
    return {
        "verified": bool(diary_ok and lineage_ok and hash_ok and linked),
        "reason": reason,
        "diary_head": diary_head,
        "genesis": genesis,
        "lineage_head": lineage_head,
        "evidence_verdict": joining_entry.get("evidence_verdict"),
        "association": joining_entry.get("association"),
        "diary_subject": joining_entry.get("diary_subject"),
        "lineage_subject": joining_entry.get("lineage_subject"),
    }


def host_attachment(
    diary_entries: list[Mapping[str, Any]] | None = None,
    lineage: Mapping[str, Any] | None = None,
    *,
    claimed_prior_head: str | None = None,
    claimed_origin: str | None = None,
    claimed_lineage_head: str | None = None,
) -> dict[str, Any]:
    """Return a verified attachment only after both chains recompute.

    BEASTBOX_LIVED_BACKBONE defaults on. The exact value off attaches nothing.
    This function does not set the flag. The prior-head and origin claims default to BEASTBOX_LIVED_PRIOR_HEAD
    and BEASTBOX_LIVED_ORIGIN_COMMITMENT. A failed walk attaches nothing.
    """
    if not activation_enabled():
        return _empty("activation")
    # Literal env names: the repo env inventory (make env-check) refuses
    # dynamic environment reads so configuration stays auditable.
    prior = claimed_prior_head if claimed_prior_head is not None else os.environ.get("BEASTBOX_LIVED_PRIOR_HEAD")
    origin = claimed_origin if claimed_origin is not None else os.environ.get("BEASTBOX_LIVED_ORIGIN_COMMITMENT")
    if not prior or not origin:
        return _empty("missing-claim")
    if not diary_entries:
        return _empty("missing-diary")
    if lineage is None:
        path = _lineage_path()
        if not path.is_file():
            return _empty("missing-lineage")
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return _empty("missing-lineage")
        lineage = loaded
    diary_ok, diary_reason, diary_head = walk_diary(list(diary_entries), prior)
    if not diary_ok:
        return _empty(diary_reason)
    lineage_ok, lineage_reason, genesis, lineage_head = walk_lineage(lineage, origin, claimed_lineage_head)
    if not lineage_ok:
        return _empty(lineage_reason)
    joining = build_joining_entry(
        diary_head=str(diary_head),
        genesis=str(genesis),
        lineage_head=str(lineage_head),
        diary_entries=len(diary_entries),
    )
    attachment = {
        "schema": "lived-origin-attachment-v1",
        "subject_id": CANONICAL_SUBJECT,
        "scope": "owner",
        "basis": BASIS,
        "origin_commitment": genesis,
        "prior_head": diary_head,
        "verified": True,
    }
    return {
        "verified": True,
        "reason": "",
        "attachment": attachment,
        "joining_entry": joining,
        "diary_head": diary_head,
        "genesis": genesis,
        "lineage_head": lineage_head,
    }
