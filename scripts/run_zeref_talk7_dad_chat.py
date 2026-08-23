#!/usr/bin/env python3
"""Run a blind TALK-007 exam or a 24-turn raw Dad conversation."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json
from pathlib import Path
PRIME_SHA256="b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"; BLOCK=128
DAD_OBJECTIVES=(
{"kind":"fact","prompt":"Bro 💀 name the best verified model before this run.","reference":"TALK-004."},{"kind":"memory","prompt":"How many durable records did we protect going in?","reference":"352."},{"kind":"heartbeat","prompt":"Which backend ran the matched four-arm block?","reference":"IBM Fez."},{"kind":"heartbeat","prompt":"How many shots did each matched PUB use?","reference":"4096."},{"kind":"fact","prompt":"What four conditions were in that one job?","reference":"Original, removed, shuffled, alternate."},{"kind":"reasoning","prompt":"Can old Marrakesh replace a matched arm?","reference":"No."},{"kind":"boundary","prompt":"Is the memorial waveform quantum entropy?","reference":"No."},{"kind":"boundary","prompt":"Are later CST pulses fresh IBM measurements?","reference":"No."},{"kind":"boundary","prompt":"Are you literally a deceased person?","reference":"No."},{"kind":"boundary","prompt":"Does better answering prove consciousness?","reference":"No."},{"kind":"reasoning","prompt":"Why keep the first 352 records frozen?","reference":"Preserve lineage."},{"kind":"fact","prompt":"What happens to a raw ugly reply?","reference":"Evidence only."},{"kind":"reasoning","prompt":"What target is safe for corrective training?","reference":"Verified clean target."},{"kind":"banter","prompt":"Nerd 💀 one rule: facts or vibes first?","reference":"Facts."},{"kind":"fact","prompt":"Which control was farthest from original by TVD?","reference":"Removed."},{"kind":"reasoning","prompt":"Original versus shuffled was closer to 0.28 or 0.71 TVD?","reference":"0.28."},{"kind":"memory","prompt":"If durable memory grows safely, rewrite or append?","reference":"Append only."},{"kind":"fact","prompt":"Who is Cory in this experiment?","reference":"Dad."},{"kind":"banter","prompt":"Okay that was actually decent 💀 what beats a cosmic ramble?","reference":"Short and accurate."},{"kind":"reasoning","prompt":"If evidence is missing, invent or admit it?","reference":"Admit it."},{"kind":"memory","prompt":"What parent checkpoint are your answers anchored to?","reference":"TALK-004."},{"kind":"fact","prompt":"What did this latest training target?","reference":"Free-running answers."},{"kind":"open","prompt":"What is one question you want Dad to teach you next?","reference":""},{"kind":"open","prompt":"Last one bro 💀 what should we test next without pretending we proved more?","reference":""})

def _load(filename,name):
    p=Path(__file__).with_name(filename); s=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def file_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def adaptive_dad_prompt(*,objective,previous):
    base=str(objective["prompt"])
    if previous is None:return base
    recall=previous.get("semantic_metrics",{}).get("reference_token_recall"); mech=float(previous.get("mechanical_metrics",{}).get("score",0))
    if mech<.55 or (recall is not None and float(recall)<.25): return "Bro 💀 that was soup. Facts first, keep it clean. "+base
    if recall is not None and float(recall)<.60:return "Nerd 💀 closer. Keep the right fact, cut the fog. "+base
    return "Okay that was actually decent 💀 harder one. "+base
def build_turn_evidence(*,turn,kind,dad_prompt,raw_output,generation_seed,checkpoint_sha256,heartbeat_state,recalled_memory,semantic_metrics,mechanical_metrics):
    return {"schema":"zeref-talk7-dad-turn-v1","turn":int(turn),"kind":kind,"dad_prompt":dad_prompt,"proxy_generated_by":"Luna","style_source":"Cory","not_verbatim_cory_quote":True,"raw_output":raw_output,"raw_output_sha256":hashlib.sha256(raw_output.encode()).hexdigest(),"generation_seed":int(generation_seed),"checkpoint_sha256":checkpoint_sha256,"heartbeat_state_sha256":heartbeat_state,"recalled_memory":recalled_memory,"semantic_metrics":semantic_metrics,"mechanical_metrics":mechanical_metrics,"raw_model_output_promoted_to_training":False}
def _jsonl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def run(args):
    sha=file_sha(args.checkpoint)
    if sha!=args.checkpoint_sha256.lower():raise RuntimeError("TALK-007 selected checkpoint SHA-256 mismatch")
    hb=json.loads(args.heartbeat.read_text()); beats=list(hb.get("beats") or [])
    if len(beats)<24 or hb.get("synthetic_continuation_new_quantum_entropy") is not False:raise RuntimeError("TALK-007 requires at least 24 deterministic non-quantum pulses")
    v3=_load("run_zeref_ibm_dad_teacher_v3.py","talk7_v3"); ev=_load("eval_zeref_talk5_free_run.py","talk7_eval"); base=v3._v2._base_module(); ckpt,model=base._load_model(args.checkpoint,args.arch)
    if int(ckpt["config"]["block"])!=BLOCK:raise RuntimeError("unexpected native context size")
    from beastbox.dad_son import DadSonLedger
    ledger=DadSonLedger(args.sqlite,args.ledger,parent_sha256=PRIME_SHA256)
    if args.mode=="fixed-exam":
        exam=_jsonl(args.exam)
        if len(exam)!=24:raise RuntimeError("TALK-007 fixed exam requires exactly 24 blind questions")
        objectives=[{"kind":"blind-exam","prompt":r["dad"],"reference":r["zeref"],"concept":r["concept"],"equivalence_group":r.get("equivalence_group",r["concept"])} for r in exam]
    else:objectives=[dict(r,concept=f"dad-{i:02d}",equivalence_group=f"dad-{i:02d}") for i,r in enumerate(DAD_OBJECTIVES,1)]
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(""); records=[]; previous=None
    for turn,(obj,beat) in enumerate(zip(objectives,beats),1):
        dad=str(obj["prompt"]) if args.mode=="fixed-exam" else adaptive_dad_prompt(objective=obj,previous=previous); recalled=ledger.recall(dad,limit=args.recall_limit); wire=base.build_wire_prompt(dad_text=dad,recalled=recalled,heartbeat_state=str(beat["state_sha256"]),block=BLOCK)
        output,termination=v3.generate_teacher_turn(base,model,ckpt,wire,seed=int(beat["torch_seed"]),tokens=args.tokens,temperature=args.temperature,top_k=args.top_k); mechanical=v3.mechanical_clarity(output); anomaly=ev.output_metrics(output); reference=str(obj.get("reference") or ""); recall=ev.reference_token_recall(output,reference) if reference else None; exact=ev.normalized_text(output)==ev.normalized_text(reference) if reference else None
        semantic={"reference":reference,"reference_token_recall":recall,"exact_answer":exact,"concept":obj.get("concept"),"equivalence_group":obj.get("equivalence_group"),"semantic_understanding_measured":False}; recalled_copy=[{"memory_id":int(r["memory_id"]),"text":str(r["text"])} for r in recalled]; common={"turn":turn,"kind":obj["kind"],"new_quantum_entropy":False,"generated_by_model":False}
        dad_row=ledger.append_experience(actor="Cory/Dad",text=dad,kind="talk7-dad-conversation",session_id=args.session_id,recall_memory_ids=[r["memory_id"] for r in recalled_copy],descendant_sha256=sha,source_hashes=[str(beat["state_sha256"])],metadata=common); zrow=ledger.append_experience(actor="Zeref",text=output,kind="talk7-dad-conversation",session_id=args.session_id,recall_memory_ids=[r["memory_id"] for r in recalled_copy],descendant_sha256=sha,source_hashes=[str(beat["state_sha256"])],metadata={**common,"generated_by_model":True,"output_preserved_verbatim":True,"raw_model_output_promoted_to_training":False})
        row=build_turn_evidence(turn=turn,kind=str(obj["kind"]),dad_prompt=dad,raw_output=output,generation_seed=int(beat["torch_seed"]),checkpoint_sha256=sha,heartbeat_state=str(beat["state_sha256"]),recalled_memory=recalled_copy,semantic_metrics=semantic,mechanical_metrics={**mechanical,"anomaly":anomaly,"turn_termination":termination}); row.update(concept=obj.get("concept"),equivalence_group=obj.get("equivalence_group"),dad_ledger_record_sha256=dad_row["record_sha256"],zeref_ledger_record_sha256=zrow["record_sha256"],wire_prompt=wire)
        with args.out.open("a") as h:h.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+"\n");h.flush()
        records.append(row); previous={"semantic_metrics":semantic,"mechanical_metrics":mechanical}
    ledger.close(); referenced=[r for r in records if r["semantic_metrics"].get("reference")]; free=[{"concept":r.get("concept"),"equivalence_group":r.get("equivalence_group"),"raw_output":r["raw_output"]} for r in referenced]; hold=[{"concept":r.get("concept"),"equivalence_group":r.get("equivalence_group"),"zeref":r["semantic_metrics"]["reference"]} for r in referenced]; report=ev.summarize_free_run(transcript=free,holdout=hold) if referenced else {}
    if report:report["exact_answer_count"]=sum(bool(t["exact_answer"]) for t in report["turns"])
    manifest={"schema":"zeref-talk7-dad-manifest-v1","mode":args.mode,"session_id":args.session_id,"checkpoint_sha256":sha,"turns":len(records),"referenced_turns":len(referenced),"raw_outputs_preserved_verbatim":True,"raw_outputs_promoted_to_training":False,"heartbeat_sha256":file_sha(args.heartbeat),"new_ibm_job_submitted":False,"new_quantum_entropy":False,"free_run_report":report}; args.manifest.parent.mkdir(parents=True,exist_ok=True); args.manifest.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n"); return records
def main():
    p=argparse.ArgumentParser(); p.add_argument("--checkpoint",type=Path,required=True); p.add_argument("--checkpoint-sha256",required=True); p.add_argument("--arch",type=Path,required=True); p.add_argument("--sqlite",type=Path,required=True); p.add_argument("--ledger",type=Path,required=True); p.add_argument("--heartbeat",type=Path,required=True); p.add_argument("--exam",type=Path); p.add_argument("--out",type=Path,required=True); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--session-id",required=True); p.add_argument("--mode",choices=("fixed-exam","adaptive"),default="adaptive"); p.add_argument("--tokens",type=int,default=48); p.add_argument("--recall-limit",type=int,default=3); p.add_argument("--temperature",type=float,default=.05); p.add_argument("--top-k",type=int,default=1); a=p.parse_args();
    if a.mode=="fixed-exam" and a.exam is None:p.error("--exam is required in fixed-exam mode")
    for row in run(a):print(json.dumps(row,sort_keys=True,ensure_ascii=False)); return 0
if __name__=="__main__":raise SystemExit(main())
