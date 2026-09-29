"""Archived original COSMOS 009/010 complete combined CPU result integrity.

This audit never downloads checkpoint weights or reruns either experiment.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent/"docs/experiments"
ORIGINAL={"009":"8ae68e4a4cbe4fab01add2e0c18fba1dab64d54b80a35cde8f89bb0ea1ceb4ae","010":"bccfbdc60228239cee5dd2ae0faca655a7a8a88111aa19e111abce61e03f0e27"}
SOURCES_009={"17:smollm2-135m":"e39524dc676c32ac7d8f0596cfffe3ba0710211711353acdf86892fc4baf125b","17:qwen2.5-0.5b":"3cb82b5c72be7db7d6d30556aff6e28955afee5f48b263fe94797c7f0d673af2","41:smollm2-135m":"43c431aa6c1b10a7255442e534ea4b76975f185819ad4a5e12f1da7cadf90902","41:qwen2.5-0.5b":"865d034adf79fc95c7324cddeb1079d141d073cac640814fd0e572da945ae41e"}
MODELS=("smollm2-135m","qwen2.5-0.5b")
LENGTHS=("short_8_records","long_32_records")
ARMS=("no_evidence","lexical","frozen_r12","adaptive_r12","oracle")
NATIVE=("dyn12","standard","shuffled_state")

def verify():
    reports={}
    for key,name in (("009","cosmos-end-to-end-009-summary.json"),
                     ("010","cosmos-native-length-010-summary.json")):
        raw=(ROOT/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=ORIGINAL[key]:
            raise ValueError("archived original full source SHA was altered "+key)
        report=json.loads(raw)
        if (json.dumps(report,sort_keys=True,ensure_ascii=False,separators=(",",":"),
                       allow_nan=False).encode()+bytes([10]))!=raw:
            raise ValueError("archived original source not canonical "+key)
        reports[key]=report
    g,n=reports["009"],reports["010"]
    if (g.get("schema")!="cosmos-original-generative-external-substrate-009-summary-v1"
        or g.get("preregistered_multimodel_two_length_candidate_pattern") is not False
        or g.get("reliable_general_generative_improvement_proven") is not False
        or len(g.get("sources",[]))!=4 or len(g.get("results",[]))!=4):
        raise ValueError("original two-model source evidence incomplete")
    if {str(s["seed"])+":"+s["model"]:s["sha256"] for s in g["sources"]}!=SOURCES_009:
        raise ValueError("individual original model source hashes changed")
    for x in g["results"]:
        if x["model"] not in MODELS or x["length"] not in LENGTHS:
            raise ValueError("unregistered result identity")
        count=16 if x["length"]=="short_8_records" else 32
        if set(x["scores"])!=set(ARMS):
            raise ValueError("missing entire experimental control arm")
        for arm in ARMS:
            v=x["scores"][arm]
            if v["count"]!=count or not 0<=v["correct"]<=count:
                raise ValueError("truncated actual generated answers")
            if arm=="no_evidence":
                if v["retrieval_correct"] is not None:
                    raise ValueError("fabricated null-source retrieval")
            elif not 0<=v["retrieval_correct"]<=count:
                raise ValueError("invalid original retrieval count")
        if x["scores"]["oracle"]["retrieval_correct"]!=count or x["scores"]["lexical"]["retrieval_correct"]!=count:
            raise ValueError("strong conventional/oracle original control was altered")
        if x["adaptive_minus_lexical_correct"]!=(x["scores"]["adaptive_r12"]["correct"]-x["scores"]["lexical"]["correct"]):
            raise ValueError("derived lexical difference wrong")
        if x["adaptive_minus_frozen_correct"]!=(x["scores"]["adaptive_r12"]["correct"]-x["scores"]["frozen_r12"]["correct"]):
            raise ValueError("derived frozen difference wrong")
    if (n.get("schema")!="cosmos-native-six-binding-010-combined-v1"
        or n.get("seeds")!=[19,43,71] or len(n.get("original_source_sha256",[]))!=3
        or n.get("preregistered_multi_length_candidate") is not False
        or n.get("novel_native_12d_long_sequence_advantage_proven") is not False
        or set(n.get("summary",{}))!=set(NATIVE)):
        raise ValueError("original new-seed native evidence missing")
    for mode in NATIVE:
        for length,den in (("test_three",256),("shift_four",128),("shift_five",128),("shift_six",128)):
            data=n["summary"][mode][length]
            raw_counts=data["per_seed_correct"]
            if data["per_seed_count"]!=[den]*3 or len(raw_counts)!=3:
                raise ValueError("wrong original native denominator")
            if not all(0<=score<=den for score in raw_counts):
                raise ValueError("original native impossible correct count")
            accuracy=round(sum(round(score/den,6) for score in raw_counts)/3,6)
            if abs(accuracy-data["mean_accuracy"])>0.000001:
                raise ValueError("original native mean does not reproduce recorded per-seed scores")
    for control in ("standard","shuffled_state"):
        for length in ("test_three","shift_four","shift_five","shift_six"):
            divisor=256 if length=="test_three" else 128
            actual=[round(a/divisor-b/divisor,6) for a,b in zip(
                n["summary"]["dyn12"][length]["per_seed_correct"],
                n["summary"][control][length]["per_seed_correct"])]
            if any(abs(x-y)>0.000001 for x,y in zip(actual,n["paired_differences"][control][length])):
                raise ValueError("native paired signed difference was misreported")
    return {"schema":"original-009-010-source-only-archive-check-v1",
            "original_full_source_shas":ORIGINAL,"original_models":list(MODELS),
            "original_native_seeds":[19,43,71],
            "real_retrieval_generation_advantage_established":False,
            "longer_context_12d_advantage_established":False,
            "new_model_execution_performed_by_this_archive_audit":False}

if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))
