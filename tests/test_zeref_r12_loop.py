from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_zeref_r12_reality_loop import ProcessLock, build_reality_context, rebuild_runtime, run_once


HW_DIR = Path("experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/hardware/run-32611912698")


def test_once_then_rebuild_preserves_state_hash_and_compact_retrieval(tmp_path):
    root = tmp_path / "r12"
    first = run_once(
        hw_dir=HW_DIR,
        root=root,
        source_created_at_utc="2026-08-23T02:04:13Z",
        query="Which backend and condition were measured?",
    )
    second = run_once(
        hw_dir=HW_DIR,
        root=root,
        source_created_at_utc="2026-08-23T02:04:13Z",
        query="Which backend and condition were measured?",
    )
    before = json.loads((root / "state/r12-state.json").read_text())
    rebuilt = rebuild_runtime(root=root, query="Which backend and condition were measured?")
    after = json.loads((root / "state/r12-state.json").read_text())

    assert first["appended_events"] == 4
    assert second["appended_events"] == 0
    assert rebuilt["event_count"] == 4
    assert before["state_sha256"] == after["state_sha256"]

    context = build_reality_context(
        ledger_path=root / "ledger/reality-events.jsonl",
        state_path=root / "state/r12-state.json",
        query="IBM Fez ORIGINAL",
        max_chars=700,
    )
    assert "R12" in context
    assert "ibm_fez" in context
    assert "ORIGINAL" in context
    assert "reality_coupling" in context
    assert '"counts"' not in context
    assert len(context) <= 700


def test_process_lock_refuses_second_writer(tmp_path):
    lock_path = tmp_path / "r12.lock"
    with ProcessLock(lock_path):
        with pytest.raises(RuntimeError, match="locked"):
            with ProcessLock(lock_path):
                pass
