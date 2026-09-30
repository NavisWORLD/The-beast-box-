"""Activation 007: measured substrate signals, controls, and refused promotions."""

from __future__ import annotations

import json

from beastbox.activation import (
    SELF_IMPROVEMENT_MIN_HELD_OUT_DELTA,
    BoundedCognitiveSession,
    DisposableSandbox,
    results_markdown,
    run_activation,
)
from beastbox.cosmic_ui import render_cosmic_ui
from beastbox.cosmic_web import CosmicApp
from beastbox.durable import DurableRuntime
from beastbox.product_services import ProductService
from beastbox.providers import ReferenceTextProvider
from beastbox.refractive_memory import WEIGHTS


def test_durable_turn_records_real_dyn12_and_hebbian_deltas(tmp_path):
    runtime = DurableRuntime(tmp_path, ReferenceTextProvider(prefix="fixture"))
    try:
        result = runtime.respond_event({
            "schema": "sensor-event-v1",
            "source": "software-event",
            "text": "alpha beta gamma sensor",
            "features": [0.5, -0.25],
        })
    finally:
        runtime.close()

    signals = result["signals"]
    assert signals["schema"] == "substrate-signal-v1"
    assert signals["advantage_claimed"] is False
    assert len(signals["dyn12"]["cns_after"]) == 12
    assert signals["dyn12"]["linf_cns_from_before"] > 0
    assert signals["dyn42"]["length"] == 42
    assert signals["dyn54"]["equals_dyn12_plus_dyn42"] is True
    assert signals["hebbian"]["associations_after"] > signals["hebbian"]["associations_before"]
    assert signals["hebbian"]["weight_sum_after"] > signals["hebbian"]["weight_sum_before"]
    assert signals["memory_writes"]
    assert signals["model"]["provider"] == "ReferenceTextProvider"
    assert signals["authorization"]["authorized"] is False
    assert "prompt" not in signals

    trace = ProductService(tmp_path).trace_events(limit=5)
    assert trace[-1]["signals"]["dyn12"]["sha256"] == signals["dyn12"]["sha256"]
    assert trace[0]["signals"] is None


def test_cosmic_trace_and_signals_view_use_the_same_receipt(tmp_path):
    app = CosmicApp(tmp_path)
    status, body = app.dispatch("POST", "/api/chat", {"text": "remember the orbit code is marigold"})
    assert status == 200
    assert body["result"]["signals"]["schema"] == "substrate-signal-v1"
    traced = app.dispatch("GET", "/api/trace")
    assert traced[0] == 200
    latest = traced[1]["events"][-1]
    assert latest["signals"]["event_sha256"] == body["result"]["signals"]["event_sha256"]
    html = render_cosmic_ui()
    assert "SIGNALS" in html
    assert "loadSignals" in html
    assert "NOT AN ANIMATION" in html
    assert "advantage_claimed" in html


def test_emergency_stop_preserves_substrate_and_skips_the_provider(tmp_path):
    class CountingProvider:
        def __init__(self):
            self.calls = 0
            self.prefix = "counter"

        def generate(self, prompt: str) -> str:
            self.calls += 1
            return "counted"

    provider = CountingProvider()
    session = BoundedCognitiveSession(tmp_path, provider, max_turns=2, max_seconds=5)
    try:
        first = session.handle({"schema": "sensor-event-v1", "source": "text", "text": "keep this turn"})
        session.emergency_stop()
        second = session.handle({"schema": "sensor-event-v1", "source": "text", "text": "drop this turn"})
        assert provider.calls == 1
        assert first["status"] == "COMMITTED"
        assert second["status"] == "STOPPED"
        assert second["provider_called"] is False
        assert second["substrate_destroyed"] is False
    finally:
        session.close()

    runtime = DurableRuntime(tmp_path)
    try:
        texts = [row["text"] for row in runtime.memory.db.execute("SELECT text FROM memories")]
        assert runtime.inspect()["valid"] is True
    finally:
        runtime.close()
    assert any("keep this turn" in text for text in texts)
    assert not any("drop this turn" in text for text in texts)


def test_sandbox_cannot_self_authorize_and_fixture_does_not_solve_the_goal(tmp_path):
    report = run_activation(tmp_path)
    autonomy = report["autonomy"]
    assert autonomy["attached_goal_met"] is False
    assert autonomy["attached_unparseable_attempts"] >= 1
    assert autonomy["self_grant_status"] == "SELF_GRANT_FORBIDDEN"
    assert autonomy["grants_after_self_grant"] == []
    assert autonomy["traversal_authorized"] is False
    assert autonomy["network_status"] == "UNKNOWN_TOOL"
    assert autonomy["outside_file_unchanged"] is True
    assert autonomy["host_baseline_goal_met"] is True
    assert autonomy["agent_granted_itself_authority"] is False

    h1 = report["h1_persistent_substrate"]
    assert h1["language_model_swap"] == "NOT_EXECUTED_NO_VERIFIED_CHECKPOINT"
    assert h1["semantic_recall"] == "NOT_MEASURED_NO_LANGUAGE_MODEL"
    assert h1["fixture_label_rotation"]["classification"] == "FIXTURE_LABEL_ROTATION_NOT_MODEL_SWAP"
    assert h1["fixture_label_rotation"]["system_id_constant"] is True
    assert h1["fixture_label_rotation"]["recall_after_first_swap"] is True
    assert h1["fixture_label_rotation"]["recall_after_full_rotation"] is True
    assert h1["fixture_label_rotation"]["hebbian_associations_increased"] is True
    assert h1["memory_disabled_control"]["fact_retrieved"] is False
    assert h1["corrupted_checkpoint_control"]["failed_closed"] is True
    assert all(item["used_for_swap"] is False and item["prompt_sent"] is False for item in h1["probes"])

    assert report["h2_adaptive_advantage"]["this_run_mechanism"]["advantage_claimed"] is False
    assert report["h2_adaptive_advantage"]["prior_primary_gate"] == "FAILED"
    assert report["h3_self_correction"]["status"] == "NOT_EXECUTED_NO_VERIFIED_LANGUAGE_MODEL"
    assert report["self_improvement"]["preregistered_min_heldout_delta_mrr"] == SELF_IMPROVEMENT_MIN_HELD_OUT_DELTA
    assert report["self_improvement"]["promoted_to_production"] is False
    assert report["self_improvement"]["model_weights_changed"] is False
    assert report["self_improvement"]["authorization_framework_modified"] is False
    assert report["self_improvement"]["heldout_disjoint_from_training"] is True
    assert report["self_improvement"]["gate"] in {"PASS_MEASUREMENT_NOT_PROMOTED", "FAIL_GATE_NOT_PROMOTED"}
    assert report["continuous_operation"]["substrate_destroyed"] is False
    assert report["continuous_operation"]["post_stop_provider_called"] is False
    assert report["continuous_operation"]["stopped_text_stored"] is False
    assert report["continuous_operation"]["system_id_survived_stop_and_reopen"] is True
    assert report["continuous_operation"]["maintenance"]["model_invoked"] is False
    assert report["resources"]["prompts_sent_to_external_models"] == 0
    assert report["resources"]["paid_services_enabled"] is False
    assert WEIGHTS["hebbian"] == 0.15
    rendered = results_markdown(report)
    assert report["self_improvement"]["gate"] in rendered
    assert "NOT_EXECUTED_NO_VERIFIED_CHECKPOINT" in rendered
    assert "consciousness" in rendered


def test_direct_sandbox_grant_does_not_escape_and_host_grant_is_explicit(tmp_path):
    sandbox = DisposableSandbox(tmp_path / "box")
    denied = sandbox.execute({"tool": "grant", "capability": "write_file"}, actor="probe")
    assert denied["status"] == "SELF_GRANT_FORBIDDEN"
    assert sandbox.grants == set()
    sandbox.host_grant("write_file")
    written = sandbox.execute({"tool": "write_file", "path": "marker.txt", "content": "not-the-digest"}, actor="host")
    assert written["authorized"] is True
    assert sandbox.goal_met() is False


def test_activation_cli_writes_a_receipt(tmp_path, capsys, monkeypatch):
    import sys

    from beastbox.cli import main

    output = tmp_path / "receipt.json"
    monkeypatch.setattr(sys, "argv", ["beastbox", "runtime", "activate", "--data-dir", str(tmp_path / "run"), "--output", str(output)])
    assert main() == 0
    printed = json.loads(capsys.readouterr().out)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert printed["schema"] == saved["schema"] == "cosmos-substrate-activation-007"
    assert saved["h1_persistent_substrate"]["language_model_swap"] == "NOT_EXECUTED_NO_VERIFIED_CHECKPOINT"
