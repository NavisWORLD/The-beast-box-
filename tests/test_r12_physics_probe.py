from __future__ import annotations

import copy

import pytest

from beastbox.r12_physics_probe import (
    ARM_ORDER,
    FROZEN_R12_VECTOR,
    NON_NEUTRAL_ARMS,
    PROTECTED_LEDGER_TIP_SHA256,
    TALK4_SHA256,
    analyze_probe,
    build_arms,
    build_echo_program,
    build_preregistration,
    derive_preseal_seeds,
    randomization_pvalue,
    residual_metrics,
    run_synthetic_preflight,
    sha256_json,
    stage_statistic,
    verify_ideal_echo,
    verify_preregistration,
)


def _blocks(effect: float = 0.0, *, prefix: str = "j"):
    rows=[]
    for i in range(24):
        base=0.08+(i%3)*0.001
        residuals={arm:base for arm in NON_NEUTRAL_ARMS}
        residuals["CANONICAL"]=base+effect
        residuals["NEUTRAL"]=base-0.01
        rows.append({"block_id":i,"job_id":f"{prefix}-{i//8}","residuals":residuals})
    return rows


def test_frozen_preregistration_is_deterministic_and_tamper_evident():
    seeds=derive_preseal_seeds()
    arms=build_arms(FROZEN_R12_VECTOR,seeds["perm_hashed_seed"])
    assert tuple(arms)==ARM_ORDER
    assert sorted(arms["CANONICAL"])==sorted(arms["PERM_HASHED"])
    packet=build_preregistration(source_commit="1"*40,vector=FROZEN_R12_VECTOR,ledger_tip=PROTECTED_LEDGER_TIP_SHA256,checkpoint_sha=TALK4_SHA256)
    digest=sha256_json(packet)
    verify_preregistration(packet,digest)
    altered=copy.deepcopy(packet); altered["analysis"]["effect_floor"]=0.01
    with pytest.raises(ValueError): verify_preregistration(altered,digest)


def test_echo_program_has_exact_inverse_budget_and_barrier():
    arms=build_arms(FROZEN_R12_VECTOR,derive_preseal_seeds()["perm_hashed_seed"])
    program=build_echo_program(arms["CANONICAL"])
    assert sum(1 for op in program if op[0]=="cx")==22
    assert sum(1 for op in program if op[0]=="barrier")==1
    assert len(program)==95


def test_exact_qm_echo_returns_every_arm_to_zero():
    pytest.importorskip("qiskit")
    arms=build_arms(FROZEN_R12_VECTOR,derive_preseal_seeds()["perm_hashed_seed"])
    report=verify_ideal_echo(arms,tolerance=1e-12)
    assert report["passed"] is True
    assert all(v["p_zero"]>=1-1e-12 for v in report["arms"].values())


def test_residual_is_one_minus_zero_survival():
    counts={"0"*12:3072,"1"+"0"*11:1024}
    metrics=residual_metrics(counts,shots=4096)
    assert metrics["survival_probability"]==0.75
    assert metrics["residual"]==0.25
    assert metrics["tvd_from_ideal"]==0.25


def test_stage_statistic_uses_canonical_minus_median_controls():
    report=stage_statistic(_blocks(0.03))
    assert report["t_stage"]==pytest.approx(0.03)


def test_randomization_test_is_seed_deterministic():
    blocks=_blocks(0.03)
    a=randomization_pvalue(blocks,seed=1234,n=2000)
    b=randomization_pvalue(blocks,seed=1234,n=2000)
    assert a==b
    assert 0.0<a["p_value"]<=1.0


def test_bounded_analysis_can_return_null_or_candidate_only():
    null=analyze_probe(_blocks(0.0,prefix="d"),_blocks(0.0,prefix="r"),analysis_seed=7,randomizations=100,discovery_backend="a",replication_backend="b")
    assert null["outcome"]=="NULL_COMPATIBLE"
    assert null["outcome"] in {"NULL_COMPATIBLE","NULL_COMPATIBLE_REPLICATION_FAILED","ANOMALY_CANDIDATE_SAME_BACKEND","ANOMALY_CANDIDATE"}


def test_1000_dataset_synthetic_preflight_stays_below_one_percent():
    packet=build_preregistration(source_commit="2"*40,vector=FROZEN_R12_VECTOR,ledger_tip=PROTECTED_LEDGER_TIP_SHA256,checkpoint_sha=TALK4_SHA256)
    report=run_synthetic_preflight(packet,datasets=1000,randomizations=20000)
    assert report["passed"] is True
    assert report["full_anomaly_rate"]<=0.01
