"""OMEGA operator, sandbox, experiments, recovery."""
import pytest

from beastbox.omega.experiments import (
    run_h1_model_independence,
    run_h2_adaptive_advantage,
    run_h3_self_correction,
)
from beastbox.omega.operator import OmegaBudgets, OmegaOperator
from beastbox.omega.recovery import recover_substrate_map
from beastbox.omega.sandbox import OmegaSandbox, SandboxDenied
from beastbox.omega.self_improve import SelfImprovementRig
from beastbox.providers import ReferenceTextProvider


def test_operator_queue_budgets_estop(tmp_path):
    op = OmegaOperator(
        tmp_path / "op", provider=ReferenceTextProvider(prefix="OP-A"),
        budgets=OmegaBudgets(max_steps=5, max_ms=30_000.0),
    )
    try:
        op.submit({"schema": "sensor-event-v1", "source": "text", "text": "event one"})
        op.submit({"schema": "sensor-event-v1", "source": "text", "text": "event two"})
        snap = op.run_until_empty()
        assert snap["steps"] == 2
        stopped = op.emergency_stop()
        assert stopped["status"] == "estop"
        # Substrate survives the stop.
        assert stopped["inspection"]["memory"]["memories"] >= 2
        with pytest.raises(RuntimeError):
            op.submit({"schema": "sensor-event-v1", "source": "text", "text": "late event"})
    finally:
        op.close()


def test_sandbox_boundaries(tmp_path):
    box = OmegaSandbox(tmp_path / "box", approve=lambda p: p["argv"][0] == "echo")
    ok = box.propose({"argv": ["echo", "hello"]})
    assert ok["approved"] is True and ok["executed"] is True and ok["returncode"] == 0
    denied = box.propose({"argv": ["cat", "OBJECTIVE.md"]})
    assert denied["approved"] is False and denied["executed"] is False
    with pytest.raises(SandboxDenied):
        OmegaSandbox(tmp_path / "box2", approve=lambda p: True).propose({"argv": ["curl", "http://x"]})
    net = box.network_attempt()
    assert net["allowed"] is False


def test_h1_h2_h3_execute_with_verdicts(tmp_path):
    h1 = run_h1_model_independence(tmp_path / "h1", seeds=1)
    assert h1["schema"] == "omega-h1-v1" and h1["verdict"] in ("PASS", "FAIL")
    h2 = run_h2_adaptive_advantage()
    assert set(h2["means"]) == {"dyn12", "standard", "shuffled", "static"}
    assert h2["verdict"] in ("PASS", "FAIL")
    h3 = run_h3_self_correction()
    assert h3["verdict"] in ("PASS", "FAIL")
    assert "leak" in h3["interpretation"].lower() or "evaluator" in h3["interpretation"].lower()


def test_recovery_map_marks_core_connected():
    m = recover_substrate_map(".")
    by_id = {c["id"]: c for c in m["components"]}
    for cid in ("dyn12", "cns7", "hebbian", "sensors", "synapse", "r12"):
        assert by_id[cid]["state"] == "CONNECTED", cid


def test_self_improve_forbids_authority_edits(tmp_path):
    rig = SelfImprovementRig(".", tmp_path / "work")
    rig.checkpoint_baseline()
    with pytest.raises(PermissionError):
        rig.propose({"beastbox/box.py": "evil"})
    with pytest.raises(PermissionError):
        rig.propose({"note.py": "x = allowed.add('EVERYTHING')"})
    res = rig.evaluate(["w1", "w2"], evaluator=lambda variant, w: 1.0 if variant == "baseline" else 0.0)
    assert res["promoted"] is False
    assert res["improved_on_heldout"] is False
    rb = rig.rollback()
    assert rb["rolled_back"] is True
