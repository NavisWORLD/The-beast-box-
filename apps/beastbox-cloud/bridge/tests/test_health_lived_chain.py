"""Public lived-chain receipt on the owner bridge health surface.

The bridge publishes the head it serves beside the model fingerprint.
The expected head is recomputed here from the stored event payloads with
the same hash the chain uses. The receipt is only that head, the entry
count, and the subject id.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/beastbox-cloud/bridge"))

import owner_bridge
from beastbox.hashutil import sha256_text
from beastbox.lived_events import CANONICAL_SUBJECT
from beastbox import rawrphos_local
from tests.test_lived_state import PRIOR, face_record, open_owner, sample

PIN_FILE = ROOT / "apps/beastbox-cloud/lib/rawrphos-public-pin.json"
PRIVATE = ("session-a", "sensor-sample-v1", "feelings", "transcript", PRIOR)


def _chain_path(root: Path) -> Path:
    return root / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite"


def _serve(root: Path) -> None:
    path = _chain_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    store = open_owner(path)
    store.admit_sensor(sample(1, face=face_record()), now_ms=1_700_000_000_000)
    store.admit_sensor(sample(2, face=face_record(present=False)), now_ms=1_700_000_000_500)
    store.close()


def recompute_served_chain(db_path: Path) -> dict:
    """Walk the chain the bridge stored. Independent of the publisher."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        meta = {row["key"]: row["value"] for row in db.execute("SELECT key, value FROM lived_meta")}
        head = meta["prior_head"]
        rows = list(db.execute(
            "SELECT payload, sha256 FROM lived_events ORDER BY sequence"
        ))
        for row in rows:
            assert sha256_text(row["payload"]) == row["sha256"]
            body = json.loads(row["payload"])
            assert body["previous"] == head
            assert body["subject_id"] == meta["subject_id"]
            head = row["sha256"]
        return {"head": head, "entry_count": len(rows), "subject_id": meta["subject_id"]}
    finally:
        db.close()


def test_published_lived_head_matches_recomputed_chain(tmp_path, monkeypatch):
    monkeypatch.setattr(rawrphos_local, "status", lambda: {"readiness": "OFFLINE_OR_DISCONNECTED", "loaded_step": None})
    assert os.environ.get("BEASTBOX_LIVED_BACKBONE") != "on"
    pin_before = PIN_FILE.read_bytes()
    _serve(tmp_path)
    expected = recompute_served_chain(_chain_path(tmp_path))
    assert expected["entry_count"] == 2
    assert expected["subject_id"] == CANONICAL_SUBJECT
    assert expected["head"] != PRIOR

    health = owner_bridge.served_pin_health(tmp_path)
    receipt = health["lived_chain"]

    assert receipt == expected
    assert set(receipt) == {"head", "entry_count", "subject_id"}
    assert health["pin_checkpoint_sha256"] == rawrphos_local.SHA
    assert health["schema"] == "beastbox-bridge-health-v2"
    published = json.dumps(health)
    for private in PRIVATE:
        assert private not in published
    assert os.environ.get("BEASTBOX_LIVED_BACKBONE") != "on"
    assert PIN_FILE.read_bytes() == pin_before
    source = Path(owner_bridge.__file__).read_text()
    assert "served_pin_health(self.bridge.root)" in source


def test_tampered_snapshot_head_is_not_published(tmp_path, monkeypatch):
    monkeypatch.setattr(rawrphos_local, "status", lambda: {"readiness": "OFFLINE_OR_DISCONNECTED"})
    _serve(tmp_path)
    path = _chain_path(tmp_path)
    walked = recompute_served_chain(path)["head"]
    db = sqlite3.connect(path)
    sequence, payload = db.execute(
        "SELECT sequence, payload FROM lived_snapshots ORDER BY sequence DESC LIMIT 1"
    ).fetchone()
    body = json.loads(payload)
    body["chain_head"] = "ab" * 32
    db.execute(
        "UPDATE lived_snapshots SET payload=? WHERE sequence=?",
        (json.dumps(body), sequence),
    )
    db.commit()
    db.close()

    health = owner_bridge.served_pin_health(tmp_path)
    receipt = health["lived_chain"]
    assert receipt["head"] is None
    assert receipt["head"] != walked
    assert receipt["entry_count"] == 0
    assert "ab" * 32 not in json.dumps(receipt)


def test_absent_chain_publishes_no_invented_head(tmp_path, monkeypatch):
    monkeypatch.setattr(rawrphos_local, "status", lambda: {"readiness": "OFFLINE_OR_DISCONNECTED"})
    health = owner_bridge.served_pin_health(tmp_path)
    assert health["lived_chain"] == {"head": None, "entry_count": 0, "subject_id": None}
    assert health["pin_step"] == rawrphos_local.STEP
    assert health["pin_checkpoint_sha256"] == rawrphos_local.SHA
