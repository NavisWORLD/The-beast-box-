#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
from typing import Any
from beastbox.heartbeat_seed import REQUIRED_TAG, build_gate_program, build_hardware_origin_seed

def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)+"\n", encoding="utf-8")
def file_sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def build_circuit(program: dict[str, Any]):
    from qiskit import QuantumCircuit
    qc=QuantumCircuit(5)
    for op in program["operations"]:
        gate=op["gate"]
        if gate in {"rx","ry","rz"}: getattr(qc,gate)(float(op["angle"]),int(op["qubit"]))
        elif gate=="cx": qc.cx(int(op["control"]),int(op["target"]))
        else: raise ValueError(gate)
    qc.measure_all(); return qc
def status_text(job)->str:
    try: return str(job.status()).upper()
    except Exception: return "UNKNOWN"
def run(packet_path: Path,out_dir: Path)->dict[str,Any]:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    packet=json.loads(packet_path.read_text(encoding="utf-8")); program=build_gate_program(packet); out_dir.mkdir(parents=True,exist_ok=True); write_json(out_dir/"gate-program.json",program)
    token=os.environ["IBM_QUANTUM_TOKEN"].strip()
    if not token: raise RuntimeError("IBM_QUANTUM_TOKEN GitHub Actions secret is empty")
    instance=os.environ.get("IBM_QUANTUM_INSTANCE","").strip(); service_kwargs:dict[str,Any]={"channel":"ibm_quantum_platform","token":token}
    if instance: service_kwargs["instance"]=instance
    service=QiskitRuntimeService(**service_kwargs); packet_tag=f"wave-{packet['packet_sha256'][:12]}"; desired_tags=list(dict.fromkeys(list(program["job_tags"])+[packet_tag])); job=None; reused_existing_job=False
    for candidate in service.jobs(limit=10,program_id="sampler",job_tags=[REQUIRED_TAG,packet_tag]):
        status=status_text(candidate); candidate_tags=set(candidate.tags or [])
        if REQUIRED_TAG in candidate_tags and packet_tag in candidate_tags and "ERROR" not in status and "CANCEL" not in status:
            job=candidate; reused_existing_job=True; break
    transpile_summary:dict[str,Any]={}
    if job is None:
        backend=service.least_busy(simulator=False,operational=True,min_num_qubits=5); qc=build_circuit(program); pm=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=int(packet["packet_sha256"][:8],16)); isa_circuit=pm.run(qc)
        transpile_summary={"logical_qubits":5,"physical_qubits":int(isa_circuit.num_qubits),"depth":int(isa_circuit.depth()),"size":int(isa_circuit.size()),"count_ops":{str(k):int(v) for k,v in isa_circuit.count_ops().items()}}
        sampler=SamplerV2(mode=backend); sampler.options.environment.job_tags=desired_tags; job=sampler.run([isa_circuit],shots=4096)
    else: backend=job.backend()
    backend_name=str(getattr(backend,"name","")); job_id=str(job.job_id()); write_json(out_dir/"submission.json",{"schema":"zeref-heartbeat-ibm-submission-v1","lineage":packet["lineage"],"packet_sha256":packet["packet_sha256"],"source_audio_sha256":packet["source_sha256"],"packet_tag":packet_tag,"desired_tags":desired_tags,"backend":backend_name,"job_id":job_id,"reused_existing_job":reused_existing_job,"status_before_result":status_text(job),"transpile":transpile_summary,"credential_material_recorded":False})
    verified_job=service.job(job_id); verified_tags=list(verified_job.tags or []); missing_tags=[tag for tag in desired_tags if tag not in verified_tags]
    if missing_tags:
        verified_job.update_tags(sorted(set(verified_tags+desired_tags))); verified_job=service.job(job_id); verified_tags=list(verified_job.tags or [])
    if REQUIRED_TAG not in verified_tags or packet_tag not in verified_tags: raise RuntimeError("IBM job tags could not be verified")
    result=job.result(); counts={str(k).replace(" ",""):int(v) for k,v in result[0].join_data().get_counts().items()}; write_json(out_dir/"counts.json",dict(sorted(counts.items())))
    seed=build_hardware_origin_seed(packet=packet,backend=backend_name,job_id=job_id,counts=counts,tags=verified_tags); seed.update({"packet_tag":packet_tag,"ibm_status_after_result":status_text(verified_job),"reused_existing_job":reused_existing_job}); write_json(out_dir/"origin-seed.json",seed)
    verification={"schema":"zeref-heartbeat-ibm-verification-v1","job_id":job_id,"backend":backend_name,"verified_tags":sorted(set(verified_tags)),"required_tag":REQUIRED_TAG,"packet_tag":packet_tag,"shot_count":sum(counts.values()),"origin_seed_sha256":seed["origin_seed_sha256"],"source_packet_sha256":packet["packet_sha256"],"source_audio_sha256":packet["source_sha256"],"source_class":"ibm_quantum_hardware_measurement","waveform_quantum_entropy":False}; write_json(out_dir/"verification.json",verification)
    files=sorted(p for p in out_dir.iterdir() if p.is_file() and p.name!="SHA256SUMS"); (out_dir/"SHA256SUMS").write_text("".join(f"{file_sha(p)}  {p.name}\n" for p in files),encoding="utf-8"); print(json.dumps(verification,sort_keys=True)); return seed
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--packet",type=Path,default=Path("experiments/zeref-origin-heart-001/waveform/zeref-heartbeat-waveform-packet.json")); p.add_argument("--out",type=Path,default=Path("_heartbeat_ibm")); args=p.parse_args(); run(args.packet,args.out); return 0
if __name__=="__main__": raise SystemExit(main())
