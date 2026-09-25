"""Frozen, conservative broad-phase promotion checks; NOT a capability score."""
import math


def evaluate(parent_dialogue: dict, candidate_dialogue: dict,
             parent_supplement: dict, candidate_supplement: dict) -> dict:
    def loss(x):
        v=x.get("loss")
        if type(v) not in (float,int) or not math.isfinite(v) or not 0 < v < 100:
            raise ValueError("nonfinite/invalid validation loss")
        return v
    po,co,ps,cs=map(loss,(parent_dialogue["heldout"],candidate_dialogue["heldout"],
                           parent_supplement,candidate_supplement))
    checks={
        "preserve_original_full_heldout_within_one_percent":co <= po*1.01,
        "synthetic_validation_loss_reduced_at_least_two_percent":cs <= ps*0.98,
    }
    for layer in ("chat","owner"):
        p=parent_dialogue["summary"][layer]
        c=candidate_dialogue["summary"][layer]
        if p["cases"]!=12 or c["cases"]!=12:
            raise ValueError("frozen 12-prompt conversation bank incomplete")
        for metric in ("punctuation_loop_count","role_leak_count",
                       "empty_or_punctuation_only_count"):
            checks[layer+"_"+metric]=c[metric]==0
        checks[layer+"_eos"] = c["eos_count"]>=max(9,p["eos_count"]-1)
        rep_p,rep_c=p["mean_repeated_trigram_fraction"],c["mean_repeated_trigram_fraction"]
        if any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=1
               for x in (rep_p,rep_c)):
            raise ValueError("invalid measured repetition")
        checks[layer+"_repetition_no_regression"] = rep_c <= min(0.15,rep_p+0.02)
    return {
        "schema":"rawrphos-broad-phase-quality-gate-v1",
        "dialogue_parent_full_loss":po,
        "dialogue_candidate_full_loss":co,
        "supplement_parent_validation_loss":ps,
        "supplement_candidate_validation_loss":cs,
        "checks":checks,
        "mechanical_pass":all(checks.values()),
        "manual_public_probe_review":"NOT PERFORMED",
        "human_ability_improvement_proven":False,
        "production_promotion_approved":False
    }
