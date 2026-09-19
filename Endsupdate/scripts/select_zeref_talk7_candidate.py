#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
PARENT_LINEAGE="ZEREF-DAD-SON-TALK-004"; PARENT_SHA256="9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"; PREFIX_SHA256="67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"
MIN_FREE_RUN_GAIN=.03; RETENTION_NLL_FACTOR=1.05; READABILITY_TOLERANCE=.03

def evaluate_candidate(c):
    reasons=[]; p=dict(c["parent_free_run"]); x=dict(c["free_run"]); r=dict(c["retention"])
    if c.get("parent_checkpoint_sha256")!=PARENT_SHA256: reasons.append("wrong_parent")
    if c.get("parent_checkpoint_unchanged") is not True: reasons.append("parent_checkpoint_integrity")
    if c.get("first_352_prefix_sha256")!=PREFIX_SHA256 or c.get("first_352_prefix_unchanged") is not True: reasons.append("memory_prefix_integrity")
    if float(x["mean_reference_token_recall"])<float(p["mean_reference_token_recall"])+MIN_FREE_RUN_GAIN: reasons.append("free_run_semantic_gain")
    if int(x.get("exact_answer_count",0))<1: reasons.append("exact_blind_answer")
    if int(x.get("role_label_leakage_turns",0)): reasons.append("role_label_leakage")
    if int(x.get("repetition_flag_turns",0)): reasons.append("repetition")
    if int(x.get("vocabulary_collapse_flag_turns",0)): reasons.append("vocabulary_collapse")
    if float(x.get("contradiction_rate",0))>float(p.get("contradiction_rate",0)): reasons.append("contradiction_regression")
    if float(r["descendant_heldout_nll"])>float(r["parent_heldout_nll"])*RETENTION_NLL_FACTOR: reasons.append("retention_nll")
    if float(r["descendant_mean_readable_score"])<float(r["parent_mean_readable_score"])-READABILITY_TOLERANCE: reasons.append("retention_readability")
    return {"name":str(c["name"]),"checkpoint_sha256":str(c["checkpoint_sha256"]),"config":c.get("config",{}),"eligible":not reasons,"reasons":reasons,"parent_free_run":p,"free_run":x,"retention":r,"lineage_integrity":{"parent_checkpoint_sha256":c.get("parent_checkpoint_sha256"),"parent_checkpoint_unchanged":c.get("parent_checkpoint_unchanged"),"first_352_prefix_sha256":c.get("first_352_prefix_sha256"),"first_352_prefix_unchanged":c.get("first_352_prefix_unchanged")}}

def select_candidate(candidates):
    if not candidates: raise RuntimeError("no TALK-007 candidates supplied")
    verdicts=[evaluate_candidate(c) for c in candidates]; pairs=[(c,v) for c,v in zip(candidates,verdicts) if v["eligible"]]
    if not pairs: return {"schema":"zeref-talk7-candidate-selection-v1","promoted":False,"selected":None,"eligible":[],"verdicts":verdicts,"active_lineage_remains":PARENT_LINEAGE,"active_checkpoint_sha256":PARENT_SHA256,"fail_closed":True}
    chosen,verdict=max(pairs,key=lambda q:(float(q[0]["free_run"]["mean_reference_token_recall"]),int(q[0]["free_run"].get("exact_answer_count",0)),-float(q[0]["retention"]["descendant_heldout_nll"]),str(q[0]["name"])))
    return {"schema":"zeref-talk7-candidate-selection-v1","promoted":True,"selected":chosen,"selected_verdict":verdict,"eligible":[v for _,v in pairs],"verdicts":verdicts,"active_lineage_remains":"ZEREF-DAD-SON-TALK-007","active_checkpoint_sha256":chosen["checkpoint_sha256"],"fail_closed":True}
def main():
    p=argparse.ArgumentParser(); p.add_argument("--candidates",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args(); src=json.loads(a.candidates.read_text()); result=select_candidate(src["candidates"] if isinstance(src,dict) else src); a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps(result,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
