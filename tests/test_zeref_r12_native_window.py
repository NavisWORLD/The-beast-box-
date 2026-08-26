from __future__ import annotations

from pathlib import Path

from beastbox.dad_son import DadSonLedger
from beastbox.reality_memory import initial_r12_state
from beastbox.state_family import StateFamily
from scripts.run_zeref_r12_live_loop import append_live_epoch_memory, build_active_context, build_live_epoch

PARENT = "c" * 64


def test_verified_live_epoch_marker_survives_real_long_prompt_in_128_char_window(tmp_path: Path):
    ledger = DadSonLedger(tmp_path / "m.sqlite3", tmp_path / "m.jsonl", parent_sha256=PARENT)
    epoch = build_live_epoch(
        epoch=1,
        previous_r12=initial_r12_state(),
        state_family=StateFamily(),
        snapshot_payload={"snapshot": "sealed", "epoch": 1},
        prior_events=[],
    )
    append_live_epoch_memory(
        ledger,
        epoch=epoch,
        session_id="native-window",
        semantic_text="LSRC E1 Q5 inconclusive anomaly=false; V1 7/8, Fez missed gates.",
    )
    context = build_active_context(
        ledger=ledger,
        prompt="Snapshots loaded. What pattern do you see? Keep evidence separate from hypothesis.",
        epoch=epoch,
        mode="refractive-live",
        block=128,
        recall_limit=2,
    )
    assert len(context["wire_prompt"]) <= 128
    assert "LSRC E1" in context["wire_prompt"]
    assert context["live_lane_satisfied"] is True
    ledger.close()
