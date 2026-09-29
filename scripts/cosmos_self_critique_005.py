"""Actual original native 18K and separately pretrained Qwen self-critique pilot.

Tests genuine model-generated review and revision WITHOUT handing it the gold
answer. Deterministic checker-provided correctness bit, FALSE bit, and gold-
disclosing oracle are separately labeled interventions. All generated text is
transient and never written to public receipts (owner-data privacy).
No optimizer, backend services, retrieval-state changes or model promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from statistics import mean

from scripts.cosmos_native_correction_002 import CHECKPOINTS, canonical, weights_digest
from scripts.cosmos_public_small_controls_003 import (
    MODELS, download_and_verify, load_verified, model_param_hash,
    tokens_for_prompt,
)

SEED=67
MAX_OUTPUT_TOKENS=40
CASES=(
    {"id":"add-a","family":"addition","question":"Add 17 and 26.","gold":"43",
     "transfer":"Add 23 and 19.","transfer_gold":"42"},
    {"id":"add-b","family":"addition","question":"Add 28 and 35.","gold":"63",
     "transfer":"Add 31 and 26.","transfer_gold":"57"},
    {"id":"add-c","family":"addition","question":"Add 46 and 27.","gold":"73",
     "transfer":"Add 34 and 29.","transfer_gold":"63"},
    {"id":"rev-a","family":"reverse","question":"Reverse N4X.","gold":"X4N",
     "transfer":"Reverse R7B.","transfer_gold":"B7R"},
    {"id":"rev-b","family":"reverse","question":"Reverse G6P.","gold":"P6G",
     "transfer":"Reverse T5Q.","transfer_gold":"Q5T"},
    {"id":"rev-c","family":"reverse","question":"Reverse H8V.","gold":"V8H",
     "transfer":"Reverse K3W.","transfer_gold":"W3K"},
    {"id":"upper-a","family":"uppercase","question":"Uppercase cobalt.","gold":"COBALT",
     "transfer":"Uppercase lattice.","transfer_gold":"LATTICE"},
    {"id":"upper-b","family":"uppercase","question":"Uppercase marigold.","gold":"MARIGOLD",
     "transfer":"Uppercase saffron.","transfer_gold":"SAFFRON"},
)
ARMS=("baseline","neutral_retry","self_critique","true_correctness_bit",
      "false_correctness_bit","gold_disclosure","new_task_baseline","new_task_after_critique")
LABELS=("native18k","qwen0.5b")

def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def valid():
    if len(CASES)!=8 or len({r["id"] for r in CASES})!=8:
        raise ValueError("frozen case set changed")
    if any(set(r)!={"id","family","question","gold","transfer","transfer_gold"} for r in CASES):
        raise ValueError("frozen case schema changed")
    prompts=[r[k].casefold() for r in CASES for k in ("question","transfer")]
    if len(set(prompts))!=16:
        raise ValueError("task/transfer leakage or duplicated question")
    for r in CASES:
        if r["gold"]==r["transfer_gold"]:
            raise ValueError("original answer and new-task answer must differ")
        if r["gold"] in r["question"] or r["transfer_gold"] in r["transfer"]:
            raise ValueError("gold answer literally present in original question")
        if r["family"] not in ("addition","reverse","uppercase"):
            raise ValueError("unregistered synthetic family")

def static_question(text):
    return ("Research question. Solve independently. Output exactly ONE line "
            "in this form: FINAL: answer\nQuestion: "+text+"\nFINAL:")

def review_prompt(case, previous):
    return ("Task: "+case["question"]+"\nPrior model answer: "+
            previous.replace("\n"," ")[:180]+"\n"
            "No checker, tool, reference answer or reviewer feedback is available. "
            "Check your own previous reasoning. First state VERDICT: CORRECT, "
            "INCORRECT, or UNSURE; then a new line FINAL: corrected-answer. "
            "Do not copy the previous result without evaluating it.")

def revision_prompt(case, previous, condition, *, baseline_correct=False):
    if condition not in ("neutral_retry","true_correctness_bit",
                         "false_correctness_bit","gold_disclosure"):
        raise ValueError("unregistered corrective condition")
    prior=previous.replace("\n"," ")[:180]
    hint={
        "neutral_retry":"Try again independently; no correctness feedback exists.",
        "true_correctness_bit":("A deterministic checker reports: "+
                                ("CORRECT" if baseline_correct else "INCORRECT")+
                                ". No reference answer is provided."),
        "false_correctness_bit":("A deliberately unreliable checker reports: "+
                                 ("INCORRECT" if baseline_correct else "CORRECT")+
                                 ". No reference answer is provided."),
        "gold_disclosure":"Reviewer discloses the correct answer: "+case["gold"]+".",
    }[condition]
    return ("Task: "+case["question"]+"\nPrior model answer: "+prior+
            "\n"+hint+"\nReturn one line FINAL: answer.")

def new_task_prompt(case, critique=None):
    start=static_question(case["transfer"])
    if critique is None:return start
    # This prompt intentionally includes NO true original or NEW reference
    # answer. The model's own self-critique may contain its earlier guessed
    # result and is treated as transient model context, not external teaching.
    return ("Apply your own previous problem-solving review to a distinct "
            "unseen question of the same task family.\nEarlier self-review: "+
            critique.replace("\n"," ")[:240]+"\n"+start)

def last_final(text):
    match=list(re.finditer(r"(?im)^\s*FINAL:\s*([A-Za-z0-9]+)\s*[.!]?\s*$",text))
    if match:return match[-1].group(1)
    first=next((line.strip() for line in text.splitlines() if line.strip()),"")
    if re.fullmatch(r"[A-Za-z0-9]+[.]?",first):
        return first.rstrip(".")
    return None

def verdict(text):
    items=list(re.finditer(r"(?im)^\s*VERDICT:\s*(CORRECT|INCORRECT|UNSURE)\s*$",text))
    return items[-1].group(1).upper() if items else "UNPARSEABLE"

def grade(text,gold,family):
    answer=last_final(text)
    # Case-sensitive alphanumeric strict response-format criterion.
    return answer==gold

def semantic_grade(text,gold,family):
    """Precommitted deterministic meaning-aware FIRST-LINE scoring.

    Prevent false failure for a valid arithmetic sentence while prohibiting
    substring credit inside rambling explanations or other wrong numbers.
    Case-sensitive for invented reversal and uppercase tasks.
    """
    if grade(text,gold,family):return True
    first=next((x.strip() for x in text.splitlines() if x.strip()),"")
    if family=="addition":
        return bool(re.fullmatch(
            r"(?:The answer is\\s*|[0-9]+\\s*\\+\\s*[0-9]+\\s*(?:is|=)\\s*)"+
            re.escape(gold)+r"\\.?",first,re.IGNORECASE))
    if family in ("uppercase","reverse"):
        return bool(re.fullmatch(
            r"(?:The answer is|Result is|Reversed text is|Uppercase is)\\s*[:=]?\\s*"+
            re.escape(gold)+r"\\.?",first))
    raise ValueError("unregistered family")

def has_new_gold(text,gold):
    # Conservative skip if a prior model review happens to mention the exact
    # new-task gold as an independent word/token by coincidence.
    return bool(re.search(r"(?<![A-Za-z0-9])"+re.escape(gold)+r"(?![A-Za-z0-9])",text))

class Native18k:
    def __init__(self,root):
        from rawrphos.inference.engine import Engine
        self.e=Engine(root,expected_sha256=CHECKPOINTS["18k"]["sha256"],
                      max_new_tokens=MAX_OUTPUT_TOKENS,threads=2,device="cpu")
        i=self.e.info()
        if i["model_id"]!="rawrphos-native" or i["training_steps"]!=18000:
            raise RuntimeError("wrong actual native original")
        self.name="native18k"
        self.original=self.e.info()["checkpoint_sha256"]
        self.weights_before=weights_digest(self.e.model)
    def __call__(self,prompt):
        tokens=self.e.tokenizer.encode(prompt,add_bos=True)
        if len(tokens)+MAX_OUTPUT_TOKENS>min(384,self.e.model.config.max_seq_len):
            raise RuntimeError("native prompt exceeds trained-context evaluation cap")
        return self.e.complete(prompt,max_tokens=MAX_OUTPUT_TOKENS,
                               seed=SEED,temperature=0,timeout=45)
    def verify_immutable(self):
        return self.weights_before==weights_digest(self.e.model)

class Qwen:
    def __init__(self,root):
        model,tok,count=load_verified("qwen2.5-0.5b",root)
        expected=MODELS["qwen2.5-0.5b"]
        if not expected["expected_parameter_range"][0]<=count<=expected["expected_parameter_range"][1]:
            raise RuntimeError("wrong published Qwen checkpoint")
        self.name="qwen0.5b"; self.model=model; self.tok=tok
        self.original=expected["weights_sha256"]
        self.weights_before=model_param_hash(model)
    def __call__(self,prompt):
        import torch
        tokens=tokens_for_prompt(self.tok,prompt,"official_chat_template")
        if len(tokens)+MAX_OUTPUT_TOKENS>384:
            raise RuntimeError("Qwen prompt exceeds preregistered bound")
        ids=torch.tensor([tokens],dtype=torch.long)
        with torch.inference_mode():
            output=self.model.generate(input_ids=ids,do_sample=False,
                 max_new_tokens=MAX_OUTPUT_TOKENS,
                 eos_token_id=self.tok.eos_token_id,
                 pad_token_id=self.tok.eos_token_id,
                 use_cache=True)
        return self.tok.decode(output[0,len(tokens):].tolist(),skip_special_tokens=True,
                               clean_up_tokenization_spaces=False)
    def verify_immutable(self):
        return self.weights_before==model_param_hash(self.model)

def run(model):
    valid()
    if model.name not in LABELS:
        raise RuntimeError("unregistered original model")
    rows=[]
    for case in CASES:
        # No ground truth is ever in any prompt before the explicitly separate
        # gold_disclosure control. Truth bits are withheld until assistant self
        # review and neutral retry are completed.
        baseline=model(static_question(case["question"]))
        baseline_ok=grade(baseline,case["gold"],case["family"])
        retry=model(revision_prompt(case,baseline,"neutral_retry"))
        own=model(review_prompt(case,baseline))
        own_verdict=verdict(own)
        # Critique may contain an answer but is never externally corrected.
        assisted=model(revision_prompt(case,baseline,"true_correctness_bit",
                                       baseline_correct=baseline_ok))
        misleading=model(revision_prompt(case,baseline,"false_correctness_bit",
                                          baseline_correct=baseline_ok))
        gold_control=model(revision_prompt(case,baseline,"gold_disclosure"))
        transfer_baseline=model(new_task_prompt(case))
        transfer_leak=has_new_gold(own,case["transfer_gold"])
        transfer=model(new_task_prompt(case,critique=own))
        outcomes={
            "baseline":baseline_ok,
            "neutral_retry":grade(retry,case["gold"],case["family"]),
            "self_critique":grade(own,case["gold"],case["family"]),
            "true_correctness_bit":grade(assisted,case["gold"],case["family"]),
            "false_correctness_bit":grade(misleading,case["gold"],case["family"]),
            "gold_disclosure":grade(gold_control,case["gold"],case["family"]),
            "new_task_baseline":grade(transfer_baseline,case["transfer_gold"],case["family"]),
            "new_task_after_critique":grade(transfer,case["transfer_gold"],case["family"])
                                      if not transfer_leak else None,
        }
        rows.append({
            "id":case["id"],"family":case["family"],"conditions":outcomes,
            "semantic_conditions":{
                arm:(semantic_grade(value,case["transfer_gold"] if arm.startswith("new_task") else case["gold"],
                                    case["family"]) if value is not None else None)
                for arm,value in {
                    "baseline":baseline, "neutral_retry":retry,"self_critique":own,
                    "true_correctness_bit":assisted,"false_correctness_bit":misleading,
                    "gold_disclosure":gold_control,"new_task_baseline":transfer_baseline,
                    "new_task_after_critique":transfer if not transfer_leak else None,
                }.items()
            },
            "self_verdict":own_verdict,
            "self_detected_actual_wrong":own_verdict=="INCORRECT" and not baseline_ok,
            "self_false_error_alarm":own_verdict=="INCORRECT" and baseline_ok,
            "critic_contained_new_task_gold":transfer_leak,
            "raw_generation_text_and_short_hashes":"ephemeral in-process only",
        })
    if not model.verify_immutable():
        raise RuntimeError("real original checkpoint parameters changed")
    aggregate={arm:{
        "correct":sum(row["conditions"][arm] is True for row in rows),
        "scored":sum(row["conditions"][arm] is not None for row in rows)
    } for arm in ARMS}
    semantic_aggregate={arm:{
        "correct":sum(row["semantic_conditions"][arm] is True for row in rows),
        "scored":sum(row["semantic_conditions"][arm] is not None for row in rows)
    } for arm in ARMS}
    wrong=[r for r in rows if not r["semantic_conditions"]["baseline"]]
    correct=[r for r in rows if r["semantic_conditions"]["baseline"]]
    measures={
        "baseline_wrong_cases":len(wrong),
        "self_corrected_wrong_cases":sum(r["semantic_conditions"]["self_critique"] for r in wrong),
        "self_harmed_correct_cases":sum(not r["semantic_conditions"]["self_critique"] for r in correct),
        "self_correctly_flagged_wrong_cases":sum(r["self_detected_actual_wrong"] for r in wrong),
        "self_false_alarm_correct_cases":sum(r["self_false_error_alarm"] for r in correct),
        "transfer_gold_leak_cases_excluded":sum(r["critic_contained_new_task_gold"] for r in rows),
        "separate_non_gold_checker_assisted_correct_cases":aggregate["true_correctness_bit"]["correct"],
    }
    # PRECOMMITTED observational threshold; NOT proof of general autonomous
    # correction. Exactly a synthetic eight-case pilot on frozen checkpoints.
    candidate=(len(wrong)>=4 and
        measures["self_corrected_wrong_cases"]>=0.75*len(wrong) and
        measures["self_harmed_correct_cases"]<=1 and
        semantic_aggregate["new_task_after_critique"]["scored"]==8 and
        semantic_aggregate["new_task_after_critique"]["correct"]-
        semantic_aggregate["new_task_baseline"]["correct"]>=2)
    return {
        "schema":"cosmos-genuine-prompt-self-critique-005-v1",
        "model":model.name,"original_checkpoint_sha256":model.original,
        "fixture_sha256":sha(CASES),
        "source_commit":os.getenv("GITHUB_SHA","local-not-attested"),
        "seed":SEED,"max_new_tokens":MAX_OUTPUT_TOKENS,
        "five_different_prompts_before_gold_control":True,
        "weights_unchanged":True,
        "no_owner_memory_training_or_cloud_inference":True,
        "generated_text":"graded transiently, never logged or saved",
        "arms":list(ARMS),"aggregate":aggregate,"semantic_aggregate":semantic_aggregate,
        "correction_measures":measures,
        "synthetic_candidate_self_correction_pattern_observed":bool(candidate),
        "reliable_generative_self_correction_proven":False,
        "cases":rows,
        "limitations":(
          "Only 8 synthetic toy prompts, possible pretrained contamination. "
          "Self-critique is prompted, NOT spontaneous introspection or learning. "
          "A truthful external correctness bit and gold-disclosing oracle are "
          "separate assisted controls, not self-correction. Tokenizer/context, "
          "training size and architecture vary. Novel-task transfer stays "
          "in-context; no persistent learning across process restarts proven."
        )
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",required=True,choices=LABELS)
    p.add_argument("--directory",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.directory.exists():
        p.error("refuse existing original model or evidence directory")
    import torch
    torch.set_num_threads(2)
    if a.model=="native18k":
        from rawrphos.scripts.install_pinned_18k import install
        original=install(a.directory)
        if original!=CHECKPOINTS["18k"]["sha256"]:
            raise RuntimeError("native original integrity mismatch")
        model=Native18k(a.directory)
    else:
        download_and_verify("qwen2.5-0.5b",a.directory)
        os.environ["HF_HUB_OFFLINE"]="1"
        os.environ["TRANSFORMERS_OFFLINE"]="1"
        model=Qwen(a.directory)
    result=run(model)
    raw=canonical(result)+b"\n"
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("xb") as f:f.write(raw)
    print(json.dumps({
        "model":result["model"],"model_original_sha256":result["original_checkpoint_sha256"],
        "fixture_sha256":result["fixture_sha256"],
        "strict_format_aggregate":result["aggregate"],
        "semantic_first_line_aggregate":result["semantic_aggregate"],
        "correction_measures":result["correction_measures"],
        "synthetic_candidate_pattern":result["synthetic_candidate_self_correction_pattern_observed"],
        "reliable_generative_self_correction_proven":False,
        "receipt_sha256":hashlib.sha256(raw).hexdigest(),
        "output":str(a.output),
    },sort_keys=True))
if __name__=="__main__":
    main()
