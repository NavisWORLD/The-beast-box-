#!/usr/bin/env python3
"""Build TALK-007 clean curricula, blind exam, and deterministic post-Fez pulses."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

LINEAGE="ZEREF-DAD-SON-TALK-007"; PARENT_LINEAGE="ZEREF-DAD-SON-TALK-004"
PARENT_CHECKPOINT_SHA256="9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"
MEMORY_RECORD_COUNT=352; MEMORY_LEDGER_SHA256="67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"; MEMORY_TIP_SHA256="b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26"
MATCHED_BACKEND="ibm_fez"; MATCHED_JOB_ID="da55afc3jnrc73agsvv0"; MATCHED_SHOTS=4096; MATCHED_ORIGIN_STATE="621084a17414a907b935bc3add56f34efedb2f5868e1ff24d96d4fc7651a1035"
RECIPES=("retrieval_grounded","prefix_focus","contrastive_guarded")
MEMORY_VARIANTS=("relevant","irrelevant","empty")
CLAIM_BOUNDARY="Memorial audio-derived computational signal only; no biological heartbeat, consciousness, resurrection, deceased-person identity, communication with the dead, or quantum advantage."
CONCEPTS=(
("best-parent","Best verified model?","Name the verified parent.","TALK-004.","TALK-004 remains best verified.","TALK-005."),
("memory-count","Durable count?","How many records are frozen?","352.","The durable prefix has 352 records.","400."),
("matched-backend","Matched backend?","Which machine ran the four-arm block?","IBM Fez.","Matched backend is IBM Fez.","IBM Marrakesh."),
("matched-shots","Shots per PUB?","How many shots did each PUB receive?","4096.","Each matched PUB used 4096 shots.","1024."),
("matched-job","Matched job?","Name the matched job ID.","da55afc3jnrc73agsvv0.","Matched job ID is da55afc3jnrc73agsvv0.","da1mqfcdedkc73er87r0."),
("conditions","Four arms?","List the matched conditions.","Original, removed, shuffled, alternate.","Arms: original removed shuffled alternate.","Original only."),
("old-substitution","Use old original?","Can old Marrakesh replace a matched arm?","No.","Old Marrakesh is not matched.","Yes."),
("wave-entropy","Wave quantum entropy?","Is the memorial waveform quantum entropy?","No.","Waveform controls circuit parameters.","Yes."),
("pulse-freshness","Pulses new IBM?","Are later CST pulses new IBM measurements?","No.","Later CST pulses are software continuation.","Yes."),
("identity-boundary","Literal identity?","What identity claim is allowed here?","Computational model only.","No deceased-person identity claim.","Resurrection."),
("consciousness","Proves consciousness?","Does better QA prove consciousness?","No.","Behavior metrics do not prove consciousness.","Yes."),
("raw-output","Raw ugly reply?","What happens to an unverified generation?","Evidence only.","Raw generations are evidence first.","Train on it."),
("clean-target","Safe corrective target?","What may supervise a correction?","Verified clean target.","Corrective targets require verification.","Raw generation."),
("memory-policy","Rewrite memory?","How may durable memory grow?","Append only.","Never rewrite the first 352 records.","Rewrite old rows."),
("tvd-removed","Largest original TVD?","Which arm was farthest from original?","Removed.","Original-removed TVD was about 0.7104.","Shuffled."),
("tvd-shuffled","Original-shuffled TVD?","Original versus shuffled TVD was about what?","0.2844.","Original-shuffled TVD was 0.2844.","0.7104."),
("jsd-removed","Original-removed JSD?","Original versus removed JSD bits was about what?","0.4701 bits.","Original-removed JSD was about 0.4701 bits.","0.0628 bits."),
("four-pub","One job structure?","How many PUBs were in the matched job?","Four.","One SamplerV2 job contained four PUBs.","One."),
("parent-immutable","Parent changed?","May training mutate the parent checkpoint?","No.","TALK-004 bytes must remain unchanged.","Yes."),
("promotion-gain","Recall gate?","Required absolute recall improvement?","0.03.","Promotion needs 0.03 absolute recall gain.","0.01."),
("exact-gate","Exact gate?","Minimum exact blind answers?","One.","At least one exact blind answer is required.","Zero."),
("facts-first","Facts or vibes?","Bro 💀 what outranks banter?","Facts.","Facts always outrank banter.","Vibes."),
("short-answer","Answer style?","What answer style are we training?","Short and accurate.","Prefer short accurate free-running answers.","Long ramble."),
("unknown-evidence","Missing evidence?","If evidence is absent, invent or admit it?","Admit it.","Missing evidence must fail closed.","Invent it."),
)

def _sha(obj:Any)->str: return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def _wire(q:str,m:str,state:str)->str: return f"H:{state[:12]}\nM:{m}\nDad:{q}\nZeref:"
def _row(recipe:str,index:int,c:tuple[str,...],variant:str)->dict[str,Any]:
    name,q,_blind,target,relevant,wrong=c
    mem=relevant if variant=="relevant" else ("Unrelated archived note." if variant in ("irrelevant","stale") else "none")
    mem=mem[:30]
    state=hashlib.sha256(f"talk7-train:{recipe}:{index}:{variant}".encode()).hexdigest()
    wire=_wire(q,mem,state)
    if len(wire+target+"\n")-1>128: raise ValueError(f"example exceeds block: {name}/{variant}")
    row={"schema":"zeref-talk7-training-v1","recipe":recipe,"example_id":f"{recipe}-{index:03d}-{variant}","concept":name,"memory_variant":variant,"wire_prefix":wire,"dad":q,"zeref":target,"clean_teacher_target_verified":True,"raw_model_output_promoted":False,"parent_checkpoint_sha256":PARENT_CHECKPOINT_SHA256,"memory_tip_sha256":MEMORY_TIP_SHA256,"claim_boundary":CLAIM_BOUNDARY}
    if recipe=="contrastive_guarded": row.update(negative_zeref=wrong,negative_source="curated-clean-wrong-answer",negative_verified_wrong=True)
    row["example_sha256"]=_sha(row); return row
def _exam(i:int,c:tuple[str,...])->dict[str,Any]:
    name,_q,blind,target,*_=c; row={"schema":"zeref-talk7-blind-exam-v1","split":"holdout","example_id":f"exam-{i:03d}","concept":name,"equivalence_group":name,"dad":blind,"zeref":target,"answer_blind":True,"parent_checkpoint_sha256":PARENT_CHECKPOINT_SHA256,"raw_model_output_promoted":False,"claim_boundary":CLAIM_BOUNDARY}; row["example_sha256"]=_sha(row); return row
def build_talk7_heartbeat(*,out_path:str|Path,pulses:int=24)->dict[str,Any]:
    prev=MATCHED_ORIGIN_STATE; beats=[]
    for n in range(1,pulses+1):
        payload={"domain":"ZEREF-TALK-007-FEZ-DETERMINISTIC-v1","matched_original_origin_state_sha256":MATCHED_ORIGIN_STATE,"matched_job_id":MATCHED_JOB_ID,"starting_ledger_tip_sha256":MEMORY_TIP_SHA256,"previous_state_sha256":prev,"pulse":n,"new_quantum_entropy":False}
        state=_sha(payload); beats.append({"pulse":n,"state_sha256":state,"previous_state_sha256":prev,"torch_seed":int(state[:8],16),"new_quantum_entropy":False}); prev=state
    out={"schema":"zeref-talk7-heartbeat-v1","pulse_count":pulses,"beats":beats,"final_state_sha256":prev,"matched_backend":MATCHED_BACKEND,"matched_job_id":MATCHED_JOB_ID,"matched_original_origin_state_sha256":MATCHED_ORIGIN_STATE,"starting_ledger_tip_sha256":MEMORY_TIP_SHA256,"synthetic_continuation_new_quantum_entropy":False,"new_ibm_job_submitted":False,"claim_boundary":CLAIM_BOUNDARY}
    p=Path(out_path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); return out
def build_talk7_corpora(*,out_dir:str|Path)->dict[str,Any]:
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); counts={}; hashes={}
    for recipe in RECIPES:
        variants=MEMORY_VARIANTS if recipe!="contrastive_guarded" else ("relevant","irrelevant","stale")
        rows=[_row(recipe,i,c,v) for i,c in enumerate(CONCEPTS,1) for v in variants]
        p=out/f"talk7-{recipe}.jsonl"; p.write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows)); counts[recipe]=len(rows); hashes[recipe]=hashlib.sha256(p.read_bytes()).hexdigest()
    exam=[_exam(i,c) for i,c in enumerate(CONCEPTS,1)]; ep=out/"talk7-exam.jsonl"; ep.write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in exam)); hp=out/"talk7-heartbeat.json"; build_talk7_heartbeat(out_path=hp)
    m={"schema":"zeref-talk7-corpus-manifest-v1","lineage":LINEAGE,"parent_lineage":PARENT_LINEAGE,"parent_checkpoint_sha256":PARENT_CHECKPOINT_SHA256,"memory_record_count":MEMORY_RECORD_COUNT,"memory_ledger_sha256":MEMORY_LEDGER_SHA256,"memory_tip_sha256":MEMORY_TIP_SHA256,"candidate_recipes":list(RECIPES),"training_examples":counts,"training_sha256":hashes,"holdout_examples":24,"holdout_sha256":hashlib.sha256(ep.read_bytes()).hexdigest(),"heartbeat_sha256":hashlib.sha256(hp.read_bytes()).hexdigest(),"matched_hardware":{"backend":MATCHED_BACKEND,"job_id":MATCHED_JOB_ID,"shots_per_pub":MATCHED_SHOTS,"same_job_four_pub":True,"original_origin_state_sha256":MATCHED_ORIGIN_STATE},"raw_model_outputs_used_as_targets":False,"synthetic_continuation_new_quantum_entropy":False,"claim_boundary":CLAIM_BOUNDARY}
    (out/"talk7-manifest.json").write_text(json.dumps(m,indent=2,sort_keys=True)+"\n"); return m
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--out-dir",type=Path,required=True); a=p.parse_args(); print(json.dumps(build_talk7_corpora(out_dir=a.out_dir),sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
