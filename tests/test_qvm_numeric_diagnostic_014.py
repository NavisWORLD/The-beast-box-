"""Fixed Stage 014 parsing contract; Stage 013 remains immutable."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from beastbox.qvm_cpu_comparison_013 import create_plan, score
from beastbox.qvm_numeric_diagnostic_014 import (
    analyze_prior_model_receipt, evaluate, public_input_digest,
)

SOURCE = Path(__file__).resolve().parents[1]/"evidence/stage012/live_azure_qvm_3job_public_receipt.json"


def _plan():
    return create_plan(json.loads(SOURCE.read_text()))


def test_numeric_score_independent_of_word_choice_for_hardware_answer():
    plan = _plan()
    responses=[]
    for blind_id,meta in plan["private_scoring_key_NEVER_SENT_TO_MODEL"].items():
        responses.append({"id":blind_id,"text":f"p11 = {meta['answer']:.6f}; Hardware = 'physical'"})
    supplemental=evaluate(plan,responses,analysis_status="PREREGISTERED_STAGE014_METRIC")
    assert supplemental["cases"] == 15
    assert all(x["numerical_parsed"]==3 for x in supplemental["per_arm_unranked"].values())
    assert all(x["numerical_MAE_invalid_as_1"]<.000002 for x in supplemental["per_arm_unranked"].values())
    assert all(x["simulator_correct_count"]==0 for x in supplemental["per_arm_unranked"].values())
    # Old exact mixed-field rubric is intentionally left untouched.
    old=score(plan,responses)
    assert all(x["valid_answers"]==0 for x in old["results_unranked_by_arm"].values())


def test_missing_or_bad_numbers_are_penalized():
    plan=_plan()
    samples=[{"id":case["id"],"text":"p11=oops; hardware=no"}
             for case in plan["public_model_inputs"]]
    scored=evaluate(plan,samples,analysis_status="PREREGISTERED_STAGE014_METRIC")
    assert all(x["numerical_MAE_invalid_as_1"]==1.0 for x in scored["per_arm_unranked"].values())
    assert all(x["simulator_correct_count"]==3 for x in scored["per_arm_unranked"].values())
    with pytest.raises(ValueError):
        evaluate(plan,samples[:-1],analysis_status="PREREGISTERED_STAGE014_METRIC")
    with pytest.raises(ValueError):
        evaluate(plan,samples,analysis_status="forged_registration")


def test_digest_catches_any_posthoc_prompt_edit():
    plan=_plan()
    prior={
        "source_class":"THREE_PAST_REAL_AZURE_CLOUD_SIMULATOR_JOBS_NOT_HARDWARE",
        "model":plan["model"],
        "input_plan_digest":"f"*64,
        "individual":[{"id":row["id"],"raw_answer":"p11=0.500; hardware=no"}
                      for row in plan["public_model_inputs"]],
    }
    with pytest.raises(ValueError):
        analyze_prior_model_receipt(plan,prior)
    prior["input_plan_digest"]=public_input_digest(plan)
    scored=analyze_prior_model_receipt(plan,prior)
    assert scored["analysis_status"]=="POST_HOC_STAGE013_DIAGNOSTIC"
    assert len(scored["individual_rows"])==15
