from __future__ import annotations

import json
from pathlib import Path

from beastbox.reality_memory import RealityLedger, sha256_json
from scripts.import_zeref_r12_fez import CONDITIONS, import_verified_fez_block, load_verified_fez_block


HW_DIR = Path("experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/hardware/run-32611912698")


def test_real_fez_block_loads_full_verified_counts():
    rows = load_verified_fez_block(HW_DIR)
    assert [row["condition"] for row in rows] == list(CONDITIONS)
    assert {row["backend"] for row in rows} == {"ibm_fez"}
    assert {row["job_id"] for row in rows} == {"da55afc3jnrc73agsvv0"}
    for row in rows:
        assert row["shot_count"] == 4096
        assert sum(row["counts"].values()) == 4096
        assert row["counts_sha256"] == sha256_json(dict(sorted(row["counts"].items())))
        assert len(row["packet_sha256"]) == 64
        assert len(row["origin_seed_sha256"]) == 64


def test_import_is_idempotent_and_writes_rebuildable_state(tmp_path):
    root = tmp_path / "reality-memory"
    kwargs = {
        "hw_dir": HW_DIR,
        "ledger_path": root / "ledger/reality-events.jsonl",
        "state_path": root / "state/r12-state.json",
        "history_path": root / "state/r12-history.jsonl",
        "manifest_path": root / "manifest.json",
        "source_created_at_utc": "2026-08-23T02:04:13Z",
    }
    first = import_verified_fez_block(**kwargs)
    second = import_verified_fez_block(**kwargs)

    assert first["appended_events"] == 4
    assert second["appended_events"] == 0
    ledger = RealityLedger(kwargs["ledger_path"])
    assert ledger.verify()["event_count"] == 4
    assert len(kwargs["history_path"].read_text().splitlines()) == 4

    manifest = json.loads(kwargs["manifest_path"].read_text())
    state = json.loads(kwargs["state_path"].read_text())
    assert manifest["event_count"] == 4
    assert manifest["measured_event_count"] == 4
    assert manifest["new_ibm_job_submitted"] is False
    assert manifest["active_checkpoint_sha256"] == "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
    assert manifest["durable_memory_record_count"] == 352
    assert state["sequence"] == 4
    assert len(state["vector"]) == 12
