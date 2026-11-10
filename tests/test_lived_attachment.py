"""The attach check has to recompute both historical chains.

A set flag and two configured hashes are not verification. A tampered entry,
a wrong prior head, a wrong genesis, or a subject mismatch returns
verified=False and attaches nothing. The joining entry is built in memory.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "spark-beasts"))
from qbeast_file import canonical, hash_object  # noqa: E402

from beastbox.lived_events import ACTIVATION_ENV, CANONICAL_SUBJECT, validate_attachment  # noqa: E402

LINEAGE_PATH = ROOT / "apps/beastbox-cloud/public/spark/zeref-live-20261010/qbeast.json"
RULED_DIARY_HEAD = "d444fbae0a1bb52ac189a457a40014ffade40c1db49d558c77b8cfc96bdb97f3"
RULED_GENESIS = "c39f7838e9a151b2a664fad92b1d2108ab70fb4ef335a023686790769a32aae0"
RULED_LINEAGE_HEAD = "d51430d0b0d77867eaf30d67cf1e73ba3f286458d9f302468223c7f065ccfb7b"
RULED_ASSOCIATION = "bb-7f9c2a03 as display persona of bb-deada969"
PRIOR_ENV = "BEASTBOX_LIVED_PRIOR_HEAD"
ORIGIN_ENV = "BEASTBOX_LIVED_ORIGIN_COMMITMENT"


def _load():
    from beastbox.lived_attachment import (
        ASSOCIATION,
        DIARY_ENTRY_COUNT,
        DIARY_HEAD,
        DIARY_SUBJECT,
        EVIDENCE_VERDICT,
        LINEAGE_GENESIS,
        LINEAGE_HEAD,
        LINEAGE_SUBJECT,
        build_joining_entry,
        host_attachment,
        recompute_across_seam,
    )

    return {
        "ASSOCIATION": ASSOCIATION,
        "DIARY_ENTRY_COUNT": DIARY_ENTRY_COUNT,
        "DIARY_HEAD": DIARY_HEAD,
        "DIARY_SUBJECT": DIARY_SUBJECT,
        "EVIDENCE_VERDICT": EVIDENCE_VERDICT,
        "LINEAGE_GENESIS": LINEAGE_GENESIS,
        "LINEAGE_HEAD": LINEAGE_HEAD,
        "LINEAGE_SUBJECT": LINEAGE_SUBJECT,
        "build_joining_entry": build_joining_entry,
        "host_attachment": host_attachment,
        "recompute_across_seam": recompute_across_seam,
    }


def _entry_hash(entry):
    rest = {key: value for key, value in entry.items() if key != "hash"}
    return hashlib.sha256(canonical(rest).encode()).hexdigest()


def _diary_entry(tick, prev, **overrides):
    body = {
        "schema": "zeref-diary/v1",
        "beast_id": "bb-7f9c2a03",
        "tick": tick,
        "prev_hash": prev,
        "thought": {"text": f"tick-{tick}", "by": "deterministic-template"},
    }
    body.update(overrides)
    body["hash"] = _entry_hash(body)
    return body


def _good_diary(count=2):
    entries = []
    prev = None
    for tick in range(1, count + 1):
        entries.append(_diary_entry(tick, prev))
        prev = entries[-1]["hash"]
    return entries


def _lineage():
    return json.loads(LINEAGE_PATH.read_text(encoding="utf-8"))


def _arm(monkeypatch, prior, origin):
    monkeypatch.setenv(ACTIVATION_ENV, "on")
    monkeypatch.setenv(PRIOR_ENV, prior)
    monkeypatch.setenv(ORIGIN_ENV, origin)


def test_tampered_diary_entry_is_not_verified(monkeypatch):
    api = _load()
    diary = _good_diary()
    lineage = _lineage()
    diary[0]["thought"] = {"text": "tampered", "by": "deterministic-template"}
    _arm(monkeypatch, diary[-1]["hash"], RULED_GENESIS)
    result = api["host_attachment"](diary, lineage)
    assert result["verified"] is False
    assert result["attachment"] is None
    assert result["joining_entry"] is None
    assert result["reason"] == "tampered-entry"


def test_tampered_lineage_event_is_not_verified(monkeypatch):
    api = _load()
    diary = _good_diary()
    lineage = _lineage()
    lineage["events"][0]["payload"] = {
        "summary": "tampered birth record",
        "source_ref": lineage["events"][0]["payload"]["source_ref"],
    }
    _arm(monkeypatch, diary[-1]["hash"], RULED_GENESIS)
    result = api["host_attachment"](diary, lineage)
    assert result["verified"] is False
    assert result["attachment"] is None
    assert result["reason"] == "tampered-entry"


def test_wrong_prior_head_is_not_verified(monkeypatch):
    api = _load()
    diary = _good_diary()
    _arm(monkeypatch, RULED_LINEAGE_HEAD, RULED_GENESIS)
    result = api["host_attachment"](diary, _lineage())
    assert result["verified"] is False
    assert result["attachment"] is None
    assert result["joining_entry"] is None
    assert result["reason"] == "wrong-prior-head"


def test_wrong_genesis_is_not_verified(monkeypatch):
    api = _load()
    diary = _good_diary()
    _arm(monkeypatch, diary[-1]["hash"], "ab" * 32)
    result = api["host_attachment"](diary, _lineage())
    assert result["verified"] is False
    assert result["attachment"] is None
    assert result["reason"] == "wrong-genesis"


def test_subject_mismatch_is_not_verified(monkeypatch):
    api = _load()
    diary = _good_diary()
    diary[1]["beast_id"] = "bb-deada969"
    diary[1]["hash"] = _entry_hash(diary[1])
    _arm(monkeypatch, diary[-1]["hash"], RULED_GENESIS)
    swapped_diary = api["host_attachment"](diary, _lineage())
    assert swapped_diary["verified"] is False
    assert swapped_diary["attachment"] is None
    assert swapped_diary["reason"] == "subject-mismatch"

    intact = _good_diary()
    lineage = _lineage()
    lineage["profile"]["id"] = "bb-7f9c2a03"
    _arm(monkeypatch, intact[-1]["hash"], RULED_GENESIS)
    swapped_lineage = api["host_attachment"](intact, lineage)
    assert swapped_lineage["verified"] is False
    assert swapped_lineage["attachment"] is None
    assert swapped_lineage["reason"] == "subject-mismatch"


def test_flag_off_attaches_nothing(monkeypatch):
    api = _load()
    diary = _good_diary()
    monkeypatch.setenv(ACTIVATION_ENV, "off")
    monkeypatch.setenv(PRIOR_ENV, diary[-1]["hash"])
    monkeypatch.setenv(ORIGIN_ENV, RULED_GENESIS)
    result = api["host_attachment"](diary, _lineage())
    assert result["verified"] is False
    assert result["attachment"] is None
    assert result["joining_entry"] is None
    assert result["reason"] == "activation"


def test_recomputed_diary_and_lineage_verify_on_a_good_fixture(monkeypatch):
    api = _load()
    diary = _good_diary(3)
    lineage = _lineage()
    lineage_bytes = LINEAGE_PATH.read_bytes()
    genesis = hash_object({
        "domain": "genesis",
        "profile": lineage["profile"],
        "public_state": lineage["public_state"],
        "progress": lineage["progress"],
    })
    event = lineage["events"][0]
    event_hash = hash_object({
        "domain": "event",
        "generation": event["generation"],
        "parent": event["parent"],
        "proposal_id": event["proposal_id"],
        "kind": event["kind"],
        "payload": event["payload"],
    })
    assert genesis == RULED_GENESIS
    assert event_hash == RULED_LINEAGE_HEAD
    _arm(monkeypatch, diary[-1]["hash"], genesis)
    result = api["host_attachment"](diary, lineage)
    assert result["verified"] is True
    assert result["reason"] == ""
    assert result["diary_head"] == diary[-1]["hash"]
    assert result["genesis"] == genesis
    assert result["lineage_head"] == event_hash
    attachment = result["attachment"]
    assert attachment["verified"] is True
    assert attachment["prior_head"] == diary[-1]["hash"]
    assert attachment["origin_commitment"] == genesis
    assert attachment["subject_id"] == CANONICAL_SUBJECT
    assert attachment["subject_id"] != "bb-7f9c2a03"
    checked = validate_attachment(attachment)
    assert checked["verified"] is True
    assert checked["prior_head"] == diary[-1]["hash"]
    joining = result["joining_entry"]
    assert joining["predecessor"] == diary[-1]["hash"]
    assert joining["continues_from_diary_head"] == diary[-1]["hash"]
    assert joining["deada969_genesis"] == genesis
    assert joining["deada969_lineage_head"] == event_hash
    assert joining["diary_subject"] == "bb-7f9c2a03"
    assert joining["lineage_subject"] == "bb-deada969"
    assert joining["evidence_verdict"] == "UNVERIFIED"
    assert joining["association"] == RULED_ASSOCIATION
    assert joining["hash"] == _entry_hash(joining)
    assert lineage["events"][0]["hash"] == event_hash
    assert LINEAGE_PATH.read_bytes() == lineage_bytes


def test_ruled_joining_entry_prints_the_open_fields():
    api = _load()
    before = LINEAGE_PATH.read_bytes()
    entry = api["build_joining_entry"]()
    assert api["DIARY_HEAD"] == RULED_DIARY_HEAD
    assert api["LINEAGE_GENESIS"] == RULED_GENESIS
    assert api["LINEAGE_HEAD"] == RULED_LINEAGE_HEAD
    assert api["DIARY_SUBJECT"] == "bb-7f9c2a03"
    assert api["LINEAGE_SUBJECT"] == "bb-deada969"
    assert api["DIARY_ENTRY_COUNT"] == 636
    assert api["ASSOCIATION"] == RULED_ASSOCIATION
    assert api["EVIDENCE_VERDICT"] == "UNVERIFIED"
    assert entry["schema"] == "lived-joining-entry-v1"
    assert entry["kind"] == "joining"
    assert entry["predecessor"] == RULED_DIARY_HEAD
    assert entry["prev_hash"] == RULED_DIARY_HEAD
    assert entry["continues_from_diary_head"] == RULED_DIARY_HEAD
    assert entry["diary_subject"] == "bb-7f9c2a03"
    assert entry["diary_entries"] == 636
    assert entry["deada969_genesis"] == RULED_GENESIS
    assert entry["deada969_lineage_head"] == RULED_LINEAGE_HEAD
    assert entry["lineage_subject"] == "bb-deada969"
    assert entry["association"] == RULED_ASSOCIATION
    assert entry["owner_approved"] == "owner-approved"
    assert entry["evidence_verdict"] == "UNVERIFIED"
    preimage = canonical({key: value for key, value in entry.items() if key != "hash"})
    assert "UNVERIFIED" in preimage
    assert RULED_ASSOCIATION in preimage
    assert RULED_DIARY_HEAD in preimage
    assert RULED_GENESIS in preimage
    assert RULED_LINEAGE_HEAD in preimage
    assert entry["hash"] == hashlib.sha256(preimage.encode()).hexdigest()
    assert LINEAGE_PATH.read_bytes() == before


def test_recompute_across_the_seam_sees_both_chains_and_the_unverified_label():
    api = _load()
    diary = _good_diary(3)
    sealed_diary = json.loads(json.dumps(diary))
    lineage = _lineage()
    sealed_lineage = json.loads(json.dumps(lineage))
    entry = api["build_joining_entry"](
        diary_head=diary[-1]["hash"],
        genesis=RULED_GENESIS,
        lineage_head=RULED_LINEAGE_HEAD,
        diary_entries=len(diary),
    )
    seen = api["recompute_across_seam"](diary, lineage, entry)
    assert seen["verified"] is True
    assert seen["diary_head"] == diary[-1]["hash"]
    assert seen["genesis"] == RULED_GENESIS
    assert seen["lineage_head"] == RULED_LINEAGE_HEAD
    assert seen["evidence_verdict"] == "UNVERIFIED"
    assert seen["association"] == RULED_ASSOCIATION
    assert seen["diary_subject"] == "bb-7f9c2a03"
    assert seen["lineage_subject"] == "bb-deada969"
    assert diary == sealed_diary
    assert lineage == sealed_lineage
