"""Public diary-chain receipt on the owner bridge health surface.

The bridge publishes the diary head his life runs on beside the model
fingerprint and the lived backbone head. The expected head is recomputed
here by walking the diary entries with the same hash the diary uses.
The receipt is only that head, the entry count, and the beast id.
Diary thoughts never reach the health surface.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/beastbox-cloud/bridge"))
sys.path.insert(0, str(ROOT / "spark-beasts"))
from qbeast_file import canonical  # noqa: E402

import owner_bridge  # noqa: E402
from beastbox import lived_chain_public, rawrphos_local  # noqa: E402

MARKER = "diary-secret-thought-marker"
EMPTY = {"head": None, "entry_count": 0, "beast_id": None}


def _entry_hash(entry):
    rest = {key: value for key, value in entry.items() if key != "hash"}
    return hashlib.sha256(canonical(rest).encode()).hexdigest()


def _diary(count=3):
    entries = []
    prev = None
    for tick in range(1, count + 1):
        body = {
            "schema": "zeref-diary/v1",
            "beast_id": "bb-7f9c2a03",
            "tick": tick,
            "prev_hash": prev,
            "thought": {"text": f"{MARKER}-{tick}", "by": "deterministic-template"},
        }
        body["hash"] = _entry_hash(body)
        entries.append(body)
        prev = body["hash"]
    return entries


def _export(root: Path, entries) -> Path:
    path = root / "diary" / "diary.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")
    return path


def _offline(monkeypatch):
    monkeypatch.setattr(rawrphos_local, "status", lambda: {"readiness": "OFFLINE_OR_DISCONNECTED", "loaded_step": None})
    monkeypatch.setattr(lived_chain_public, "_mirror_entries", lambda: None)


def test_published_diary_head_matches_recomputed_chain(tmp_path, monkeypatch):
    _offline(monkeypatch)
    entries = _diary(3)
    _export(tmp_path, entries)
    expected_head = entries[-1]["hash"]
    assert _entry_hash(entries[-1]) == expected_head

    health = owner_bridge.served_pin_health(tmp_path)
    receipt = health["diary_chain"]
    assert receipt == {"head": expected_head, "entry_count": 3, "beast_id": "bb-7f9c2a03"}
    assert set(receipt) == {"head", "entry_count", "beast_id"}
    assert "lived_chain" in health
    assert MARKER not in json.dumps(health)


def test_tampered_diary_entry_publishes_no_head(tmp_path, monkeypatch):
    _offline(monkeypatch)
    entries = _diary(3)
    entries[1]["thought"] = {"text": "tampered", "by": "deterministic-template"}
    _export(tmp_path, entries)

    health = owner_bridge.served_pin_health(tmp_path)
    assert health["diary_chain"] == EMPTY


def test_wrong_subject_publishes_no_head(tmp_path, monkeypatch):
    _offline(monkeypatch)
    entries = _diary(2)
    entries[0]["beast_id"] = "bb-deada969"
    entries[0]["hash"] = _entry_hash(entries[0])
    entries[1]["prev_hash"] = entries[0]["hash"]
    entries[1]["hash"] = _entry_hash(entries[1])
    _export(tmp_path, entries)

    health = owner_bridge.served_pin_health(tmp_path)
    assert health["diary_chain"] == EMPTY


def test_absent_diary_publishes_no_invented_head(tmp_path, monkeypatch):
    _offline(monkeypatch)
    health = owner_bridge.served_pin_health(tmp_path)
    assert health["diary_chain"] == EMPTY
    assert health["pin_step"] == rawrphos_local.STEP
    assert health["pin_checkpoint_sha256"] == rawrphos_local.SHA
