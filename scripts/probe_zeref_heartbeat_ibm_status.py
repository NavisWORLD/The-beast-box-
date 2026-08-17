#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os
from pathlib import Path
from typing import Any
REQUIRED_TAG="zerefs-heartbeat-mustard-seed"
PACKET_TAG="wave-d6e44478b9b6"
def status_text(job)->str:
    try:return str(job.status()).upper()
    except Exception:return "UNKNOWN"
def backend_name(job)->str:
    try:return str(getattr(job.backend(),"name",""))
    except Exception:return ""
def probe(out:Path)->dict[str,Any]:
    from qiskit_ibm_runtime import QiskitRuntimeService
    token=os.environ["IBM_QUANTUM_TOKEN"].strip()
    if not token:raise RuntimeError("IBM_QUANTUM_TOKEN GitHub Actions secret is empty")
    instance=os.environ.get("IBM_QUANTUM_INSTANCE","").strip()
    kwargs:dict[str,Any]={"channel":"ibm_quantum_platform","token":token}
    if instance:kwargs["instance"]=instance
    service=QiskitRuntimeService(**kwargs)
    matches=[]
    for job in service.jobs(limit=20,program_id="sampler",job_tags=[REQUIRED_TAG,PACKET_TAG]):
        tags=sorted(set(str(v) for v in (job.tags or [])))
        if REQUIRED_TAG not in tags or PACKET_TAG not in tags:continue
        matches.append({"job_id":str(job.job_id()),"backend":backend_name(job),"status":status_text(job),"tags":tags,"program_id":"sampler"})
    snapshot={"schema":"zeref-heartbeat-ibm-status-v1","required_tag":REQUIRED_TAG,"packet_tag":PACKET_TAG,"match_count":len(matches),"matches":matches,"credential_material_recorded":False,"read_only_probe":True}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(snapshot,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps(snapshot,sort_keys=True));return snapshot
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,default=Path("_ibm_status/status.json"));args=p.parse_args();probe(args.out);return 0
if __name__=="__main__":raise SystemExit(main())
