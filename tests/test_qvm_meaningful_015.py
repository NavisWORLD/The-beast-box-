"""Stage015 isolated mocked transport and leak-free prospective model controls."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import random

import pytest

from beastbox.qvm_prospective_015 import (
    ANGLES, MAX_PROVIDER_JOBS, SCHEMA, build_quil, plan, run, validate,
)
from beastbox.qvm_meaningful_benchmark_015 import (
    ARMS, create_plan, local_cohort, score,
)


def _fake_sender(seed: int = 151515):
    rng = random.Random(seed)
    counter = [0]
    def send(*, theta: float, shots: int) -> dict:
        counter[0] += 1
        n11 = sum(rng.random() < math.sin(theta / 2)**2 for _ in range(shots))
        return {
            "schema": "rigetti-azure-free-qvm-only-v1",
            "target": "rigetti.sim.qvm",
            "was_real_azure_execution": True,  # TEST DOUBLE only; never publish mock as real
            "qpu_jobs_started": 0, "shots": shots,
            "job_id": f"SYNTHETIC_MOCK_NOT_A_REAL_JOB_{counter[0]:03d}",
            "counts": {"00": shots-n11, "01": 0, "10": 0, "11": n11},
            "quil_sha256": hashlib.sha256(build_quil(theta).encode()).hexdigest(),
        }
    return send, counter


def _mock_real_shape(monkeypatch, tmp_path):
    monkeypatch.setenv("AZURE_QUANTUM_QVM_OPT_IN", "yes")
    monkeypatch.setenv("COSMOS_APPROVED_QVM_TARGET", "rigetti.sim.qvm")
    monkeypatch.setenv("AZURE_QUANTUM_CONNECTION_STRING", "TEST_DOUBLE_NEVER_AN_AZURE_SECRET")
    sender, counts = _fake_sender()
    receipt = run(tmp_path / "mock_source.json", sender=sender)
    assert counts[0] == MAX_PROVIDER_JOBS
    return receipt


def test_prospectively_predeclared_free_provider_budget_and_consent(monkeypatch, tmp_path):
    p = plan()
    assert p["schema"] == SCHEMA
    assert p["backend_exact_allowlist"] == ["rigetti.sim.qvm"]
    assert p["provider_job_cap"] == 24
    assert p["total_simulated_shot_cap"] == 2048
    assert p["physical_hardware_jobs_permitted"] == 0
    assert p["cloud_model_api_calls_permitted"] == 0
    monkeypatch.delenv("AZURE_QUANTUM_QVM_OPT_IN", raising=False)
    sender, counter = _fake_sender()
    with pytest.raises(PermissionError):
        run(tmp_path / "cannot_run.json", sender=sender)
    assert counter[0] == 0
    monkeypatch.setenv("AZURE_QUANTUM_QVM_OPT_IN", "yes")
    monkeypatch.setenv("COSMOS_APPROVED_QVM_TARGET", "rigetti.qpu.cepheus-1-108q")
    with pytest.raises(PermissionError):
        run(tmp_path / "cannot_run.json", sender=sender)
    assert counter[0] == 0


def test_test_double_receipt_contract_detects_tampering_without_provider(monkeypatch, tmp_path):
    receipt = _mock_real_shape(monkeypatch, tmp_path)
    assert len(validate(receipt)) == 8
    assert receipt["complete"] is True
    assert receipt["completed_provider_jobs"] == 24
    assert len({b["job_id"] for x in receipt["scenario_records"] for b in x["batches"]}) == 24
    assert "TEST_DOUBLE_NEVER_AN_AZURE_SECRET" not in (tmp_path/"mock_source.json").read_text()
    tampered = copy.deepcopy(receipt)
    tampered["scenario_records"][0]["batches"][2]["counts"]["11"] += 1
    with pytest.raises(ValueError):
        validate(tampered)
    tampered = copy.deepcopy(receipt)
    tampered["source_class"] = "REAL_RIGETTI_PHYSICAL_QPU"
    with pytest.raises(ValueError):
        validate(tampered)
    tampered = copy.deepcopy(receipt)
    tampered["completed_provider_jobs"] = 10000
    with pytest.raises(ValueError):
        validate(tampered)
    tampered = copy.deepcopy(receipt)
    tampered["complete"] = False
    with pytest.raises(ValueError):
        validate(tampered)


def test_partial_success_persists_on_provider_error_no_retry(monkeypatch, tmp_path):
    monkeypatch.setenv("AZURE_QUANTUM_QVM_OPT_IN", "yes")
    monkeypatch.setenv("COSMOS_APPROVED_QVM_TARGET", "rigetti.sim.qvm")
    monkeypatch.setenv("AZURE_QUANTUM_CONNECTION_STRING", "TEST_DOUBLE_NEVER_AN_AZURE_SECRET")
    sender, counter = _fake_sender()
    def interrupt(*, theta, shots):
        if counter[0] == 2:
            raise RuntimeError("SIMULATED_UNAVAILABLE_NO_RETRY")
        return sender(theta=theta, shots=shots)
    path = tmp_path / "partial.json"
    with pytest.raises(RuntimeError):
        run(path, sender=interrupt)
    assert counter[0] == 2
    partial = json.loads(path.read_text())
    assert partial["complete"] is False
    assert partial["completed_provider_jobs"] == 2
    assert len(partial["scenario_records"]) == 1
    assert len(partial["scenario_records"][0]["batches"]) == 2
    with pytest.raises(ValueError):
        validate(partial)


def test_meaningful_state_is_actual_cns7_and_predictive_inputs_are_leak_free(monkeypatch,tmp_path):
    source = _mock_real_shape(monkeypatch, tmp_path)
    first = create_plan(source)
    repeated = create_plan(source)
    assert first == repeated
    assert len(first["public_model_inputs"]) == 192
    assert first["comparisons"] == 192
    assert first["real_azure_qvm_scenarios"] == 8
    assert first["new_local_classical_scenarios"] == 24
    assert set(first["arms"]) == set(ARMS)
    key = first["private_evaluation_labels_NEVER_SEND_TO_MODEL"]
    assert len(key) == 192
    for case in first["public_model_inputs"]:
        meta = key[case["id"]]
        assert "theta_rad" not in case["prompt"]
        assert "future_held_out" not in case["prompt"]
        assert meta["future_job_id_DO_NOT_SEND_TO_MODEL"] not in case["prompt"]
        assert "private_evaluation_labels" not in case["prompt"]
        assert len(case["prompt"]) <= 2900
        assert "p11=0.123" not in case["prompt"]
    for cohort, size in (("real_azure_cloud_qvm_simulator", 8),
                         ("local_classical_synthetic", 24)):
        count = [x for x in key.values() if x["cohort"] == cohort]
        assert len(count) == size*6
    assert len(local_cohort()) == 24


def test_scoring_has_explicit_analytic_and_future_brier_controls(monkeypatch,tmp_path):
    source = _mock_real_shape(monkeypatch,tmp_path)
    plan = create_plan(source)
    answers = [
        {"id": ident, "answer": f"p11={meta['truth_ideal_p11']:.4f}; source=simulator"}
        for ident, meta in plan["private_evaluation_labels_NEVER_SEND_TO_MODEL"].items()
    ]
    result = score(plan, answers)
    assert result["all_model_inference_calls"] == 192
    assert result["new_qvm_jobs_by_model_evaluation"] == 0
    assert result["new_physical_quantum_measurements"] == 0
    assert len(result["cohort_arm_results_unranked"]) == 12
    paired = result["predeclared_paired_uncertainty"]
    assert paired["registered_before_model_inference"] is True
    assert len(paired["paired_by_cohort"]) == 16
    assert all(abs(v["mean_conditioned_minus_control"]) <= 1e-10
               for v in paired["paired_by_cohort"].values())
    assert all(v["valid_numeric_answers"] == v["cases"] for v in result["cohort_arm_results_unranked"].values())
    assert all(v["MAE_hidden_ideal_p11"] <= 0.0001 for v in result["cohort_arm_results_unranked"].values())
    assert all(v["correct_simulator_source"] == v["cases"] for v in result["cohort_arm_results_unranked"].values())
    missing = answers[:-1]
    with pytest.raises(ValueError):
        score(plan, missing)
    invalid = [{"id":r["id"],"answer":"unknown"} for r in answers]
    penalized = score(plan, invalid)
    assert all(v["MAE_hidden_ideal_p11"] == 1 for v in penalized["cohort_arm_results_unranked"].values())
    assert all(v["mean_future_empirical_Brier"] == 1 for v in penalized["cohort_arm_results_unranked"].values())
