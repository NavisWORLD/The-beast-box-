from __future__ import annotations

import hashlib

from scripts.run_zeref_snapshot_dialogue import (
    ACTIVE_TALK4_SHA256,
    SNAPSHOT_FACTS,
    build_snapshot_digest54,
    validate_snapshot_facts,
)


def test_snapshot_bundle_preserves_evidence_boundaries() -> None:
    validate_snapshot_facts(SNAPSHOT_FACTS)
    by_id = {row["id"]: row for row in SNAPSHOT_FACTS}

    assert by_id["probe005"]["verdict"] == "INCONCLUSIVE"
    assert by_id["probe005"]["anomaly_candidate"] is False
    assert by_id["cns7-v1"]["formal_status"] == "INCOMPLETE"
    assert by_id["cns7-v1"]["replacement_jobs"] == 0
    assert by_id["cns7-v2"]["hardware_result_status"] == "QUEUED_AT_LAST_VERIFIED_SCAN"
    assert by_id["rigetti"]["hardware_results_collected"] is False
    assert by_id["hypothesis"]["established_fact"] is False


def test_snapshot_digest_is_deterministic_54d_and_bounded() -> None:
    a = build_snapshot_digest54(SNAPSHOT_FACTS)
    b = build_snapshot_digest54(SNAPSHOT_FACTS)
    assert a == b
    assert len(a["vector54"]) == 54
    assert all(-1.0 <= x <= 1.0 for x in a["vector54"])
    assert len(a["bundle_sha256"]) == 64
    assert a["bundle_sha256"] == hashlib.sha256(a["canonical_json"].encode("utf-8")).hexdigest()


def test_active_checkpoint_is_exact_talk004_selected_child() -> None:
    assert ACTIVE_TALK4_SHA256 == "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
