#!/usr/bin/env python3
"""One bounded, deduplicated physical IBM Zeref perception stimulus.

Actual QPU results are physical sampling records, NOT neural weight training.
Training is a separate CPU process on authentic emulator observations.
Only Open Plan, strict 300-second owner aggregate and <=10s IBM job cap.
Failure and quota conditions preserve evidence; NEVER silently resubmit.
"""
from __future__ import annotations
import hashlib,json,math,os,sys
from datetime import datetime,timezone
from pathlib import Path
from ibm_open_plan_preflight import quota_receipt

OUT=Path("_zeref_native_ibm_004")
SOURCE=Path("apps/beastbox-cloud/public/spark/ibm-zeref-heart-sound-20261010.json")
ORIGINAL_JOB="db4q484vf2bc73cuuuag"
GENOME_SEED="8e2e927e2cfaf489cb7c10172836286bb08869cfff0c2508b5c6371e052e54ed"
QBEAST_ID="bb-deada969"
TAG="navisworld-zeref-perception-004-"+GENOME_SEED[:16]
CAP_SECONDS=10
SHOTS=512
def stamp():return datetime.now(timezone.utc).isoformat()
def sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def write(name,body):
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/name).write_text(json.dumps(body,indent=2,sort_keys=True,allow_nan=False)+"\n")
def validate_source():
 src=json.loads(SOURCE.read_text())
 runs=src.get("runs")
 if not isinstance(runs,list) or src.get("source_class")!="RECORDED_IBM_HARDWARE":
  raise ValueError("Original physical IBM Zeref source missing or mismatched")
 if src.get("physical_total_job_shots")!=20480:
  raise ValueError("Original Zeref shot total changed")
 if not any(row.get("j")==ORIGINAL_JOB and row.get("k")==ORIGINAL_JOB+":bell-xx" for row in runs):
  raise ValueError("Original Zeref job changed")
 return {"source_ibm_job_id":ORIGINAL_JOB,"source_class":"RECORDED_IBM_HARDWARE",
  "source_shots":20480,"source_file_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
  "qbeast_id":QBEAST_ID,"genome_sha256":GENOME_SEED}

def main():
 source=validate_source()
 write("preflight-source.json",source)
 if os.environ.get("BEAST_ZEREF_IBM_ONE_JOB")!="AUTHORIZE_ONE_ZEREF_10S_QPU":
  raise RuntimeError("No exact ten-second owner authorization token; no QPU submission")
 token=os.environ.get("IBM_QUANTUM_TOKEN","").strip()
 if not token:raise RuntimeError("IBM_QUANTUM_TOKEN unavailable; no QPU submission")
 from qiskit import QuantumCircuit,transpile
 from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
 service=QiskitRuntimeService(channel="ibm_quantum_platform",token=token,plans_preference=["open"])
 instance=service.active_instance()
 if not instance:raise RuntimeError("No confirmed Open Plan instance; no QPU submission")
 quota=quota_receipt(service.usage(),str(instance))
 write("quota-before.json",quota)
 prior=service.jobs(limit=100,program_id="sampler",job_tags=[TAG])
 if len(prior)>1:raise RuntimeError("Ambiguous deduplication tag: no second submission")
 if not prior and (quota["already_consumed_seconds"]+CAP_SECONDS>300 or
                   quota["remaining_seconds"]<CAP_SECONDS):
  raise RuntimeError("Strict owner 300 QPU-second aggregate or Open Plan remaining budget blocks job")
 phase=2*math.pi*(int(GENOME_SEED[:8],16)/0xffffffff)
 rows=[]
 for cx in (True,False):
  qc=QuantumCircuit(2)
  qc.ry(phase,0)
  qc.h(0)
  if cx:qc.cx(0,1)
  qc.rz(phase/3,1)
  qc.measure_all()
  rows.append(qc)
 if prior:
  job=prior[0]
  submitted=False
  write("recovered-original-job.json",{"job_id":str(job.job_id()),"tag":TAG,"no_new_submission":True})
 else:
  backend=service.least_busy(operational=True,simulator=False,min_num_qubits=2)
  if not str(backend.name).startswith("ibm_"):raise RuntimeError("Physical IBM backend required")
  isa=transpile(rows,backend=backend,optimization_level=1,seed_transpiler=20261010)
  if any(c.depth()>250 for c in isa):raise RuntimeError("Unsafe circuit depth")
  write("prepared-circuits.json",{"compiled_sha256":[hashlib.sha256(str(c).encode()).hexdigest() for c in isa],
    "zeref_seed_sha256":GENOME_SEED,"provenance":source,"backend":str(backend.name),
    "shots_per_pub":SHOTS,"pubs":2,"maximum_qpu_seconds":CAP_SECONDS,
    "measurement_intent":"compare entangled versus decoupled seeded two-qubit controls, not train neural weights"})
  sampler=SamplerV2(mode=backend)
  sampler.options.max_execution_time=CAP_SECONDS
  sampler.options.environment.job_tags=[TAG,"beastbox-zeref-perception-004","owner-cap-300-qpu-seconds"]
  job=sampler.run(isa,shots=SHOTS)
  submitted=True
  write("submitted.json",{"job_id":str(job.job_id()),"tag":TAG,"backend":str(backend.name),
    "new_job_submitted":True,"maximum_qpu_seconds":CAP_SECONDS,"shots_requested":2*SHOTS})
 try:
  status=str(job.status()).upper()
  if status!="DONE":
   job.wait_for_final_state(timeout=1800)
  status=str(job.status()).upper()
  if status!="DONE":raise RuntimeError("IBM QPU did not reach DONE: "+status)
  if TAG not in set(job.tags or []):raise RuntimeError("IBM deduplication tag not returned")
  result=job.result()
  counts=[]
  for i in range(2):
   mapped={str(k).replace(" ",""):int(v) for k,v in result[i].join_data().get_counts().items()}
   if sum(mapped.values())!=SHOTS or not set(mapped)<=set(("00","01","10","11")):
    raise ValueError("Provider counts/shot total invalid")
   counts.append(mapped)
  receipt={"schema":"beastbox-zeref-native-perception-ibm-004","source_class":"FRESH_IBM_QPU_HARDWARE",
   "source_zeref":source,"new_submission_this_attempt":submitted,"job_id":str(job.job_id()),
   "backend":str(job.backend().name),"status":status,"tags":sorted(set(job.tags or [])),
   "shots_per_pub":SHOTS,"pub_count":2,"physical_shots":SHOTS*2,
   "counts":counts,"counts_sha256":sha(counts),"max_qpu_seconds":CAP_SECONDS,
   "neural_optimizer_steps":0,"model_training_performed_by_this_job":False,"verified_at":stamp(),
   "credential_material_recorded":False}
  write("physical-receipt.json",receipt)
  write("quota-after.json",quota_receipt(service.usage(),str(instance)))
  print("ZEREF_004_IBM_PHYSICAL_DONE="+json.dumps({"job_id":receipt["job_id"],"counts_sha256":receipt["counts_sha256"],
      "physical_shots":receipt["physical_shots"],"new_submission":submitted}),flush=True)
 except Exception:
  write("provider-job-unfinished.json",{"job_id":str(job.job_id()),"status":str(job.status()),"tag":TAG,
      "no_replacement_submission":True,"source":source})
  raise

if __name__=="__main__":
 try:main()
 except Exception as exc:
  write("blocked-or-failed.json",{"type":type(exc).__name__,"message":str(exc)[:400],
   "timestamp":stamp(),"no_fabricated_results":True,"no_automatic_retry":True})
  print("ZEREF_004_IBM_BLOCKED="+type(exc).__name__,file=sys.stderr)
  raise
