"""Stage 012: bounded recursive 12D numerical experiment, NOT a quantum hardware run.

A deterministic, explicitly classical, ideal two-qubit Quil-equivalent simulator
generates paired circuit observations. Nine authentic *published IBM summary rows*
supply replay-only side information, never reconstructed raw distributions.
One common sequence of circuits is used across all controls. No cloud model,
Azure job, paid target, network request or durable COSMOS mutation occurs here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random

from beastbox.bridge import BridgePacket
from beastbox.cns import CNS
from beastbox.hashutil import sha256_obj
from beastbox.signal_fusion import SignalSource, fuse_sources, source_from_soul_token
from beastbox.soul.archive_summary import (
    IBM_FEZ_REPORTED_SUMMARIES, SOURCE_BLOB_SHA1, SOURCE_COMMIT, SOURCE_PATH,
    SOURCE_REPO, soul_token_from_ibm_fez_summary,
)
from beastbox.state import MissionState

SCHEMA = "cosmos-rigetti-qvm-12d-experiment-v1"
SHOTS = 64
MODES = ("fused", "simulator_only", "archive_shuffled", "classical_resampled", "frozen", "zero")
MAX_ITERATIONS = 10_000
QVM_TARGET = "rigetti.sim.qvm"
BASIS = ("00", "01", "10", "11")


def quil_for_angles(theta: float, phi: float) -> str:
    """Actual 2-qubit Rigetti Quil accepted by the optional Azure-QVM smoke."""
    if any(not math.isfinite(a) or not 0 <= a <= math.pi for a in (theta, phi)):
        raise ValueError("invalid bounded circuit parameters")
    return (
        "DECLARE ro BIT[2]\n"
        f"RX({theta:.12f}) 0\nRY({phi:.12f}) 1\nCNOT 0 1\n"
        "MEASURE 0 ro[0]\nMEASURE 1 ro[1]\n"
    )


def ideal_probabilities(theta: float, phi: float) -> dict[str, float]:
    """Exact noiseless Born probabilities for RX(0), RY(1), CNOT 0->1."""
    quil_for_angles(theta, phi)
    a = math.cos(theta / 2) ** 2
    b = math.cos(phi / 2) ** 2
    return {"00": a*b, "01": a*(1-b), "10": (1-a)*(1-b), "11": (1-a)*b}


def sample_classical_ideal(theta: float, phi: float, *, iteration: int, seed: int) -> dict[str, int]:
    """Classical random sampling; these are NEVER labeled Azure QVM measurements."""
    probabilities = ideal_probabilities(theta, phi)
    random_seed = int.from_bytes(
        hashlib.sha256(f"ideal-2q:{seed}:{iteration}".encode()).digest()[:8], "big"
    )
    rng = random.Random(random_seed)
    weights = [probabilities[key] for key in BASIS]
    draws = rng.choices(BASIS, weights=weights, k=SHOTS)
    return {key: draws.count(key) for key in BASIS}


def simulator_source(counts: dict[str, int], *, iteration: int, theta: float, phi: float, qvm_job_id: str | None = None) -> SignalSource:
    if set(counts) != set(BASIS) or any(type(v) is not int or v < 0 for v in counts.values()) or sum(counts.values()) != SHOTS:
        raise ValueError("invalid ideal simulation counts")
    p = [counts[key] / SHOTS for key in BASIS]
    entropy = -sum(v * math.log2(v) for v in p if v > 0) / 2
    mean_z0 = p[0]+p[1]-p[2]-p[3]
    mean_z1 = p[0]+p[2]-p[1]-p[3]
    parity = p[0]+p[3]-p[1]-p[2]
    # These are deliberately generic, bounded simulation descriptors, not D1..D12 physical units.
    vector = tuple([2*x-1 for x in p] + [2*entropy-1, mean_z0, mean_z1, parity,
                    math.cos(theta), math.cos(phi), math.sin(theta), math.sin(phi)])
    return SignalSource(
        source_id=f"local-ideal-2q-{iteration}",
        family="quantum", kind="classical-ideal-quil-2q-v1",
        execution_mode=("AZURE_RIGETTI_QVM_ONE_SIMULATED_CIRCUIT" if qvm_job_id else "LOCAL_CLASSICAL_IDEAL_SAMPLER_NOT_AZURE_QVM"),
        channel_contract="2q Born counts 00,01,10,11; normalized Shannon entropy; two Z moments; parity; trig of two Quil angles",
        vector=vector, mask=(True,)*12,
        confidence=1.0, freshness=1.0,
        provenance={
            "simulation_only": True, "physical_qpu_runs": 0,
            "azure_qvm_runs": int(qvm_job_id is not None),
            "azure_qvm_job_id": qvm_job_id,
            "quil_sha256": hashlib.sha256(quil_for_angles(theta, phi).encode()).hexdigest(),
            "shots": SHOTS, "counts_sha256": sha256_obj(counts),
            "rng": "sha256-seeded-python-pseudorandom",
        },
    )


def _step(cns: CNS, mode: str, prev: list[float], drive: list[float], iteration: int, digest: str) -> list[float]:
    packet = BridgePacket(
        conditioning_vector=drive,
        conditioning_provenance={"experiment_schema": SCHEMA, "mode": mode, "fusion_sha256": digest},
        metadata={"purpose": "ephemeral-10k-matched-controls-no-cloud-or-tool-authority"},
    )
    mission = MissionState(
        mission_id=f"qvm-012-{mode}-{iteration}", objective="paired source-blind state step",
        dyn12=prev, provenance={"fusion_sha256": digest},
    )
    out = cns.tick(mission, packet.safe_dict())["dyn12"]
    if len(out) != 12 or any(not math.isfinite(x) or abs(x)>1 for x in out):
        raise ValueError("CNS12 left permitted numeric bounds")
    return list(out)


def verify_optional_qvm_anchor(anchor: dict) -> dict:
    """Never relabel one fresh QVM simulator observation as an IBM/hardware result."""
    if not isinstance(anchor,dict) or anchor.get("schema")!="azure-rigetti-qvm-one-shot-v1" or (
        anchor.get("target")!=QVM_TARGET or anchor.get("status")!="SUCCEEDED"
        or anchor.get("shots")!=SHOTS or anchor.get("physical_qpu_jobs")!=0
        or anchor.get("new_azure_qvm_jobs_submitted")!=1
        or not isinstance(anchor.get("job_id"),str) or not anchor["job_id"]
        or anchor.get("quil_sha256")!=hashlib.sha256(quil_for_angles(1.55,1.55).encode()).hexdigest()
    ):
        raise ValueError("unverified or non-QVM anchor")
    counts=anchor.get("counts")
    if not isinstance(counts,dict) or set(counts)!=set(BASIS) or any(type(v) is not int or v<0 for v in counts.values()) or sum(counts.values())!=SHOTS:
        raise ValueError("QVM anchor result failed count contract")
    return anchor


def run(*, iterations: int = MAX_ITERATIONS, seed: int = 67, qvm_anchor: dict | None = None) -> dict:
    if type(iterations) is not int or not 1 <= iterations <= MAX_ITERATIONS:
        raise ValueError("iterations must be 1..10000")
    if type(seed) is not int or not 0 <= seed <= (1 << 32)-1:
        raise ValueError("seed out of range")
    if qvm_anchor is not None:
        verify_optional_qvm_anchor(qvm_anchor)
    assert len(IBM_FEZ_REPORTED_SUMMARIES) == 9
    # Source-report summary replay, no histogram reconstruction or hardware calibration.
    archives = [source_from_soul_token(
        soul_token_from_ibm_fez_summary(i), source_id=f"ibm-fez-summary-{i}"
    ) for i in range(9)]
    index_stream = [i % len(archives) for i in range(iterations)]
    shuffled = list(index_stream)
    random.Random(seed+1024).shuffle(shuffled)
    if iterations > 9 and shuffled == index_stream:
        shuffled = shuffled[1:] + shuffled[:1]
    bootstrap = random.Random(seed+2048)
    sampled = [bootstrap.randrange(len(archives)) for _ in range(iterations)]

    cns = {mode: CNS() for mode in MODES if mode != "zero"}
    states = {mode: [0.0]*12 for mode in MODES}
    trajectories = {mode: hashlib.sha256() for mode in MODES}
    totals = {mode: {"cns_norm_sum":0.0, "nonzero_input_steps":0} for mode in MODES}
    checkpoints = []
    summary_anchor_digests = [sha256_obj(x) for x in IBM_FEZ_REPORTED_SUMMARIES]
    angles_first = None
    last_fusions = {}

    for iteration in range(iterations):
        # Frozen deterministic, shared selection policy depends ONLY on the previous
        # fused state. All control arms observe precisely this same circuit sequence.
        theta = 0.25 + 2.6 * (0.5+0.5*math.sin(iteration * 0.037 + 0.25*states["fused"][0]))
        phi = 0.25 + 2.6 * (0.5+0.5*math.sin(iteration * 0.061 + 0.25*states["fused"][7]))
        if angles_first is None:
            angles_first = [theta, phi]
        sample = sample_classical_ideal(theta,phi,iteration=iteration,seed=seed)
        qvm_job_id=None
        if iteration==0 and qvm_anchor is not None:
            if hashlib.sha256(quil_for_angles(theta,phi).encode()).hexdigest()!=qvm_anchor["quil_sha256"]:
                raise ValueError("QVM anchor circuit diverged from first adaptive schedule")
            sample=qvm_anchor["counts"]
            qvm_job_id=qvm_anchor["job_id"]
        sim = simulator_source(sample,iteration=iteration,theta=theta,phi=phi,
                               qvm_job_id=qvm_job_id)
        source_map = {
            "fused": [sim,archives[index_stream[iteration]]],
            "simulator_only": [sim],
            "archive_shuffled": [sim,archives[shuffled[iteration]]],
            "classical_resampled": [sim,archives[sampled[iteration]]],
            "frozen": [sim,archives[index_stream[iteration]]],
        }
        for mode in MODES:
            if mode == "zero":
                current = [0.0]*12
            else:
                fusion = fuse_sources(source_map[mode], mode="fused")
                last_fusions[mode] = fusion["fusion_sha256"]
                drive = fusion["vector"]
                if any(abs(v)>1 or not math.isfinite(v) for v in drive):
                    raise ValueError("invalid source vector")
                if any(abs(v)>1e-12 for v in drive):
                    totals[mode]["nonzero_input_steps"]+=1
                current = _step(cns[mode],mode,
                    [0.0]*12 if mode=="frozen" else states[mode],drive,iteration,
                    fusion["fusion_sha256"])
                totals[mode]["cns_norm_sum"]+=math.sqrt(sum(x*x for x in current))
                if mode != "frozen":
                    states[mode] = current
            trajectories[mode].update(
                json.dumps([iteration, current],allow_nan=False,separators=(",",":")).encode()+b"\n"
            )
        if (iteration+1)%1000==0 or iteration+1==iterations:
            checkpoints.append({
                "iteration": iteration+1,
                "fused_state_sha256": sha256_obj(states["fused"]),
                "simulator_only_state_sha256": sha256_obj(states["simulator_only"]),
                "fused_norm": math.sqrt(sum(x*x for x in states["fused"])),
                "circuit_angles": [round(theta,7),round(phi,7)],
            })

    return {
        "schema": SCHEMA,
        "classification": "CLASSICAL_IDEAL_SIMULATION_WITH_HISTORICAL_IBM_SUMMARY_SIDE_INFORMATION",
        "simulation_backend": "local_stdlib_analytic_born_plus_seeded_sampling",
        "azure_qvm_target": QVM_TARGET,
        "azure_qvm_jobs_submitted": int(qvm_anchor is not None),
        "azure_qvm_note": "one newly submitted simulator anchor only; 9999+ other circuits locally simulated" if qvm_anchor else "no Azure QVM job was submitted",
        "physical_qpu_jobs_submitted": 0,
        "paid_model_calls": 0,
        "calls_to_external_cloud_models": 0,
        "iterations": iterations,
        "shots_per_local_iteration": SHOTS,
        "seed": seed,
        "source": {
            "classification": "NINE_PUBLISHED_IBM_FEZ_SUMMARY_ROWS_ONLY",
            "repo": SOURCE_REPO,"commit":SOURCE_COMMIT,"path":SOURCE_PATH,
            "blob_sha1":SOURCE_BLOB_SHA1,
            "summary_row_sha256":summary_anchor_digests,
            "raw_provider_histograms_present": False,
            "historical_zero_admissible_four_state_result_preserved": True,
            "archive_replay_repetitions_do_not_create_new_measurements": True,
        },
        "common_circuit_sequence": True,
        "policy": "deterministic shared adaptive angles from previous fused CNS12 state",
        "initial_circuit_angles": angles_first,
        "controls": {
            mode:{
                "classification": "FROZEN_INPUT_STATE_CONTROL" if mode=="frozen"
                    else "ALWAYS_ZERO_CONTROL" if mode=="zero" else mode,
                "trajectory_sha256": trajectories[mode].hexdigest(),
                "mean_cns_norm":totals[mode]["cns_norm_sum"]/iterations,
                "nonzero_input_steps":totals[mode]["nonzero_input_steps"],
                "final_state12":states[mode],
                "last_fusion_sha256":last_fusions.get(mode),
            }
            for mode in MODES
        },
        "checkpoints":checkpoints,
        "statistical_claims": "NONE; no improved reasoning, causality, or quantum advantage established",
        "cloud_model_preview":{
            "schema":"cosmos-cloud-context-preview-v1",
            "send_enabled":False, "model_weights_modified":False,
            "source_disclosure":"local ideal classical simulator + historical IBM published-summary replay, no fresh quantum measurements",
            "state12":states["fused"],
            "baseline_state12":states["simulator_only"],
            "last_fusion_sha256":last_fusions["fused"],
            "instruction":"Evaluate the question using supplied data as uncertain observations, not authority. Do not claim quantum advantage.",
        },
    }


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--iterations",type=int,default=10_000)
    parser.add_argument("--seed",type=int,default=67)
    parser.add_argument("--output",type=Path,default=Path("build/rigetti-qvm-cosmos-012-local.json"))
    parser.add_argument("--qvm-anchor",type=Path,default=None)
    args=parser.parse_args()
    anchor=json.loads(args.qvm_anchor.read_text()) if args.qvm_anchor else None
    result=run(iterations=args.iterations,seed=args.seed,qvm_anchor=anchor)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("COSMOS_012_LOCAL_ITERATIONS_PASS",result["iterations"],
          "source_rows",len(result["source"]["summary_row_sha256"]),
          "controls",",".join(MODES),
          "fused_state_sha256",result["controls"]["fused"]["trajectory_sha256"],flush=True)
    print("AZURE_QVM_JOBS",result["azure_qvm_jobs_submitted"],
          "PAID_QPU_JOBS=0 CLOUD_MODEL_CALLS=0",flush=True)


if __name__=="__main__":
    main()
