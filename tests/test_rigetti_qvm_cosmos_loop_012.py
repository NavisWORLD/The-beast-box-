"""Stage-012 sealed replay, matched controls and fail-closed Azure target tests."""
from __future__ import annotations

import hashlib
import importlib.util
import math
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1] / "experiments" / "rigetti-qvm-cosmos-012"


def _load(name: str):
    spec = importlib.util.spec_from_file_location("stage012_"+name,ROOT/(name+".py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ideal_quil_probabilities_normalized_and_basis():
    loop=_load("loop")
    for theta,phi in ((0,0),(math.pi,0),(0,math.pi),(1.55,1.55)):
        probs=loop.ideal_probabilities(theta,phi)
        assert set(probs)=={"00","01","10","11"}
        assert all(0<=v<=1 for v in probs.values())
        assert sum(probs.values())==pytest.approx(1)
        assert "CNOT 0 1" in loop.quil_for_angles(theta,phi)
    assert loop.ideal_probabilities(0,0)=={"00":1.0,"01":0.0,"10":0.0,"11":0.0}
    assert sum(loop.sample_classical_ideal(1.55,1.55,iteration=0,seed=67).values())==64


def test_bounded_local_cns_replay_reproducible_and_controls():
    loop=_load("loop")
    a=loop.run(iterations=31,seed=67)
    b=loop.run(iterations=31,seed=67)
    assert a==b
    assert a["source"]["raw_provider_histograms_present"] is False
    assert a["source"]["historical_zero_admissible_four_state_result_preserved"] is True
    assert len(a["source"]["summary_row_sha256"])==9
    assert a["azure_qvm_jobs_submitted"]==a["physical_qpu_jobs_submitted"]==0
    assert a["calls_to_external_cloud_models"]==0
    assert set(a["controls"])==set(loop.MODES)
    assert all(len(row["final_state12"])==12 for row in a["controls"].values())
    assert a["controls"]["fused"]["trajectory_sha256"] != a["controls"]["simulator_only"]["trajectory_sha256"]
    assert a["controls"]["fused"]["trajectory_sha256"] != a["controls"]["archive_shuffled"]["trajectory_sha256"]
    assert a["controls"]["zero"]["nonzero_input_steps"]==0
    assert a["controls"]["zero"]["final_state12"]==[0.0]*12
    assert a["controls"]["frozen"]["final_state12"]==[0.0]*12
    assert a["cloud_model_preview"]["send_enabled"] is False
    assert a["checkpoints"][-1]["iteration"]==31


def test_qvm_one_job_anchor_is_optional_and_never_relabels_replay():
    loop=_load("loop")
    qvm=_load("azure_qvm")
    dry=qvm.dry_run()
    assert dry["target"]==loop.QVM_TARGET
    assert dry["job_count"]==dry["physical_qpu_jobs"]==0
    assert dry["real_azure_qvm_execution_attested"] is False
    with pytest.raises(ValueError):
        qvm.require_target("rigetti.qpu.cepheus-1-108q")
    anchor={
        "schema":qvm.SCHEMA,"target":qvm.TARGET,"status":"SUCCEEDED",
        "shots":64,"physical_qpu_jobs":0,"new_azure_qvm_jobs_submitted":1,
        "job_id":"synthetic-unit-test-not-azure", "quil_sha256":dry["quil_sha256"],
        "counts":{"00":20,"01":12,"10":13,"11":19},
    }
    loop.verify_optional_qvm_anchor(anchor)
    out=loop.run(iterations=9,seed=67,qvm_anchor=anchor)
    assert out["azure_qvm_jobs_submitted"]==1
    assert out["physical_qpu_jobs_submitted"]==0
    assert out["source"]["raw_provider_histograms_present"] is False
    assert out["controls"]["fused"]["trajectory_sha256"] != loop.run(iterations=9,seed=67)["controls"]["fused"]["trajectory_sha256"]
    for bad in (
        {**anchor,"target":"rigetti.qpu.cepheus-1-108q"},
        {**anchor,"quil_sha256":"0"*64},
        {**anchor,"counts":{"00":64}},
        {**anchor,"physical_qpu_jobs":1},
    ):
        with pytest.raises(ValueError):
            loop.verify_optional_qvm_anchor(bad)


def test_invalid_budgets_and_angles_fail_closed():
    loop=_load("loop")
    for n in (0,-1,10_001):
        with pytest.raises(ValueError):
            loop.run(iterations=n)
    for angle in (-1.0,float("nan"),math.pi+1):
        with pytest.raises(ValueError):
            loop.quil_for_angles(angle,0.1)


def test_raw_export_decoder_reconstructs_full_bounded_5bit_counts_without_network():
    import base64
    import zlib
    raw=_load("raw_archive")
    sample=bytes(list(range(32))*128)  # clearly synthetic unit fixture: 4096 true shots
    header_spec=b"{'descr': '|u1', 'fortran_order': False, 'shape': (4096, 1), }"
    header=header_spec.ljust(117,b" ")+bytes([10])
    assert len(header)==118
    npy=bytes([0x93])+b"NUMPY"+bytes([1,0])+(118).to_bytes(2,"little")+header+sample
    assert len(npy)==4224  # the 128-byte header is not 128 extra measurements
    compressed=base64.b64encode(zlib.compress(npy)).decode("ascii")
    bitarray={"__type__":"BitArray","__value__":{
        "num_bits":5, "array":{"__type__":"ndarray","__value__":compressed}}}
    data={"__value__":{"fields":{"meas":bitarray}}}
    pub={"__type__":"SamplerPubResult","__value__":{"data":data}}
    payload={"__type__":"PrimitiveResult","__value__":{"pub_results":[pub]}}
    counts,shots,header_bytes=raw.decode_serialized_bitarray(payload)
    assert shots==4096 and header_bytes==128 and len(counts)==32
    assert set(counts.values())=={128}
    assert raw.historical_entropy(counts)==pytest.approx(1.0)
    assert raw.git_blob_sha1(b"hi")==hashlib.sha1(b"blob 2"+bytes([0])+b"hi").hexdigest()
    payload["__value__"]["pub_results"][0]["__value__"]["data"]["__value__"]["fields"]["meas"]["__value__"]["num_bits"]=4
    with pytest.raises(ValueError):
        raw.decode_serialized_bitarray(payload)


def test_untrusted_full_archived_manifest_is_rejected():
    loop=_load("loop")
    with pytest.raises(ValueError):
        loop.run(iterations=1,raw_histograms={"schema":"anything","records":[]})
