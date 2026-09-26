"""Stage 013 provenance, 12D context and complete-case scoring tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from beastbox.qvm_cpu_comparison_013 import ARMS, create_plan, score

RECEIPT = Path(__file__).resolve().parents[1] / "evidence/stage012/live_azure_qvm_3job_public_receipt.json"


def _receipt():
    return json.loads(RECEIPT.read_text())


def test_fixed_blind_plan_is_repeatable_and_does_not_leak_heldout_job():
    first = create_plan(_receipt())
    second = create_plan(_receipt())
    assert first == second
    assert first["cases"] == 15
    assert set(first["arms"]) == set(ARMS)
    assert first["trials"] == 3
    assert first["no_new_provider_quantum_jobs"] is True
    assert first["zero_model_api_calls"] is True
    key = first["private_scoring_key_NEVER_SENT_TO_MODEL"]
    public = first["public_model_inputs"]
    assert len(key) == len(public) == 15
    assert len({row["id"] for row in public}) == 15
    assert all(row["id"] in key for row in public)
    for case in public:
        meta = key[case["id"]]
        assert meta["heldout_job"] not in case["prompt"]
        assert "private_scoring_key" not in case["prompt"]
        assert "your OWN three-decimal numerical calculation" in case["prompt"]
        assert "p11=0.123" not in case["prompt"]
        assert len(case["prompt"]) <= 2400
        assert case["prompt"].count("Target theta radians:") == 1
    assert sum(row["prompt"].count("auxiliary_software_state_12d") for row in public) == 9
    assert sum(row["prompt"].count("prior_cloud_QVM_simulations_not_hardware") for row in public) == 12


def test_controls_use_same_priors_and_heldout_truth_is_not_embedded_in_state():
    plan = create_plan(_receipt())
    key = plan["private_scoring_key_NEVER_SENT_TO_MODEL"]
    for trial in (1, 2, 3):
        cases = {key[row["id"]]["arm"]: row["prompt"] for row in plan["public_model_inputs"]
                 if key[row["id"]]["trial"] == trial}
        assert set(cases) == set(ARMS)
        assert "Additional external DATA" not in cases["baseline"]
        assert "auxiliary_software_state_12d" not in cases["memory_only"]
        assert "auxiliary_software_state_12d" in cases["conditioned"]
        assert "auxiliary_software_state_12d" in cases["order_control"]
        assert "auxiliary_software_state_12d" in cases["classical_matched"]


def test_complete_prescored_answers_all_cases_without_artificial_gains():
    plan = create_plan(_receipt())
    outputs = [
        {"id":key,"text":f"p11={meta['answer']:.3f}; hardware=no"}
        for key,meta in plan["private_scoring_key_NEVER_SENT_TO_MODEL"].items()
    ]
    result = score(plan,outputs)
    assert result["number_of_model_calls"] == 15
    assert set(result["results_unranked_by_arm"]) == set(ARMS)
    assert all(arm["valid_answers"] == 3 for arm in result["results_unranked_by_arm"].values())
    assert all(arm["hardware_correct"] == 3 for arm in result["results_unranked_by_arm"].values())
    assert all(arm["MAE_including_invalid_penalty"] < .001 for arm in result["results_unranked_by_arm"].values())
    tampered = copy.deepcopy(outputs)
    tampered[0]["id"] = "T00"
    with pytest.raises(ValueError):
        score(plan,tampered)
    partial = [{"id":key,"text":"I cannot complete"} for key in plan["private_scoring_key_NEVER_SENT_TO_MODEL"]]
    invalid = score(plan,partial)
    assert all(arm["MAE_including_invalid_penalty"] == 1.0 for arm in invalid["results_unranked_by_arm"].values())


def test_reject_wrong_source_integrity_and_bad_random_seed():
    source = _receipt()
    wrong = copy.deepcopy(source)
    wrong["target"] = "rigetti.qpu"
    with pytest.raises(ValueError):
        create_plan(wrong)
    with pytest.raises(ValueError):
        create_plan(source, seed=-1)
