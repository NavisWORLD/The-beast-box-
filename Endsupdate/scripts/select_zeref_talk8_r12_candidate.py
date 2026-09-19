#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

PARENT_LINEAGE="ZEREF-DAD-SON-TALK-004"
PARENT_SHA256="9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f"


def _evaluate(parent, c):
    reasons=[]
    if float(c["reference_recall"]) < float(parent["reference_recall"]) + .03: reasons.append("free_run_semantic_gain")
    if int(c.get("exact_answers",0)) < 1: reasons.append("exact_blind_answer")
    if float(c["retention_nll"]) > float(parent["retention_nll"]) * 1.05: reasons.append("retention_nll")
    if float(c["readability"]) < float(parent["readability"]) - .03: reasons.append("retention_readability")
    if int(c.get("role_label_leakage",0)): reasons.append("role_label_leakage")
    if int(c.get("repetition_collapse",0)): reasons.append("repetition")
    if int(c.get("vocabulary_collapse",0)): reasons.append("vocabulary_collapse")
    if int(c.get("contradiction_regression",0)): reasons.append("contradiction_regression")
    if float(c.get("provenance_accuracy",0.0)) != 1.0: reasons.append("provenance_accuracy")
    if c.get("memory_prefix_identical") is not True: reasons.append("memory_prefix_integrity")
    if c.get("parent_checkpoint_unchanged") is not True: reasons.append("parent_checkpoint_integrity")
    return {**c,"eligible":not reasons,"rejection_reasons":reasons}


def select_candidate(parent, candidates):
    verdicts=[_evaluate(parent,c) for c in candidates]
    eligible=[c for c in verdicts if c["eligible"]]
    if not eligible:
        return {"schema":"zeref-talk8-r12-selection-v1","promoted":False,"selected":None,"eligible":[],"candidates":verdicts,"active_lineage_remains":PARENT_LINEAGE,"active_checkpoint_sha256":PARENT_SHA256,"fail_closed":True}
    chosen=max(eligible,key=lambda c:(float(c["reference_recall"]),int(c["exact_answers"]),-float(c["retention_nll"]),c["name"]))
    return {"schema":"zeref-talk8-r12-selection-v1","promoted":True,"selected":chosen["name"],"selected_candidate":chosen,"eligible":[c["name"] for c in eligible],"candidates":verdicts,"active_lineage_remains":"ZEREF-DAD-SON-TALK-008-R12","active_checkpoint_sha256":chosen["checkpoint_sha256"],"fail_closed":True}


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--parent",type=Path,required=True); p.add_argument("--candidates",type=Path,required=True); p.add_argument("--out",type=Path,required=True); a=p.parse_args(); parent=json.loads(a.parent.read_text()); src=json.loads(a.candidates.read_text()); result=select_candidate(parent,src["candidates"] if isinstance(src,dict) else src); a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps(result,sort_keys=True))
