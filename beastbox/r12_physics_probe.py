"""Null-first R12 Physics Probe 001 contracts.

This module deliberately separates an engineered 12-coordinate R12 state from any
claim about physical dimensions.  It provides the frozen quantum-echo mapping,
preregistration hashing, residual metrics, randomization tests and bounded verdicts.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from typing import Any

PROBE_ID = "r12-physics-probe-001"
CIRCUIT_FORMULA_VERSION = "r12-quantum-echo-v1"
SEED_FORMULA_VERSION = "r12-probe-preseal-v1"
DESIGN_COMMIT_SHA = "75dc7ea62a6c37cf1df834c1b876864758bc9181"
PROTECTED_STATE_SHA256 = "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"
PROTECTED_LEDGER_TIP_SHA256 = "78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415"
TALK4_SHA256 = "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"

R12_NAMES = (
    "source_integrity", "temporal_novelty", "measurement_confidence",
    "distribution_energy", "cross_condition_agreement", "distribution_entropy",
    "surprise", "memory_relevance", "retention_pressure",
    "contradiction_pressure", "adaptation_stability", "reality_coupling",
)
FROZEN_R12_VECTOR = OrderedDict((
    ("source_integrity", 1.0),
    ("temporal_novelty", 1.0),
    ("measurement_confidence", 1.0),
    ("distribution_energy", 0.03709721565246582),
    ("cross_condition_agreement", 0.5821940104166666),
    ("distribution_entropy", 0.9737669098248636),
    ("surprise", 0.33837890625),
    ("memory_relevance", 0.6),
    ("retention_pressure", 0.86767578125),
    ("contradiction_pressure", 0.0),
    ("adaptation_stability", 0.9791562241472875),
    ("reality_coupling", 0.7824778407808468),
))
ARM_ORDER = ("CANONICAL", "PERM_CYCLIC", "PERM_REVERSE", "PERM_HASHED", "COMPLEMENT", "NEUTRAL")
NON_NEUTRAL_ARMS = ARM_ORDER[:-1]
CLAIM_BOUNDARY = (
    "Probe 001 tests a preregistered matched-control quantum echo residual. "
    "No outcome by itself proves a literal twelfth dimension, a new law of physics, "
    "quantum advantage, consciousness, resurrection, deceased identity, or communication with the dead."
)


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def _validate_vector(vector: Mapping[str, float]) -> tuple[float, ...]:
    if tuple(vector.keys()) != R12_NAMES:
        raise ValueError("R12 vector names/order mismatch")
    values = tuple(float(vector[name]) for name in R12_NAMES)
    if not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in values):
        raise ValueError("R12 values must be finite and in [0,1]")
    return values


def centered_vector(vector: Mapping[str, float]) -> tuple[float, ...]:
    return tuple(2.0 * value - 1.0 for value in _validate_vector(vector))


def _domain_seed(seed_material: str, domain: str) -> int:
    digest = hashlib.sha256(f"{seed_material}:{domain}".encode()).hexdigest()
    return int(digest[:16], 16)


def derive_preseal_seeds() -> dict[str, Any]:
    material = {
        "probe_id": PROBE_ID,
        "seed_formula_version": SEED_FORMULA_VERSION,
        "r12_state_sha256": PROTECTED_STATE_SHA256,
        "r12_ledger_tip_sha256": PROTECTED_LEDGER_TIP_SHA256,
        "talk4_checkpoint_sha256": TALK4_SHA256,
        "circuit_formula_version": CIRCUIT_FORMULA_VERSION,
        "design_commit_sha256": DESIGN_COMMIT_SHA,
    }
    preseal = sha256_json(material)
    return {
        "seed_material": material,
        "preseal_seed_sha256": preseal,
        "perm_hashed_seed": _domain_seed(preseal, "perm-hashed"),
        "arm_order_seed": _domain_seed(preseal, "arm-order"),
        "analysis_seed": _domain_seed(preseal, "analysis"),
        "synthetic_seed": _domain_seed(preseal, "synthetic"),
    }


def build_arms(vector: Mapping[str, float], perm_seed: int) -> dict[str, tuple[float, ...]]:
    values = _validate_vector(vector)
    indices = list(range(12))
    random.Random(int(perm_seed)).shuffle(indices)
    return {
        "CANONICAL": values,
        "PERM_CYCLIC": values[1:] + values[:1],
        "PERM_REVERSE": tuple(reversed(values)),
        "PERM_HASHED": tuple(values[i] for i in indices),
        "COMPLEMENT": tuple(1.0 - value for value in values),
        "NEUTRAL": (0.5,) * 12,
    }


def build_preregistration(*, source_commit: str, vector: Mapping[str, float], ledger_tip: str, checkpoint_sha: str) -> dict[str, Any]:
    if len(source_commit) != 40:
        raise ValueError("source_commit must be a 40-character git SHA")
    if ledger_tip != PROTECTED_LEDGER_TIP_SHA256:
        raise ValueError("protected R12 ledger tip mismatch")
    if checkpoint_sha != TALK4_SHA256:
        raise ValueError("protected TALK-004 checkpoint mismatch")
    values = _validate_vector(vector)
    seeds = derive_preseal_seeds()
    arms = build_arms(vector, seeds["perm_hashed_seed"])
    return {
        "schema": "r12-physics-probe-preregistration-v1",
        "probe_id": PROBE_ID,
        "source_commit": source_commit,
        "protected": {
            "r12_state_sha256": PROTECTED_STATE_SHA256,
            "r12_ledger_tip_sha256": ledger_tip,
            "talk4_checkpoint_sha256": checkpoint_sha,
            "r12_vector": {name: values[i] for i, name in enumerate(R12_NAMES)},
        },
        "seeds": {k: seeds[k] for k in ("preseal_seed_sha256", "perm_hashed_seed", "arm_order_seed", "analysis_seed", "synthetic_seed")},
        "circuit": {
            "formula_version": CIRCUIT_FORMULA_VERSION,
            "qubits": 12,
            "phi": (1.0 + math.sqrt(5.0)) / 2.0,
            "echo": "U(R12); barrier; U(R12)^dagger; measure",
            "optimization_level": 0,
        },
        "arms": {name: list(arms[name]) for name in ARM_ORDER},
        "workload": {
            "discovery_blocks": 24,
            "replication_blocks": 24,
            "arms_per_block": 6,
            "shots_per_pub": 4096,
            "planned_hardware_shots": 1179648,
        },
        "analysis": {
            "primary_residual": "1-P(000000000000)",
            "stage_statistic": "median(D_CANONICAL - median(D_controls))",
            "randomizations": 100000,
            "stage_p_threshold": 0.005,
            "effect_floor": 0.02,
            "two_sided": True,
        },
        "backend_policy": {
            "distinct_replication_backend_preferred": True,
            "minimum_qubits": 12,
            "connected_paths_per_stage": 4,
            "blocks_per_path_orientation": 3,
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }


def verify_preregistration(packet: Mapping[str, Any], claimed_sha256: str) -> None:
    if sha256_json(packet) != str(claimed_sha256):
        raise ValueError("preregistration SHA-256 mismatch")
    if packet.get("schema") != "r12-physics-probe-preregistration-v1":
        raise ValueError("unexpected preregistration schema")
    protected = packet.get("protected", {})
    if protected.get("r12_state_sha256") != PROTECTED_STATE_SHA256:
        raise ValueError("protected R12 state mismatch")
    if protected.get("r12_ledger_tip_sha256") != PROTECTED_LEDGER_TIP_SHA256:
        raise ValueError("protected ledger tip mismatch")
    if protected.get("talk4_checkpoint_sha256") != TALK4_SHA256:
        raise ValueError("protected checkpoint mismatch")
    if packet.get("workload", {}).get("planned_hardware_shots") != 1179648:
        raise ValueError("workload mismatch")
    if packet.get("analysis", {}).get("randomizations") != 100000:
        raise ValueError("analysis randomization contract mismatch")


def build_echo_program(values: Sequence[float]) -> list[tuple[Any, ...]]:
    vals = tuple(float(v) for v in values)
    if len(vals) != 12 or not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in vals):
        raise ValueError("echo requires twelve finite values in [0,1]")
    x = tuple(2.0 * v - 1.0 for v in vals)
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    a = ((0,1),(2,3),(4,5),(6,7),(8,9),(10,11))
    b = ((1,2),(3,4),(5,6),(7,8),(9,10))
    ops: list[tuple[Any, ...]] = []
    ops += [("ry", i, math.pi*x[i]) for i in range(12)]
    ops += [("rz", i, (math.pi/phi)*x[i]) for i in range(12)]
    ops += [("cx", q0, q1) for q0, q1 in a]
    ops += [("cx", q0, q1) for q0, q1 in b]
    ops += [("ry", i, (math.pi/phi)*x[i]) for i in range(12)]
    ops += [("barrier",)]
    ops += [("ry", i, -(math.pi/phi)*x[i]) for i in reversed(range(12))]
    ops += [("cx", q0, q1) for q0, q1 in reversed(b)]
    ops += [("cx", q0, q1) for q0, q1 in reversed(a)]
    ops += [("rz", i, -(math.pi/phi)*x[i]) for i in reversed(range(12))]
    ops += [("ry", i, -math.pi*x[i]) for i in reversed(range(12))]
    return ops


def build_echo_circuit(values: Sequence[float], *, measure: bool = False):
    try:
        from qiskit import QuantumCircuit
    except ImportError as exc:
        raise ImportError("build_echo_circuit requires the quantum extra") from exc
    qc = QuantumCircuit(12)
    for op in build_echo_program(values):
        if op[0] == "ry": qc.ry(float(op[2]), int(op[1]))
        elif op[0] == "rz": qc.rz(float(op[2]), int(op[1]))
        elif op[0] == "cx": qc.cx(int(op[1]), int(op[2]))
        elif op[0] == "barrier": qc.barrier()
        else: raise AssertionError(op[0])
    if measure:
        qc.measure_all()
    return qc


def verify_ideal_echo(arms: Mapping[str, Sequence[float]], *, tolerance: float = 1e-12) -> dict[str, Any]:
    try:
        from qiskit.quantum_info import Statevector
    except ImportError as exc:
        raise ImportError("verify_ideal_echo requires the quantum extra") from exc
    report = {"schema": "r12-probe-ideal-echo-v1", "tolerance": float(tolerance), "arms": {}}
    for name in ARM_ORDER:
        sv = Statevector.from_instruction(build_echo_circuit(arms[name], measure=False))
        p0 = float(sv.probabilities_dict().get("0"*12, 0.0))
        passed = p0 >= 1.0-tolerance and max(0.0, 1.0-p0) <= tolerance
        report["arms"][name] = {"p_zero": p0, "nonzero_probability": max(0.0, 1.0-p0), "fidelity_zero": p0, "passed": passed}
    report["passed"] = all(row["passed"] for row in report["arms"].values())
    return report


def _normalize_counts(counts: Mapping[str, int], shots: int) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw, value in counts.items():
        key = str(raw).replace(" ", "")
        if len(key) != 12 or any(bit not in "01" for bit in key):
            raise ValueError(f"invalid 12-bit outcome: {raw}")
        n = int(value)
        if n < 0: raise ValueError("negative count")
        out[key] = out.get(key, 0) + n
    if sum(out.values()) != int(shots):
        raise ValueError("shot total mismatch")
    return dict(sorted(out.items()))


def residual_metrics(counts: Mapping[str, int], *, shots: int = 4096) -> dict[str, Any]:
    c = _normalize_counts(counts, shots)
    zero = "0"*12
    p0 = c.get(zero, 0)/float(shots)
    residual = 1.0-p0
    jsd = 0.0
    parity = 0.0
    hamming: dict[str, int] = {}
    marg = [0]*12
    nonzero: list[tuple[str,int]] = []
    for outcome, count in c.items():
        p = count/float(shots)
        q = 1.0 if outcome == zero else 0.0
        m = 0.5*(p+q)
        if p > 0: jsd += 0.5*p*math.log2(p/m)
        if q > 0: jsd += 0.5*q*math.log2(q/m)
        weight = outcome.count("1")
        hamming[str(weight)] = hamming.get(str(weight),0)+count
        parity += (1.0 if weight%2 == 0 else -1.0)*count
        for i, bit in enumerate(outcome):
            if bit == "1": marg[i] += count
        if outcome != zero: nonzero.append((outcome,count))
    nonzero.sort(key=lambda item:(-item[1],item[0]))
    return {
        "shot_count": int(shots), "zero_count": c.get(zero,0),
        "survival_probability": p0, "residual": residual, "tvd_from_ideal": residual,
        "jsd_bits_from_ideal": jsd, "parity_expectation": parity/float(shots),
        "hamming_weight": dict(sorted(hamming.items(), key=lambda kv:int(kv[0]))),
        "bit_one_marginals": [v/float(shots) for v in marg],
        "top_nonzero_outcomes": nonzero[:16],
    }


def _median(values: Sequence[float]) -> float:
    x = sorted(float(v) for v in values)
    if not x: raise ValueError("median requires values")
    n = len(x); m = n//2
    return x[m] if n%2 else 0.5*(x[m-1]+x[m])


def _validate_blocks(blocks: Sequence[Mapping[str, Any]], *, exact24: bool = True) -> None:
    if exact24 and len(blocks) != 24: raise ValueError("stage requires exactly 24 blocks")
    seen: set[Any] = set()
    for block in blocks:
        bid = block.get("block_id")
        if bid in seen: raise ValueError("duplicate block_id")
        seen.add(bid)
        residuals = block.get("residuals")
        if not isinstance(residuals, Mapping): raise ValueError("block residuals missing")
        for arm in ARM_ORDER:
            v = float(residuals[arm])
            if not math.isfinite(v) or not 0.0 <= v <= 1.0: raise ValueError("residual outside [0,1]")


def stage_statistic(blocks: Sequence[Mapping[str, Any]], *, candidate_arm: str = "CANONICAL") -> dict[str, Any]:
    _validate_blocks(blocks)
    if candidate_arm not in NON_NEUTRAL_ARMS: raise ValueError("candidate arm must be non-neutral")
    controls = tuple(a for a in NON_NEUTRAL_ARMS if a != candidate_arm)
    effects = [float(b["residuals"][candidate_arm])-_median([float(b["residuals"][a]) for a in controls]) for b in blocks]
    return {"candidate_arm": candidate_arm, "control_arms": list(controls), "block_effects": effects, "t_stage": _median(effects)}


def _effect_table(blocks: Sequence[Mapping[str, Any]]):
    import numpy as np
    table = np.empty((len(blocks),len(NON_NEUTRAL_ARMS)), dtype=np.float64)
    for bi,b in enumerate(blocks):
        vals = [float(b["residuals"][a]) for a in NON_NEUTRAL_ARMS]
        for ai in range(len(vals)):
            table[bi,ai] = vals[ai]-_median(vals[:ai]+vals[ai+1:])
    return table


def randomization_pvalue(blocks: Sequence[Mapping[str, Any]], *, seed: int, n: int = 100000, candidate_arm: str = "CANONICAL") -> dict[str, Any]:
    import numpy as np
    _validate_blocks(blocks)
    if candidate_arm not in NON_NEUTRAL_ARMS: raise ValueError("candidate arm must be non-neutral")
    n = int(n)
    if n <= 0: raise ValueError("randomizations must be positive")
    observed = float(stage_statistic(blocks,candidate_arm=candidate_arm)["t_stage"])
    table = _effect_table(blocks)
    rng = np.random.default_rng(int(seed)); extreme = 0; remain = n
    rows = np.arange(len(blocks))[None,:]
    while remain:
        size = min(20000,remain)
        picks = rng.integers(0,len(NON_NEUTRAL_ARMS),size=(size,len(blocks)),dtype=np.int8)
        stats = np.median(table[rows,picks],axis=1)
        extreme += int(np.count_nonzero(np.abs(stats) >= abs(observed)-1e-15))
        remain -= size
    return {"candidate_arm":candidate_arm,"observed_t_stage":observed,"randomizations":n,"extreme_count":extreme,"p_value":float((extreme+1)/(n+1)),"two_sided":True,"seed":int(seed)}


def job_influence(blocks: Sequence[Mapping[str, Any]], *, candidate_arm: str = "CANONICAL") -> dict[str, Any]:
    full = float(stage_statistic(blocks,candidate_arm=candidate_arm)["t_stage"])
    jobs = sorted({str(b.get("job_id", "")) for b in blocks})
    if len(jobs) < 2 or any(not j for j in jobs): raise ValueError("job influence requires multiple job IDs")
    controls = tuple(a for a in NON_NEUTRAL_ARMS if a != candidate_arm)
    without: dict[str,float] = {}; ratios: dict[str,float] = {}
    for job in jobs:
        subset = [b for b in blocks if str(b.get("job_id")) != job]
        effects = [float(b["residuals"][candidate_arm])-_median([float(b["residuals"][a]) for a in controls]) for b in subset]
        t = _median(effects); without[job] = t; ratios[job] = abs(full-t)/max(abs(full),1e-15)
    maximum = max(ratios.values())
    return {"full_t_stage":full,"without_job":without,"influence_ratio":ratios,"max_influence_ratio":maximum,"passed":maximum<=0.5}


def _stage_report(blocks: Sequence[Mapping[str, Any]], *, seed: int, randomizations: int, p_threshold: float, effect_floor: float, candidate_arm: str = "CANONICAL") -> dict[str, Any]:
    stat = stage_statistic(blocks,candidate_arm=candidate_arm); effect=float(stat["t_stage"]); effect_pass=abs(effect)>=effect_floor
    if effect_pass:
        rnd = randomization_pvalue(blocks,seed=seed,n=randomizations,candidate_arm=candidate_arm); p=float(rnd["p_value"])
    else:
        rnd={"candidate_arm":candidate_arm,"observed_t_stage":effect,"randomizations":0,"p_value":1.0,"two_sided":True,"seed":int(seed),"short_circuited_by_effect_floor":True}; p=1.0
    return {**stat,"effect_pass":effect_pass,"p_value":p,"significance_pass":p<=p_threshold,"randomization":rnd}


def analyze_probe(discovery_blocks: Sequence[Mapping[str, Any]], replication_blocks: Sequence[Mapping[str, Any]], *, analysis_seed: int, randomizations: int = 100000, discovery_backend: str, replication_backend: str, p_threshold: float = 0.005, effect_floor: float = 0.02) -> dict[str, Any]:
    d = _stage_report(discovery_blocks,seed=_domain_seed(f"{analysis_seed:016x}","discovery"),randomizations=randomizations,p_threshold=p_threshold,effect_floor=effect_floor)
    r = _stage_report(replication_blocks,seed=_domain_seed(f"{analysis_seed:016x}","replication"),randomizations=randomizations,p_threshold=p_threshold,effect_floor=effect_floor)
    dt,rt=float(d["t_stage"]),float(r["t_stage"]); same=(dt>0 and rt>0) or (dt<0 and rt<0)
    influence=job_influence(replication_blocks); r["same_sign_as_discovery"]=same; r["job_influence"]=influence
    controls={}; control_special=False; canonical_abs=abs(rt)
    for arm in NON_NEUTRAL_ARMS[1:]:
        rep=_stage_report(replication_blocks,seed=_domain_seed(f"{analysis_seed:016x}",f"replication-{arm.lower()}"),randomizations=randomizations,p_threshold=p_threshold,effect_floor=effect_floor,candidate_arm=arm)
        eq=rep["effect_pass"] and rep["significance_pass"] and abs(float(rep["t_stage"]))>=canonical_abs-1e-15
        rep["equivalently_special"]=eq; controls[arm]=rep; control_special = control_special or eq
    r["control_leave_one_out"]=controls; r["control_specialness_pass"]=not control_special
    dpass=d["effect_pass"] and d["significance_pass"]
    rpass=r["effect_pass"] and r["significance_pass"] and same and influence["passed"] and not control_special
    d["stage_pass"]=dpass; r["stage_pass"]=rpass
    if not dpass: outcome="NULL_COMPATIBLE"
    elif not rpass: outcome="NULL_COMPATIBLE_REPLICATION_FAILED"
    elif discovery_backend==replication_backend: outcome="ANOMALY_CANDIDATE_SAME_BACKEND"
    else: outcome="ANOMALY_CANDIDATE"
    return {"schema":"r12-physics-probe-analysis-v1","discovery_backend":discovery_backend,"replication_backend":replication_backend,"independent_backend_replication":discovery_backend!=replication_backend,"discovery":d,"replication":r,"outcome":outcome,"claim_boundary":CLAIM_BOUNDARY}


def run_synthetic_preflight(packet: Mapping[str, Any], *, datasets: int = 1000, randomizations: int = 20000) -> dict[str, Any]:
    import numpy as np
    if int(datasets)<=0: raise ValueError("datasets must be positive")
    rng=np.random.default_rng(int(packet["seeds"]["synthetic_seed"])); shots=int(packet["workload"]["shots_per_pub"])
    floor=float(packet["analysis"]["effect_floor"]); threshold=float(packet["analysis"]["stage_p_threshold"])
    full=0; dpass_count=0
    def stage(si:int):
        rows=[]
        for b in range(24):
            job=b//8; path=(b//6)%4; base=0.055+float(rng.uniform(0,0.025)); common=float(rng.normal(0,0.004))+(path-1.5)*0.0015+float(rng.normal(0,0.002)); residuals={}
            for arm in NON_NEUTRAL_ARMS:
                p=min(max(base+common+0.004+float(rng.normal(0,0.0015)),0.001),0.30); residuals[arm]=int(rng.binomial(shots,p))/shots
            p=min(max(base+common,0.001),0.30); residuals["NEUTRAL"]=int(rng.binomial(shots,p))/shots
            rows.append({"block_id":b,"job_id":f"s{si}-job-{job}","residuals":residuals})
        return rows
    for i in range(int(datasets)):
        rep=analyze_probe(stage(0),stage(1),analysis_seed=int(packet["seeds"]["analysis_seed"])+i,randomizations=int(randomizations),discovery_backend="synthetic-a",replication_backend="synthetic-b",p_threshold=threshold,effect_floor=floor)
        if rep["discovery"]["stage_pass"]: dpass_count+=1
        if rep["outcome"]=="ANOMALY_CANDIDATE": full+=1
    rate=full/int(datasets)
    return {"schema":"r12-physics-probe-synthetic-preflight-v1","datasets":int(datasets),"randomizations_when_effect_floor_reached":int(randomizations),"discovery_pass_count":dpass_count,"full_anomaly_count":full,"full_anomaly_rate":rate,"maximum_allowed_rate":0.01,"passed":rate<=0.01}
