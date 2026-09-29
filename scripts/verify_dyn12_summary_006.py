"""Archive-level recheck of original real 3-seed numerical summary; NOT retraining."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from statistics import mean
P=Path(__file__).resolve().parent.parent/"docs/experiments/cosmos-dyn12-controlled-006-summary.json"
SHA="e64b5ae3819e09993016848d7849e19c5e195fa8e143b5dde61b4a5e74f08f57"

def verify():
    raw=P.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SHA:
        raise ValueError("original numeric receipt modified")
    r=json.loads(raw)
    if raw!=json.dumps(r,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()+bytes([10]):
        raise ValueError("noncanonical original receipt")
    if (r.get("schema")!="cosmos-native-dyn12-006-paired-summary-v1" or
        r.get("seed_set")!=[11,29,47] or
        r.get("novel_intelligence_advantage_proven") is not False or
        r.get("preregistered_synthetic_candidate_pattern_observed") is not False or
        len(r.get("per_seed_receipt_sha256",[]))!=3):
        raise ValueError("seed/protocol/null result mismatch")
    z=r["summary"]
    if set(z)!={"dyn12","standard","shuffled_state"}:
        raise ValueError("missing independent trained control")
    for mode,splits in z.items():
        for name,part in splits.items():
            correct=part["per_seed_correct"];count=part["per_seed_count"]
            if len(correct)!=3 or len(count)!=3 or len(set(count))!=1:
                raise ValueError("missing seed count")
            if count[0]!=(128 if name!="test" else 256):
                raise ValueError("wrong heldout denominator")
            if not all(0<=v<=n for v,n in zip(correct,count)):
                raise ValueError("impossible correctness count")
            observed=round(mean(v/n for v,n in zip(correct,count)),6)
            if abs(observed-part["mean_accuracy"])>0.000001:
                raise ValueError("aggregate does not match per-seed counts")
    for compared,key in (("standard","dyn12_minus_standard"),
                         ("shuffled_state","dyn12_minus_shuffled_state")):
        d=[round(round(a/256,6)-round(b/256,6),6) for a,b in zip(
            z["dyn12"]["test"]["per_seed_correct"],
            z[compared]["test"]["per_seed_correct"])]
        if any(abs(x-y)>0.000001 for x,y in zip(d,r["paired_differences"][key])):
            raise ValueError("reported pairwise differences do not match source counts")
    return {"original_sha256":SHA,"registered_seeds":r["seed_set"],
            "candidate_pattern":r["preregistered_synthetic_candidate_pattern_observed"],
            "scope":"archived three-seed original CI summary audit, not checkpoint retraining"}
if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))
