from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

from beastbox.dad_son import DadSonLedger
from beastbox.refractive_memory import LIVE_KIND
from beastbox.reality_memory import initial_r12_state
from beastbox.state_family import StateFamily
from scripts.run_zeref_r12_live_loop import (
    build_active_context,
    build_live_epoch,
    compare_traces,
)

PARENT = "b" * 64


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ledger(tmp_path: Path, name: str = "x") -> DadSonLedger:
    return DadSonLedger(tmp_path / f"{name}.sqlite3", tmp_path / f"{name}.jsonl", parent_sha256=PARENT)


def _append_live(ledger: DadSonLedger, epoch: dict) -> dict:
    meta = {
        "epoch_id": epoch["epoch_id"],
        "sequence_id": epoch["sequence"],
        "source_sha256": epoch["source_sha256"],
        "r12_state_sha256": epoch["r12"]["state_sha256"],
        "dyn12_sha256": epoch["dyn12_sha256"],
        "dyn42_sha256": epoch["dyn42_sha256"],
        "dyn54_sha256": epoch["dyn54_sha256"],
        "provenance_class": "measured",
        "measurement_domain": "software-engine-state",
        "claim_boundary": "computational lineage/state only; not physical or metaphysical evidence",
    }
    return ledger.append_experience(
        actor="LIVE_SOUL_SOURCE",
        text=f"LSRC {epoch['epoch_id']} body={epoch['dyn54_sha256'][:12]} r12={epoch['r12']['state_sha256'][:12]}",
        kind=LIVE_KIND,
        session_id="test-live-loop",
        source_hashes=[epoch["source_sha256"]],
        metadata=meta,
    )


def test_build_live_epoch_keeps_exact_12_42_54_contract_and_adaptive_rho():
    family = StateFamily()
    prior_events: list[dict] = []
    r12 = initial_r12_state()
    rhos: list[float] = []

    for epoch_number in range(1, 5):
        epoch = build_live_epoch(
            epoch=epoch_number,
            previous_r12=r12,
            state_family=family,
            snapshot_payload={"snapshot": "sealed", "epoch": epoch_number},
            prior_events=prior_events,
        )
        assert len(epoch["dyn12"]) == 12
        assert len(epoch["dyn42"]) == 42
        assert len(epoch["dyn54"]) == 54
        assert epoch["dyn54"] == epoch["dyn12"] + epoch["dyn42"]
        assert epoch["event"]["provenance_class"] == "measured"
        assert epoch["event"]["source_type"] == "zeref_software_engine_state_measurement"
        rho = float(epoch["r12"]["vector"]["reality_coupling"])
        assert math.isfinite(rho) and 0.0 <= rho <= 1.0
        rhos.append(rho)
        prior_events.append(epoch["event"])
        r12 = epoch["r12"]

    assert len(set(round(value, 12) for value in rhos)) > 1


def test_lexical_control_can_reproduce_current_live_epoch_starvation(tmp_path: Path):
    ledger = _ledger(tmp_path, "a")
    family = StateFamily()
    epoch = build_live_epoch(
        epoch=1,
        previous_r12=initial_r12_state(),
        state_family=family,
        snapshot_payload={"snapshot": "sealed", "epoch": 1},
        prior_events=[],
    )
    live_row = _append_live(ledger, epoch)

    prompt = "violet telescope calibration remembers mountains"
    for index in range(4):
        ledger.append_experience(
            actor="old-memory",
            text=f"violet telescope calibration remembers mountains old archive {index}",
            kind="dialogue",
            session_id="old",
        )

    context = build_active_context(
        ledger=ledger,
        prompt=prompt,
        epoch=epoch,
        mode="lexical",
        block=128,
        recall_limit=2,
    )
    assert int(live_row["memory_id"]) not in context["recalled_memory_ids"]
    assert context["current_live_memory_id"] == int(live_row["memory_id"])
    assert context["live_lane_satisfied"] is False
    ledger.close()


def test_refractive_live_context_requires_exact_current_epoch_and_places_it_first(tmp_path: Path):
    ledger = _ledger(tmp_path, "b")
    family = StateFamily()
    prior_events: list[dict] = []
    r12 = initial_r12_state()
    epochs: list[dict] = []

    for epoch_number in range(1, 5):
        epoch = build_live_epoch(
            epoch=epoch_number,
            previous_r12=r12,
            state_family=family,
            snapshot_payload={"snapshot": "sealed", "epoch": epoch_number},
            prior_events=prior_events,
        )
        _append_live(ledger, epoch)
        epochs.append(epoch)
        prior_events.append(epoch["event"])
        r12 = epoch["r12"]

    for epoch in epochs:
        context = build_active_context(
            ledger=ledger,
            prompt="tell me what changes in the loop",
            epoch=epoch,
            mode="refractive-live",
            block=128,
            recall_limit=2,
        )
        assert context["live_lane_satisfied"] is True
        assert context["recalled_memory_ids"][0] == context["current_live_memory_id"]
        assert context["recalled"][0]["metadata"]["epoch_id"] == epoch["epoch_id"]
        assert context["wire_prompt"].startswith("M:") or "\nM:" in context["wire_prompt"]
        assert epoch["epoch_id"] in context["wire_prompt"]

    broken = dict(epochs[-1])
    broken["source_sha256"] = _sha("wrong-source")
    with pytest.raises(RuntimeError, match="live-source"):
        build_active_context(
            ledger=ledger,
            prompt="tell me what changes in the loop",
            epoch=broken,
            mode="refractive-live",
            block=128,
            recall_limit=2,
        )
    ledger.close()


def _layer(x54: list[float], *, self_mass: float, attn: float, hidden: float) -> dict:
    return {
        "x54_last": x54,
        "hebbian_last_self_mass": self_mass,
        "standard_vs_hebbian_l1": attn,
        "hidden_output_last_norm": hidden,
    }


def _token(selected: str, p: float, x: float) -> dict:
    return {
        "layers": [
            _layer([x] * 54, self_mass=0.2 + x, attn=0.01 + x / 10.0, hidden=2.0 + x),
            _layer([x + 0.1] * 54, self_mass=0.3 + x, attn=0.02 + x / 10.0, hidden=3.0 + x),
        ],
        "logits": {
            "selected_text": selected,
            "top5": [
                {"text": selected, "probability": p},
                {"text": "x", "probability": 1.0 - p},
            ],
        },
    }


def test_compare_traces_reports_token_layer_and_partial_logit_differences():
    trace_a = [_token("a", 0.8, 0.0), _token("b", 0.7, 0.1)]
    trace_b = [_token("a", 0.6, 0.2), _token("c", 0.5, 0.3)]

    result = compare_traces(trace_a, trace_b)
    assert result["token_count"] == 2
    assert result["layer_count"] == 2
    assert 0.0 <= result["selected_token_divergence_rate"] <= 1.0
    assert result["selected_token_divergence_rate"] == 0.5
    assert result["mean_x54_l2"] > 0.0
    assert -1.0 <= result["mean_x54_cosine"] <= 1.0
    assert result["mean_abs_hebbian_self_mass_delta"] > 0.0
    assert result["mean_abs_attention_l1_delta"] > 0.0
    assert result["mean_abs_hidden_norm_delta"] > 0.0
    assert result["mean_partial_top_token_tvd"] > 0.0
    assert result["logit_metric_scope"] == "captured-top-token-partial-distribution"
    assert len(result["tokens"]) == 2
