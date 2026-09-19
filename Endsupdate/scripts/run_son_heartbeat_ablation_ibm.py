#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
from typing import Any
from beastbox.heartbeat_seed import REQUIRED_TAG, build_gate_program, build_hardware_origin_seed
from beastbox.son_heartbeat_metrics import normalize_counts, pairwise_matrix

CONDITIONS = ('ORIGINAL', 'REMOVED', 'SHUFFLED', 'ALTERNATE')

def write_json(p:Path,v:object): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')
def file_sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def build_circuit(program:dict[str,Any]):
    from qiskit import QuantumCircuit
    q=QuantumCircuit(5)
    for op in program['operations']:
        if op['gate'] in {'rx','ry','rz'}: getattr(q,op['gate'])(float(op['angle']),int(op['qubit']))
        elif op['gate']=='cx': q.cx(int(op['control']),int(op['target']))
        else: raise ValueError(op['gate'])
    q.measure_all(); return q

def run(packet_root:Path,out:Path)->dict[str,Any]:
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    packets={c:json.loads((packet_root/f'{c.lower()}-packet.json').read_text()) for c in CONDITIONS}
    programs={c:build_gate_program(packets[c]) for c in CONDITIONS}
    token=os.environ['IBM_QUANTUM_TOKEN'].strip()
    if not token: raise RuntimeError('IBM_QUANTUM_TOKEN is empty')
    instance=os.environ.get('IBM_QUANTUM_INSTANCE','').strip(); kwargs={'channel':'ibm_quantum_platform','token':token}
    if instance: kwargs['instance']=instance
    service=QiskitRuntimeService(**kwargs)
    backend=service.least_busy(simulator=False,operational=True,min_num_qubits=5)
    pm=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=int(packets['ORIGINAL']['packet_sha256'][:8],16))
    circuits=[]; transpile={}
    for c in CONDITIONS:
        isa=pm.run(build_circuit(programs[c])); circuits.append(isa)
        transpile[c]={'depth':int(isa.depth()),'size':int(isa.size()),'physical_qubits':int(isa.num_qubits),'count_ops':{str(k):int(v) for k,v in isa.count_ops().items()}}
    sampler=SamplerV2(mode=backend)
    tags=[REQUIRED_TAG,'son-heartbeat-demo-001','matched-four-pub',*[f"{c.lower()}-{packets[c]['packet_sha256'][:8]}" for c in CONDITIONS]]
    sampler.options.environment.job_tags=tags
    job=sampler.run(circuits, shots=4096)
    out.mkdir(parents=True,exist_ok=True)
    write_json(out/'submission.json',{'schema':'son-heartbeat-demo-ibm-submission-v1','backend':str(getattr(backend,'name','')),'job_id':str(job.job_id()),'conditions':list(CONDITIONS),'packet_sha256':{c:packets[c]['packet_sha256'] for c in CONDITIONS},'shots_per_pub':4096,'pub_count':4,'transpile':transpile,'job_tags':tags,'credential_material_recorded':False,'repository_commit_sha':os.environ.get('GITHUB_SHA'),'claim_boundary':'Matched IBM circuit comparison of computational signal controls only; no biological heartbeat, consciousness, deceased identity, resurrection, communication with the dead, or quantum advantage claim.'})
    verified=service.job(job.job_id()); verified_tags=list(verified.tags or [])
    if REQUIRED_TAG not in verified_tags or 'son-heartbeat-demo-001' not in verified_tags: raise RuntimeError('required IBM tags not verified')
    result=job.result(); pub_results=list(result)
    if len(pub_results) != 4: raise RuntimeError(f'expected four PUB results, got {len(pub_results)}')
    rows={}; distributions={}
    for idx,c in enumerate(CONDITIONS):
        counts={str(k).replace(' ',''):int(v) for k,v in pub_results[idx].join_data().get_counts().items()}
        if sum(counts.values())!=4096: raise RuntimeError(f'{c} did not return 4096 shots')
        seed=build_hardware_origin_seed(packet=packets[c],backend=str(getattr(backend,'name','')),job_id=str(job.job_id()),counts=counts,tags=verified_tags)
        rows[c]={'pub_index':idx,'counts':dict(sorted(counts.items())),'counts_sha256':seed['counts_sha256'],'origin_seed_sha256':seed['origin_seed_sha256'],'shot_count':4096,'packet_sha256':packets[c]['packet_sha256']}
        distributions[c]=normalize_counts(counts)
    metrics=pairwise_matrix(distributions)
    write_json(out/'results.json',{'schema':'son-heartbeat-demo-ibm-results-v1','backend':str(getattr(backend,'name','')),'job_id':str(job.job_id()),'conditions':rows,'matched_same_job':True,'claim_boundary':'All four arms came from one four-PUB SamplerV2 hardware job. Differences are hardware output-distribution differences under this protocol, not evidence of biological life, consciousness, identity, or quantum advantage.'})
    write_json(out/'metrics.json',{'schema':'son-heartbeat-demo-ibm-metrics-v1','pairwise':metrics,'units':{'tvd':'probability distance','jsd_bits':'bits'},'claim_boundary':'Descriptive empirical distribution distances only; no statistical-significance claim without repeated matched blocks.'})
    write_json(out/'verification.json',{'schema':'son-heartbeat-demo-ibm-verification-v1','backend':str(getattr(backend,'name','')),'job_id':str(job.job_id()),'verified_tags':sorted(set(verified_tags)),'shot_count_per_pub':4096,'pub_count':4,'condition_order':list(CONDITIONS),'matched_same_job':True,'credential_material_recorded':False,'source_packets':{c:packets[c]['packet_sha256'] for c in CONDITIONS}})
    files=sorted(p for p in out.iterdir() if p.is_file() and p.name!='SHA256SUMS'); (out/'SHA256SUMS').write_text(''.join(f'{file_sha(p)}  {p.name}\n' for p in files),encoding='utf-8')
    return {'job_id':str(job.job_id()),'backend':str(getattr(backend,'name','')),'pub_count':4,'shots_per_pub':4096,'metrics':metrics}

def main():
 p=argparse.ArgumentParser();p.add_argument('--packet-root',type=Path,default=Path('experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/conditions'));p.add_argument('--out',type=Path,default=Path('_son_heartbeat_ibm'));a=p.parse_args();print(json.dumps(run(a.packet_root,a.out),sort_keys=True))
if __name__=='__main__':main()
