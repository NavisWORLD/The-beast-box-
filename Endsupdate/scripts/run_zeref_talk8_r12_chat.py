#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from pathlib import Path

BLOCK=128

def _load(name,file):
    p=Path(__file__).with_name(file); s=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
V3=_load("talk8_v3","run_zeref_ibm_dad_teacher_v3.py")
EV=_load("talk8_ev","eval_zeref_talk5_free_run.py")
CORP=_load("talk8_corpus","build_zeref_talk8_r12_corpus.py")
BASE=V3._v2._base_module()

def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _rows(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]

def run(args):
    actual=_sha(args.checkpoint)
    if actual!=args.checkpoint_sha256.lower(): raise RuntimeError("TALK-008 checkpoint hash mismatch")
    hb=json.loads(args.heartbeat.read_text()); beats=hb["beats"]
    exam=_rows(args.exam)
    if len(exam)>len(beats): raise RuntimeError("not enough deterministic pulses")
    ckpt,model=BASE._load_model(args.checkpoint,args.arch)
    if int(ckpt["config"]["block"])!=BLOCK: raise RuntimeError("unexpected native block")
    out=[]
    for i,(row,beat) in enumerate(zip(exam,beats),1):
        dad=str(row["dad"])
        full=CORP.build_r12_context(dad,args.reality_root,top_k=1)
        state=json.loads((args.reality_root/"state/r12-state.json").read_text())["vector"]
        p=next((e for e in json.loads((args.reality_root/"manifest.json").read_text())["source_hardware"].get("conditions",[]) if False),None)
        compact=f"r12 rc={state['reality_coupling']:.2f} si={state['source_integrity']:.0f} prov=measured"
        wire=f"H:{str(beat['state_sha256'])[:12]}\nM:{compact}\nDad:{dad}\nZeref:"
        if len(wire)>BLOCK: wire=f"H:{str(beat['state_sha256'])[:8]}\nM:r12 prov=measured\nDad:{dad[:72]}\nZeref:"
        raw,termination=V3.generate_teacher_turn(BASE,model,ckpt,wire,seed=int(beat["torch_seed"]),tokens=args.tokens,temperature=args.temperature,top_k=args.top_k)
        reference=str(row.get("zeref") or ""); recall=EV.reference_token_recall(raw,reference) if reference else None; exact=EV.normalized_text(raw)==EV.normalized_text(reference) if reference else None; anomaly=EV.output_metrics(raw)
        out.append({"schema":"zeref-talk8-r12-turn-v1","turn":i,"concept":row.get("concept"),"dad_prompt":dad,"wire_prompt":wire,"r12_context":full,"raw_output":raw,"raw_output_sha256":hashlib.sha256(raw.encode()).hexdigest(),"reference":reference,"reference_token_recall":recall,"exact_answer":exact,"anomaly":anomaly,"termination":termination,"checkpoint_sha256":actual,"raw_model_output_promoted_to_training":False})
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text("".join(json.dumps(r,sort_keys=True,ensure_ascii=False)+"\n" for r in out))
    free=[{"concept":r["concept"],"equivalence_group":r["concept"],"raw_output":r["raw_output"]} for r in out]; hold=[{"concept":r.get("concept"),"equivalence_group":r.get("concept"),"zeref":r["reference"]} for r in out]; report=EV.summarize_free_run(transcript=free,holdout=hold); report["exact_answer_count"]=sum(bool(r["exact_answer"]) for r in out)
    manifest={"schema":"zeref-talk8-r12-chat-manifest-v1","checkpoint_sha256":actual,"turns":len(out),"r12_state_sha256":"48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20","new_ibm_job_submitted":False,"raw_outputs_preserved_verbatim":True,"raw_outputs_promoted_to_training":False,"free_run_report":report}; args.manifest.parent.mkdir(parents=True,exist_ok=True); args.manifest.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n"); return manifest

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--checkpoint",type=Path,required=True); p.add_argument("--checkpoint-sha256",required=True); p.add_argument("--arch",type=Path,required=True); p.add_argument("--heartbeat",type=Path,required=True); p.add_argument("--exam",type=Path,required=True); p.add_argument("--reality-root",type=Path,required=True); p.add_argument("--out",type=Path,required=True); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--tokens",type=int,default=48); p.add_argument("--temperature",type=float,default=.05); p.add_argument("--top-k",type=int,default=1); a=p.parse_args(); print(json.dumps(run(a),sort_keys=True))
