"""Verify ORIGINAL sanitized real 18K/Qwen self-correction outcomes; not rerun."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.cosmos_self_critique_005 import CASES,ARMS,sha, CHECKPOINTS,MODELS
ROOT=Path(__file__).resolve().parent.parent/"docs/experiments"
EXPECTED={"native18k":"b985f76760c4a7942a8d91b2fd1e2ed778c21ceb0e6d291525b217d0808db1bb","qwen0.5b":"0a3e333d6da399a05b52d4317485dac6267355a44b039694f64ea2970b05c36d"}
CHECKPOINT={"native18k":CHECKPOINTS["18k"]["sha256"],
            "qwen0.5b":MODELS["qwen2.5-0.5b"]["weights_sha256"]}

def verify(label:str,root:Path=ROOT)->dict:
    if label not in EXPECTED:raise ValueError("unknown original model")
    raw=(root/("cosmos-self-correction-005-"+label+"-receipt.json")).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED[label]:
        raise ValueError("original real CPU receipt bytes altered")
    doc=json.loads(raw)
    if raw!=json.dumps(doc,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()+bytes([10]):
        raise ValueError("not original canonical receipt")
    if (doc.get("schema")!="cosmos-genuine-prompt-self-critique-005-v1" or
        doc.get("model")!=label or
        doc.get("original_checkpoint_sha256")!=CHECKPOINT[label] or
        doc.get("fixture_sha256")!=sha(CASES) or
        doc.get("arms")!=list(ARMS) or len(doc.get("cases",[]))!=8 or
        doc.get("weights_unchanged") is not True or
        doc.get("no_owner_memory_training_or_cloud_inference") is not True or
        doc.get("reliable_generative_self_correction_proven") is not False):
        raise ValueError("wrong original published identity or protocol")
    for original,case in zip(CASES,doc["cases"]):
        if case.get("id")!=original["id"] or case.get("family")!=original["family"]:
            raise ValueError("missing case identity")
        if set(case["conditions"])!=set(ARMS) or set(case["semantic_conditions"])!=set(ARMS):
            raise ValueError("case missing frozen experimental condition")
        if any(key in case for key in ("generation","prompt","raw_generation","generated_text")):
            raise ValueError("owner-derived model text must not be public")
        if case["self_verdict"] not in ("CORRECT","INCORRECT","UNSURE","UNPARSEABLE"):
            raise ValueError("unknown parsed review verdict")
        if any(x is not None and type(x) is not bool for x in case["conditions"].values()):
            raise ValueError("nonbool strict result")
        if any(x is not None and type(x) is not bool for x in case["semantic_conditions"].values()):
            raise ValueError("nonbool semantic result")
        if (case["self_detected_actual_wrong"] !=
            (case["self_verdict"]=="INCORRECT" and not case["semantic_conditions"]["baseline"])):
            raise ValueError("self detection did not derive from baseline correctness")
        if (case["self_false_error_alarm"] !=
            (case["self_verdict"]=="INCORRECT" and case["semantic_conditions"]["baseline"])):
            raise ValueError("self false-alarm did not derive from baseline correctness")
        if case["critic_contained_new_task_gold"] != (
            case["semantic_conditions"]["new_task_after_critique"] is None):
            raise ValueError("new-task gold leakage not excluded")
    for key,field in (("aggregate","conditions"),("semantic_aggregate","semantic_conditions")):
        if set(doc[key])!=set(ARMS):raise ValueError("missing aggregate condition")
        for arm in ARMS:
            values=[c[field][arm] for c in doc["cases"]]
            got=doc[key][arm]
            if got!={"correct":sum(x is True for x in values),
                     "scored":sum(x is not None for x in values)}:
                raise ValueError("archived per-case scores do not reproduce aggregate")
    cases=doc["cases"]
    errors=[c for c in cases if not c["semantic_conditions"]["baseline"]]
    already=[c for c in cases if c["semantic_conditions"]["baseline"]]
    m=doc["correction_measures"]
    expected={
        "baseline_wrong_cases":len(errors),
        "self_corrected_wrong_cases":sum(c["semantic_conditions"]["self_critique"] for c in errors),
        "self_harmed_correct_cases":sum(not c["semantic_conditions"]["self_critique"] for c in already),
        "self_correctly_flagged_wrong_cases":sum(c["self_detected_actual_wrong"] for c in errors),
        "self_false_alarm_correct_cases":sum(c["self_false_error_alarm"] for c in already),
        "transfer_gold_leak_cases_excluded":sum(c["critic_contained_new_task_gold"] for c in cases),
        "separate_non_gold_checker_assisted_correct_cases":
            doc["aggregate"]["true_correctness_bit"]["correct"],
    }
    if m!=expected:raise ValueError("incorrect original detection/correction claims")
    if doc.get("synthetic_candidate_self_correction_pattern_observed") is not False:
        raise ValueError("historical failed candidate threshold cannot be rewritten")
    return {"model":label,"original_ci_receipt_sha256":EXPECTED[label],
            "baseline_semantic":doc["semantic_aggregate"]["baseline"]["correct"],
            "intrinsic_corrected_wrong_cases":m["self_corrected_wrong_cases"],
            "gold_disclosure_semantic":doc["semantic_aggregate"]["gold_disclosure"]["correct"],
            "quality_claim_proven":False,
            "scope":"archived actual original CPU receipts verified; NOT new model inference"}
if __name__=="__main__":
    print(json.dumps({"results":[verify(x) for x in sorted(EXPECTED)]},sort_keys=True))
