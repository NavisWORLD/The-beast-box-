#!/usr/bin/env python3
"""ONE physical IBM Sampler job conditioned by user-supplied Wraith image light-field features.

Safety:
- A single fixed job with 4 PUBs, 4,096 shots per PUB (total 16,384).
- Limit is 120 QPU seconds on the sole job; cumulative owner ceiling is 300.
- Selects only an authenticated IBM Open Plan instance (600-second allowance).
- Rechecks quota, fails closed, checks a STABLE remote job tag for replay safety.
- No database, chat API, Railway, Azure, third-party inference, or secret logs.
- No CHSH/Bell inequality violation claim from ZZ/XX correlations.
- Original job metadata and bitstring counts are preserved with hashes.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from ibm_open_plan_preflight import quota_receipt

TAG = "navisworld-wraith-glyph303c-videoef1e-audio-v1"
OUT = Path("_ibm_bone_pig_image_light12d_20261010")
PACKET_PATH = Path("experiment-input/wraith-image-video-audio-light12d-20261009.json")
SOURCE_SHA = "303c9d2865195f0f1f7c19eaf889fa989270435e4a3047a7eb6d4b6c6de0449d"
FEATURE_SHA = "ceede33f8d78a88f8d69e315490558e9bc21c8b88cf935bd8b1e6c52d57e2f04"
SHOTS_PER_CIRCUIT = 4096
QPU_HARD_CAP = 120
EXPECTED_CIRCUITS = ["bell_zz", "bell_xx", "decoupled_zz", "decoupled_xx"]


VIDEO_SHA = "ef1e0982371a0d74ab25ee994f51f011bd6efa9b4e7fa5c25ca7a39acf4358f5"
FULL_PACKET_SHA = "255bf3bcf15d38b4c24c51daa6914386a3defa21ea7c1e2134d0eb4f33890b7e"

def verified_image_light():
    """Fail closed unless both user's glyph and movie-with-audio supplied quantum parameters."""
    packet=json.loads(PACKET_PATH.read_text())
    core={k:v for k,v in packet.items() if k!="qpu_summary_sha256"}
    if packet.get("schema") != "beastbox-wraith-qpu-photo-video-audio-light12d-v1" or packet.get("creature_name")!="Wraith":
        raise ValueError("Wrong creature packet")
    if packet.get("source_image_sha256")!=SOURCE_SHA or packet.get("source_video_sha256")!=VIDEO_SHA:
        raise ValueError("Wraith original sources differ")
    if packet.get("qpu_summary_sha256")!=FEATURE_SHA or digest(core)!=FEATURE_SHA or packet.get("original_full_packet_sha256")!=FULL_PACKET_SHA:
        raise ValueError("Original image-video-audio source feature commitment mismatch")
    if packet.get("window_count")!=48 or packet.get("frame_count",0)<48 or packet.get("audio_sample_count",0)<8000 or packet.get("raw_media_sent_to_ibm") is not False:
        raise ValueError("No actual sampled video/audio source or unsafe source state")
    g=packet.get("global_12d")
    q=packet.get("quarter_means_12d")
    if not isinstance(g,list) or len(g)!=12 or not isinstance(q,list) or len(q)!=4 or len({tuple(row) for row in q})!=4:
        raise ValueError("Missing multisource 12D feature channels")
    for row in [g]+q:
        if len(row)!=12 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in row):
            raise ValueError("Nonfinite/invalid 12-channel feature")
    if g[6]<=0 or g[7]<=0 or g[8]<=0:
        raise ValueError("No video motion or audio signal; abort before quantum submission")
    return packet


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(name: str, content: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n")


def digest(data: object) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def circuits(image_light):
    """A genuine 12D pixel/motion/audio gate encoder; no photon or audio waveform injection."""
    from qiskit import QuantumCircuit
    g=image_light["global_12d"]
    q=image_light["quarter_means_12d"]
    result=[]
    for entangled in (True,False):
        for basis in ("z","x"):
            name=("bell" if entangled else "decoupled")+"_"+basis+basis
            qc=QuantumCircuit(2,name=name)
            qc.h(0)
            if entangled:qc.cx(0,1)
            quarters=(q[0],q[1]) if basis=="z" else (q[2],q[3])
            for i in range(12):
                # Original static glyph: 0..5 and 11; moving video: 6;
                # original video's real PCM audio: 7..10. All are present.
                theta=1.25*(.4*g[i]+.3*quarters[0][i]+.3*quarters[1][i])
                target=i%2
                if i%3==0:qc.rx(theta,target)
                elif i%3==1:qc.ry(theta,target)
                else:qc.rz(theta,target)
            if basis=="x":qc.h(0);qc.h(1)
            qc.measure_all()
            result.append((name,qc))
    assert [n for n,_ in result]==EXPECTED_CIRCUITS
    return result


def counts_for(pub) -> dict[str, int]:
    counts = pub.join_data().get_counts()
    clean = {str(k).replace(" ", ""): int(v) for k, v in counts.items()}
    if not clean or not all(len(k) == 2 and set(k) <= set("01") and v >= 0 for k, v in clean.items()):
        raise ValueError("Unexpected QPU measurement bitstring shape")
    if sum(clean.values()) != SHOTS_PER_CIRCUIT:
        raise ValueError("Hardware counts do not match requested shots")
    return dict(sorted(clean.items()))


def same_parity(counts):
    shots = sum(counts.values())
    return (counts.get("00", 0) + counts.get("11", 0) - counts.get("01", 0) - counts.get("10", 0)) / shots


def run():
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    image_light = verified_image_light()
    save("source_pre_hardware.json", {
        "original_glyph_sha256":SOURCE_SHA,"original_video_sha256":VIDEO_SHA,
        "original_full_packet_sha256":FULL_PACKET_SHA,"qpu_summary_sha256":FEATURE_SHA,
        "channels":image_light["channels"],"global_12d":image_light["global_12d"],
        "quarter_means_12d":image_light["quarter_means_12d"],
        "audio_sample_count":image_light["audio_sample_count"],
        "video_frames":image_light["frame_count"],
        "source_is_classical_image_video_audio_to_quantum_gates":True,
        "raw_media_uploaded_to_ibm":False
    })
    token = os.environ.get("IBM_QUANTUM_TOKEN", "").strip()
    if not token:
        raise RuntimeError("IBM_QUANTUM_TOKEN is not configured in GitHub Actions")
    service = QiskitRuntimeService(
        channel="ibm_quantum_platform", token=token, plans_preference=["open"]
    )
    instance = service.active_instance()
    if not instance:
        raise RuntimeError("No active Open Plan instance; hardware submission disabled")
    # Do not log an instance CRN or the credential.
    quota = quota_receipt(service.usage(), str(instance))
    save("preflight.json", quota)
    if not quota["headroom_for_one_300_second_job"] or quota["remaining_seconds"] < 300:
        raise RuntimeError("Owner's 300-second aggregate headroom not verified: fail closed")
    if QPU_HARD_CAP > quota["maximum_possible_job_limit_seconds"]:
        raise RuntimeError("Requested fixed job cap exceeds verified Open Plan budget")
    # The owner authorized 300 QPU seconds total, NOT per request. Fail closed
    # if other experiment time from the Open Plan instance has consumed headroom.
    if quota["already_consumed_seconds"] + QPU_HARD_CAP > 300:
        raise RuntimeError("300-second cumulative owner experiment budget would be exceeded")
    if os.environ.get("BEAST_REAL_QPU_ONE_JOB") != "YES_ONE_REAL_JOB":
        raise RuntimeError("Explicit one-job execution flag not set: fail closed")

    # Fail closed if replay lookup is inaccessible. The fixed tag is deliberately
    # stable across workflow retries, PR updates, and workflow dispatch.
    previous = service.jobs(limit=100, program_id="sampler", job_tags=[TAG])
    if previous:
        if len(previous) != 1: raise RuntimeError("Ambiguous remote-tag replay, refuse a new job")
        job = previous[0]
        save("submission.json", {
            "schema": "navisworld-ibm-onejob-submission-v1", "existing_job_reused": True,
            "job_id": str(job.job_id()), "utc": stamp(), "job_tag": TAG,
            "no_new_job_submitted_on_this_attempt": True,
            "qpu_hard_cap_seconds": QPU_HARD_CAP,
        })
        print("REUSED_EXISTING_JOB_ID=" + str(job.job_id()), flush=True)
    else:
        backend = service.least_busy(simulator=False, operational=True, min_num_qubits=2)
        if bool(backend.configuration().simulator):
            raise RuntimeError("Backend is a simulator: QPU execution refused")
        specimens = circuits(image_light)
        pm = generate_preset_pass_manager(
            backend=backend, optimization_level=1, seed_transpiler=241009
        )
        isa = [pm.run(qc) for _, qc in specimens]
        if len(isa) != 4 or any(int(q.depth()) > 300 for q in isa):
            raise RuntimeError("Unexpected compiled circuit complexity")
        save("proposed_circuits.json", {
            "schema": "beastbox-ibm-probe-circuits-v1",
            "design": "Original Wraith glyph plus moving-video/audio 12D conditioned gates, Bell vs no-CX controls",
            "image_source_sha256": SOURCE_SHA,
            "video_source_sha256":VIDEO_SHA,"full_feature_sha256":FULL_PACKET_SHA,
            "image_feature_commitment_sha256": FEATURE_SHA,
            "source_image_feature_commitment":FEATURE_SHA,
            "names": EXPECTED_CIRCUITS,
            "shots_per_circuit": SHOTS_PER_CIRCUIT,
            "total_shots_requested": SHOTS_PER_CIRCUIT * len(isa),
            "backend_name": str(backend.name),
            "compiled_depths": [int(q.depth()) for q in isa],
            "max_qpu_seconds": QPU_HARD_CAP,
            "circuit_qasm_sha256": [hashlib.sha256(str(q).encode()).hexdigest() for q in isa],
            "no_bell_inequality_violation_claimed": True,
            "image_light_affects_quantum_gates_before_submission": True,
            "video_audio_affects_quantum_gates_before_submission":True,
        })
        sampler = SamplerV2(mode=backend)
        sampler.options.max_execution_time = QPU_HARD_CAP
        sampler.options.environment.job_tags = [TAG, "navisworld", "beast-reality-probe"]
        # ONE request, not four jobs, with one server-enforced QPU runtime limit.
        job = sampler.run(isa, shots=SHOTS_PER_CIRCUIT)
        record = {
            "schema": "navisworld-ibm-onejob-submission-v1",
            "job_id": str(job.job_id()), "utc": stamp(), "job_tag": TAG,
            "backend": str(backend.name), "source_class": "IBM_HARDWARE_SUBMITTED",
            "existing_job_reused": False, "requested_jobs_this_attempt": 1,
            "max_qpu_seconds": QPU_HARD_CAP, "total_user_budget_qpu_seconds": 300,
            "shots_requested_total": 4 * SHOTS_PER_CIRCUIT,
            "credential_saved": False,
        }
        save("submission.json", record)
        print("REAL_QPU_JOB_ID=" + str(job.job_id()), flush=True)

    # If the job remains in queue after Actions times out, its submission.json is
    # retained by the workflow even if results are not available yet. A rerun with
    # the same tag recovers the job instead of submitting another.
    raw = job.result()
    if len(raw) != len(EXPECTED_CIRCUITS):
        raise RuntimeError("Returned PUB count differs from submitted circuit count")
    distributions = {name: counts_for(raw[i]) for i, name in enumerate(EXPECTED_CIRCUITS)}
    metrics = {}
    try:
        metrics = job.metrics() or {}
    except Exception:
        metrics = {"metrics_status": "not_available"}
    usage = metrics.get("usage", {}) if isinstance(metrics, dict) else {}
    quantum_seconds = usage.get("quantum_seconds") if isinstance(usage, dict) else None
    if quantum_seconds is not None and (not isinstance(quantum_seconds, (float, int)) or not math.isfinite(quantum_seconds)):
        quantum_seconds = None
    analysis = {
        "bell_ZZ": same_parity(distributions["bell_zz"]),
        "bell_XX": same_parity(distributions["bell_xx"]),
        "decoupled_ZZ": same_parity(distributions["decoupled_zz"]),
        "decoupled_XX": same_parity(distributions["decoupled_xx"]),
    }
    receipt = {
        "schema": "navisworld-ibm-longer-onejob-physics-receipt-v1",
        "job_id": str(job.job_id()), "backend_name": str(job.backend().name),
        "source_class": "RECORDED_IBM_HARDWARE",
        "submitted_on_or_before": stamp(),
        "job_status": str(job.status()),
        "shot_count": sum(sum(c.values()) for c in distributions.values()),
        "measurements": distributions,
        "expectations": analysis,
        "hardware_metrics": {"quantum_seconds": quantum_seconds},
        "qpu_job_limit_seconds": QPU_HARD_CAP,
        "counts_digest_sha256": digest(distributions),
        "beast_genesis_digest_sha256": digest({
            "domain": "NAVISWORLD::IBM::WRAITH_IMAGE_VIDEOAUDIO_LIGHT12D::QBEAST::V1",
            "job_id": str(job.job_id()), "backend": str(job.backend().name),
            "counts": distributions
        }),
        "wraith_multisource_pre_hardware":{
          "original_glyph_sha256":SOURCE_SHA,"original_video_sha256":VIDEO_SHA,
          "full_packet_sha256":FULL_PACKET_SHA,"qpu_summary_sha256":FEATURE_SHA,
          "video_motion_and_audio_are_qpu_gate_controls":True,
          "raw_media_uploaded":False,
          "physical_optical_light_or_sound_state":False
        },
        "study_limitations": [
            "ZZ/XX correlations are hardware measurements, not a full state vector tomography.",
            "Two-basis correlation differences do not alone establish a CHSH/Bell inequality violation.",
            "Decoupled controls omit CX gate; this is not evidence of dynamical decoupling.",
            "The creature's subsequent personality, state evolution and conversation are classical computations.",
            "No Azure Cosmos DB write or live game conversation occurred in this job.",
            "Quantum circuit uses classical features from the Wraith glyph, moving video frames and video PCM audio; there is no optical photon injection."
        ],
    }
    save("measurement_receipt.json", receipt)
    print("IBM_WRAITH_MULTISOURCE_REAL_MEASUREMENT_RESULT=" + json.dumps({
        "job_id": receipt["job_id"], "backend": receipt["backend_name"],
        "shots": receipt["shot_count"], "quantum_seconds": quantum_seconds,
        "expectations": analysis, "counts_digest_sha256": receipt["counts_digest_sha256"],
        "genesis_digest_sha256": receipt["beast_genesis_digest_sha256"],
        "photo_sha256": SOURCE_SHA, "video_sha256": VIDEO_SHA,
        "features_sha256":FEATURE_SHA,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        save("failure.json", {
            "schema": "navisworld-ibm-probe-failure-v1", "utc": stamp(),
            "error_type": type(exc).__name__,
            "message": str(exc)[:400].replace(os.environ.get("IBM_QUANTUM_TOKEN", "__NOT_PRESENT__"), "[REDACTED]"),
            "notice": "Failure is not an IBM measurement. Inspect submission.json separately for any prior submission.",
        })
        print("PROBE_FAILED=" + type(exc).__name__, file=sys.stderr)
        raise
