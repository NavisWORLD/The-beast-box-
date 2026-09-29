"""Independently validate published sanitized actual-original PHOS/Spark CPU receipts.
Source-only integrity and per-case regrading; NOT fresh checkpoint inference.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from statistics import mean
from scripts.cosmos_micro_originals_004 import (
    ARMS, CASES, LABELS, ORIGINAL_SHA, REPO, REV, SURFACES, sha256,
)
ROOT = Path(__file__).resolve().parent.parent / "docs" / "experiments"
RECEIPTS = {"phos":"3ec7c8bcc2d1f6ae28bd5ea363c6a8a6dac41afa9b580ad3a209088c007bf935","cosmos_born":"8106d122c6b965be0ff476af5e91304a7e48e15d5e7c75f5512ed2fc9ec60ca2"}
def verify(label: str, root: Path=ROOT) -> dict:
    if label not in RECEIPTS: raise ValueError("unregistered original")
    name=f"cosmos-micro-originals-004-{label}-measurements.json"
    raw=(root/name).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=RECEIPTS[label]:
        raise ValueError("source original receipt bytes changed")
    doc=json.loads(raw)
    if raw!=json.dumps(doc,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()+b"\\n".replace(b"\\\\n",b"\\n"):
        raise ValueError("noncanonical public evidence")
    target_path,_ = LABELS[label]
    if not (doc["schema"]=="cosmos-original-sub4m-prompt-feedback-004-v1"
       and doc["upstream_repo"]==REPO and doc["upstream_revision"]==REV
       and doc["model"]==label and doc["original_sha256"]==ORIGINAL_SHA[target_path]
       and doc["fixture_sha256"]==sha256(CASES)
       and doc["shared_arms"]==list(ARMS) and doc["prompt_surfaces"]==list(SURFACES)
       and doc["no_model_training_memory_or_authority"] is True
       and 500000 <= doc["parameter_count_measured"] < 3909956
       and len(doc["parameter_sha256_before_and_after_identical"])==64
       and len(doc["observations"])==8):
        raise ValueError("original identity or protocol mismatch")
    for surface in SURFACES:
        for case in CASES:
            row=next((x for x in doc["observations"] if x["surface"]==surface and x["id"]==case["id"]),None)
            if row is None or row["gold"]!=case["gold"] or set(row["outcomes"])!=set(ARMS):
                raise ValueError("truncated or relabeled actual original evidence")
            for arm in ARMS:
                record=row["outcomes"][arm]
                if (any(key in record for key in ("generation","generation_sha256","consumed_prompt","consumed_prompt_sha256"))
                    or (arm=="direct_correction" and "full_prompt_sha256" in record)):
                    raise ValueError("potential private checkpoint output published")
                if (type(record["exact_first_line"]) is not bool or
                    type(record["secondary_task_content"]) is not bool or
                    type(record["target_encodable"]) is not bool or
                    record["generated_characters"]!=12 or
                    record["unsupported_characters_removed"]<0 or
                    record["left_context_characters_truncated"]<0):
                    raise ValueError("malformed observation or response length")
        subset=[x for x in doc["observations"] if x["surface"]==surface]
        for arm in ARMS:
            items=[row["outcomes"][arm] for row in subset]
            got=doc["aggregate"][surface][arm]
            if (got["strict_success_count"]!=sum(x["exact_first_line"] for x in items) or
                got["secondary_task_success_count"]!=sum(x["secondary_task_content"] for x in items) or
                got["target_encodable_cases"]!=sum(x["target_encodable"] for x in items) or
                got["literal_target_question_retained_cases"]!=sum(
                  x["diagnostic"]["literal_target_query_in_consumed_context"] for x in items)):
                raise ValueError("recorded outcomes disagree with aggregate")
            expect=sum(x["diagnostic"]["literal_example_in_consumed_context"] for x in items) if arm!="baseline" else None
            if got["separate_example_retained_cases"]!=expect:
                raise ValueError("separate example retention summary was altered")
            if len([x for x in items if x["target_encodable"]])!=len(CASES):
                if got["mean_target_nll_nats"] is not None:
                    raise ValueError("must not average unrepresentable gold target")
            else:
                nll=round(mean(x["target_nll_nats"] for x in items),6)
                if abs(got["mean_target_nll_nats"]-nll)>0.000001:
                    raise ValueError("mean gold-target NLL does not reproduce")
    return {"model":label,"original_ci_receipt_sha256":RECEIPTS[label],
            "learned_parameter_count":doc["parameter_count_measured"],
            "strict_compact_baseline":doc["aggregate"]["compact_char_fit"]["baseline"]["strict_success_count"],
            "strict_compact_feedback":doc["aggregate"]["compact_char_fit"]["correct_example"]["strict_success_count"],
            "target_encodable_compact":doc["aggregate"]["compact_char_fit"]["baseline"]["target_encodable_cases"],
            "observations":len(doc["observations"])*len(ARMS),
            "scope":"independent archived privacy-sanitized evidence audit; not a model rerun"}
if __name__=="__main__":
    print(json.dumps({"models":[verify(x) for x in sorted(RECEIPTS)]},sort_keys=True))
