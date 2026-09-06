#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from beastbox.r12_physics_probe import (
    ARM_ORDER, CLAIM_BOUNDARY, build_echo_circuit, residual_metrics,
    sha256_json, stage_statistic, verify_ideal_echo, verify_preregistration,
)


def _name(backend: Any) -> str:
    value = getattr(backend, "name", "")
    return str(value() if callable(value) else value)


def find_connected_paths(edges: Iterable[tuple[int,int]], *, length: int = 12, limit: int = 96) -> list[tuple[int,...]]:
    adjacency: dict[int,set[int]] = {}
    for a0,b0 in edges:
        a,b=int(a0),int(b0)
        if a==b: continue
        adjacency.setdefault(a,set()).add(b); adjacency.setdefault(b,set()).add(a)
    found: list[tuple[int,...]]=[]; seen:set[tuple[int,...]]=set()
    def dfs(path:list[int]) -> None:
        if len(found)>=limit: return
        if len(path)==length:
            p=tuple(path); canonical=min(p,tuple(reversed(p)))
            if canonical not in seen: seen.add(canonical); found.append(canonical)
            return
        for nxt in sorted(adjacency.get(path[-1],())):
            if nxt in path: continue
            path.append(nxt); dfs(path); path.pop()
            if len(found)>=limit: return
    for start in sorted(adjacency):
        dfs([start])
        if len(found)>=limit: break
    return found


def _domain_seed(seed:int,text:str)->int:
    return int(hashlib.sha256(f"{int(seed)}:{text}".encode()).hexdigest()[:16],16)


def balanced_block_plan(stage:str, paths:Sequence[Sequence[int]], *, arm_order_seed:int)->list[dict[str,Any]]:
    if stage not in {"discovery","replication"}: raise ValueError("unknown stage")
    if len(paths)<4: raise ValueError("at least four connected 12-qubit paths are required")
    selected=[tuple(int(q) for q in path) for path in paths[:4]]
    if any(len(p)!=12 or len(set(p))!=12 for p in selected): raise ValueError("invalid physical path")
    plan=[]; bid=0
    for repeat in range(3):
        for pi,path in enumerate(selected):
            for orientation in ("forward","reverse"):
                physical=path if orientation=="forward" else tuple(reversed(path))
                order=list(ARM_ORDER); random.Random(_domain_seed(arm_order_seed,f"{stage}:{bid}:arms")).shuffle(order)
                plan.append({"stage":stage,"block_id":bid,"repeat":repeat,"path_index":pi,"base_path":list(path),"physical_path":list(physical),"orientation":orientation,"arm_order":order}); bid+=1
    if len(plan)!=24: raise AssertionError("balanced plan must contain 24 blocks")
    return plan


def chunk_block_plan(plan:Sequence[Mapping[str,Any]], *, blocks_per_job:int=8)->list[list[dict[str,Any]]]:
    n=int(blocks_per_job)
    if n<=0: raise ValueError("blocks_per_job must be positive")
    return [[dict(v) for v in plan[i:i+n]] for i in range(0,len(plan),n)]


def sanitize_counts(counts:Mapping[str,int], *, shots:int=4096)->dict[str,int]:
    out:dict[str,int]={}
    for raw,value in counts.items():
        key=str(raw).replace(" ","")
        if len(key)!=12 or any(bit not in "01" for bit in key): raise ValueError("invalid 12-bit outcome")
        n=int(value)
        if n<0: raise ValueError("negative count")
        out[key]=out.get(key,0)+n
    if sum(out.values())!=int(shots): raise ValueError("shot total mismatch")
    return dict(sorted(out.items()))


def _coupling_edges(backend:Any)->list[tuple[int,int]]:
    coupling=getattr(backend,"coupling_map",None)
    if coupling is None:
        target=getattr(backend,"target",None)
        if target is not None and hasattr(target,"build_coupling_map"): coupling=target.build_coupling_map()
    if coupling is None: raise RuntimeError(f"backend {_name(backend)} has no coupling map")
    edges=coupling.get_edges() if hasattr(coupling,"get_edges") else coupling
    return [(int(a),int(b)) for a,b in edges]


def _rank_paths(backend:Any, paths:Sequence[tuple[int,...]])->list[tuple[int,...]]:
    try: props=backend.properties()
    except Exception: props=None
    def cost(path:tuple[int,...]):
        if props is None: return (0.0,path)
        score=0.0
        for q in path:
            try: score+=float(props.readout_error(q))
            except Exception: pass
        for a,b in zip(path,path[1:]):
            try: score+=float(props.gate_error("cx",[a,b]))
            except Exception:
                try: score+=float(props.gate_error("ecr",[a,b]))
                except Exception: pass
        return (score,path)
    return sorted(paths,key=cost)


def select_stage_backends_with_paths(backends:Sequence[Any], *, minimum_qubits:int=12)->dict[str,Any]:
    eligible=[]
    for backend in backends:
        try:
            status=backend.status()
            if int(getattr(backend,"num_qubits",0))<minimum_qubits or not bool(getattr(status,"operational",False)): continue
            paths=_rank_paths(backend,find_connected_paths(_coupling_edges(backend),length=12,limit=96))
            if len(paths)<4: continue
            eligible.append((int(getattr(status,"pending_jobs",10**9)),_name(backend),backend,paths[:4]))
        except Exception: continue
    if not eligible: raise RuntimeError("no operational IBM backend exposes four connected 12-qubit paths")
    eligible.sort(key=lambda x:(x[0],x[1])); d=eligible[0]; r=eligible[1] if len(eligible)>1 else d
    return {"discovery":d[2],"replication":r[2],"discovery_paths":d[3],"replication_paths":r[3],"independent_backend_replication":d[1]!=r[1]}


def _write_json(path:Path,value:object)->None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")


def _file_sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256s(root:Path)->None:
    files=sorted(p for p in root.rglob("*") if p.is_file() and p.name!="SHA256SUMS")
    (root/"SHA256SUMS").write_text("".join(f"{_file_sha(p)}  {p.relative_to(root).as_posix()}\n" for p in files),encoding="utf-8")


def _compile_block(backend:Any, block:Mapping[str,Any], arms:Mapping[str,Sequence[float]], *, seed:int):
    try: from qiskit import transpile
    except ImportError as exc: raise ImportError("IBM runner requires quantum extra") from exc
    circuits=[]; metadata=[]; physical=[int(q) for q in block["physical_path"]]
    for arm in block["arm_order"]:
        source=build_echo_circuit(arms[arm],measure=True)
        compiled=transpile(source,backend=backend,optimization_level=0,seed_transpiler=int(seed),initial_layout=physical)
        src={str(k):int(v) for k,v in source.count_ops().items()}; comp={str(k):int(v) for k,v in compiled.count_ops().items()}
        if src.get("cx",0)!=22: raise RuntimeError("source echo CX budget changed")
        if int(compiled.depth())<=0 or int(compiled.size())<=0: raise RuntimeError("compiled echo collapsed")
        circuits.append(compiled); metadata.append({"stage":block["stage"],"block_id":int(block["block_id"]),"arm":arm,"physical_path":physical,"orientation":block["orientation"],"source_depth":int(source.depth()),"source_size":int(source.size()),"source_count_ops":src,"compiled_depth":int(compiled.depth()),"compiled_size":int(compiled.size()),"compiled_count_ops":comp})
    non=[m for m in metadata if m["arm"]!="NEUTRAL"]
    if len({json.dumps(m["compiled_count_ops"],sort_keys=True) for m in non})!=1: raise RuntimeError("non-neutral compiled gate budgets diverged within block")
    return circuits,metadata


def _runtime_service():
    try: from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc: raise ImportError("IBM runner requires qiskit-ibm-runtime") from exc
    token=os.environ.get("IBM_QUANTUM_TOKEN","").strip()
    if not token: raise RuntimeError("IBM_QUANTUM_TOKEN is empty")
    kwargs={"channel":"ibm_quantum_platform","token":token}; instance=os.environ.get("IBM_QUANTUM_INSTANCE","").strip()
    if instance: kwargs["instance"]=instance
    return QiskitRuntimeService(**kwargs)


def _available_backends(service:Any)->list[Any]:
    try: return list(service.backends(simulator=False,operational=True,min_num_qubits=12))
    except TypeError:
        out=[]
        for b in service.backends():
            try:
                config=b.configuration()
                if int(getattr(b,"num_qubits",0))>=12 and bool(getattr(b.status(),"operational",False)) and not bool(getattr(config,"simulator",False)): out.append(b)
            except Exception: pass
        return out


def _submit_chunk(*,service:Any,backend:Any,stage:str,chunk:Sequence[Mapping[str,Any]],arms:Mapping[str,Sequence[float]],prereg_sha:str,source_commit:str,shots:int,out_root:Path,job_index:int)->dict[str,Any]:
    try: from qiskit_ibm_runtime import SamplerV2
    except ImportError as exc: raise ImportError("IBM runner requires qiskit-ibm-runtime") from exc
    circuits=[]; meta=[]
    for block in chunk:
        seed=_domain_seed(int(prereg_sha[:16],16),f"{stage}:{block['block_id']}:transpile")
        c,m=_compile_block(backend,block,arms,seed=seed); circuits.extend(c); meta.extend(m)
    tags=["r12-physics-probe-001",stage,f"src-{source_commit[:8]}",f"prereg-{prereg_sha[:8]}",f"job-{job_index}"]
    sampler=SamplerV2(mode=backend); sampler.options.environment.job_tags=tags
    job=sampler.run(circuits,shots=int(shots)); job_id=str(job.job_id())
    root=out_root/"measured"/stage/f"job-{job_index:02d}-{job_id}"
    _write_json(root/"submission.json",{"schema":"r12-physics-probe-ibm-submission-v1","stage":stage,"backend":_name(backend),"job_id":job_id,"pub_count":len(circuits),"shots_per_pub":int(shots),"block_ids":[int(v["block_id"]) for v in chunk],"pub_metadata":meta,"job_tags":tags,"preregistration_sha256":prereg_sha,"source_commit":source_commit,"credential_material_recorded":False,"claim_boundary":CLAIM_BOUNDARY})
    verified=service.job(job_id); verified_tags=list(getattr(verified,"tags",[]) or [])
    if "r12-physics-probe-001" not in verified_tags or f"prereg-{prereg_sha[:8]}" not in verified_tags: raise RuntimeError("IBM tags failed round-trip verification")
    results=list(job.result())
    if len(results)!=len(meta): raise RuntimeError("IBM PUB result count mismatch")
    pubs=[]; blocks:dict[int,dict[str,Any]]={}
    for idx,(pub,m) in enumerate(zip(results,meta,strict=True)):
        counts=sanitize_counts(pub.join_data().get_counts(),shots=shots); metrics=residual_metrics(counts,shots=shots)
        row={"pub_index":idx,**m,"counts":counts,"counts_sha256":sha256_json(counts),"metrics":metrics}; pubs.append(row)
        bid=int(m["block_id"]); block=blocks.setdefault(bid,{"block_id":bid,"job_id":job_id,"backend":_name(backend),"physical_path":m["physical_path"],"orientation":m["orientation"],"residuals":{}}); block["residuals"][m["arm"]]=metrics["residual"]
    for block in blocks.values():
        if set(block["residuals"])!=set(ARM_ORDER): raise RuntimeError("matched block missing arm")
    _write_json(root/"results.json",{"schema":"r12-physics-probe-ibm-results-v1","stage":stage,"backend":_name(backend),"job_id":job_id,"pubs":pubs,"blocks":[blocks[k] for k in sorted(blocks)],"claim_boundary":CLAIM_BOUNDARY})
    _write_json(root/"verification.json",{"schema":"r12-physics-probe-ibm-verification-v1","stage":stage,"backend":_name(backend),"job_id":job_id,"verified_tags":sorted(set(verified_tags)),"pub_count":len(results),"shots_per_pub":int(shots),"credential_material_recorded":False,"preregistration_sha256":prereg_sha})
    _write_sha256s(root)
    return {"job_id":job_id,"backend":_name(backend),"stage":stage,"block_count":len(chunk),"pub_count":len(results),"path":str(root)}


def _is_payload_size_error(exc:Exception)->bool:
    text=str(exc).lower(); return any(token in text for token in ("pub","payload","too large","maximum","exceed","limit"))


def _aggregate_stage_blocks(out_root:Path,stage:str)->list[dict[str,Any]]:
    blocks={}
    for p in sorted((out_root/"measured"/stage).glob("job-*/results.json")):
        for block in json.loads(p.read_text())["blocks"]:
            bid=int(block["block_id"])
            if bid in blocks: raise RuntimeError(f"duplicate {stage} block {bid}")
            blocks[bid]=block
    if set(blocks)!=set(range(24)): raise RuntimeError(f"{stage} did not produce block IDs 0..23")
    return [blocks[i] for i in range(24)]


def _seal_discovery_direction(out_root:Path,prereg_sha:str)->dict[str,Any]:
    stat=stage_statistic(_aggregate_stage_blocks(out_root,"discovery")); t=float(stat["t_stage"]); sign=1 if t>0 else -1 if t<0 else 0
    seal={"schema":"r12-physics-probe-discovery-direction-seal-v1","preregistration_sha256":prereg_sha,"block_count":24,"t_discovery":t,"sign":sign,"sealed_before_replication_submission":True}; seal["seal_sha256"]=sha256_json(seal); _write_json(out_root/"derived"/"discovery-direction-seal.json",seal); return seal


def run_hardware(*,prereg_path:Path,prereg_sha_path:Path,out_root:Path)->dict[str,Any]:
    packet=json.loads(prereg_path.read_text()); prereg_sha=prereg_sha_path.read_text().strip().split()[0]; verify_preregistration(packet,prereg_sha)
    arms={name:tuple(float(v) for v in packet["arms"][name]) for name in ARM_ORDER}; ideal=verify_ideal_echo(arms,tolerance=1e-12)
    if not ideal["passed"]: raise RuntimeError("exact standard-QM echo precondition failed before IBM submission")
    service=_runtime_service(); selected=select_stage_backends_with_paths(_available_backends(service),minimum_qubits=12)
    source_commit=str(packet["source_commit"]); shots=int(packet["workload"]["shots_per_pub"]); jobs=[]; backend_receipts={}
    for stage in ("discovery","replication"):
        backend=selected[stage]; paths=selected[f"{stage}_paths"]; plan=balanced_block_plan(stage,paths,arm_order_seed=int(packet["seeds"]["arm_order_seed"])); queue=chunk_block_plan(plan,blocks_per_job=8); backend_receipts[stage]={"backend":_name(backend),"paths":[list(p) for p in paths],"block_plan":plan}; ji=0
        while queue:
            chunk=queue.pop(0)
            try: receipt=_submit_chunk(service=service,backend=backend,stage=stage,chunk=chunk,arms=arms,prereg_sha=prereg_sha,source_commit=source_commit,shots=shots,out_root=out_root,job_index=ji)
            except Exception as exc:
                if len(chunk)>1 and _is_payload_size_error(exc):
                    mid=len(chunk)//2; queue=[chunk[:mid],chunk[mid:]]+queue; continue
                raise
            jobs.append(receipt); ji+=1
        _aggregate_stage_blocks(out_root,stage)
        if stage=="discovery": _seal_discovery_direction(out_root,prereg_sha)
    receipt={"schema":"r12-physics-probe-hardware-run-v1","preregistration_sha256":prereg_sha,"source_commit":source_commit,"jobs":jobs,"stage_backends":{"discovery":_name(selected["discovery"]),"replication":_name(selected["replication"])},"independent_backend_replication":bool(selected["independent_backend_replication"]),"planned_hardware_shots":shots*48*6,"backend_receipts":backend_receipts,"credential_material_recorded":False,"claim_boundary":CLAIM_BOUNDARY}; _write_json(out_root/"hardware-run.json",receipt); return receipt


def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--prereg",type=Path,required=True); p.add_argument("--prereg-sha",type=Path,required=True); p.add_argument("--out",type=Path,default=Path("experiments/r12-physics-probe-001")); a=p.parse_args(); print(json.dumps(run_hardware(prereg_path=a.prereg,prereg_sha_path=a.prereg_sha,out_root=a.out),sort_keys=True))

if __name__=="__main__": main()
