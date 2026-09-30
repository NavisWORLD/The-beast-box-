"""COSMOS 011: audit actual handoffs and calibrate the generator before routing claims.

This audit is a scientific follow-up to the PRESERVED negative 009/010 data,
not a revision of original preregistered scoring or evidence. It diagnoses
whether actual product runtime R12/CNS/feedback handoffs are used, then checks
real original models' oracle-conditioned copy/calculation abilities separately.
No existing owner memory, production service or original weights are touched.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
from statistics import mean
from types import SimpleNamespace

from beastbox.durable import DurableRuntime
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import RefractiveMemoryRouter
from scripts.cosmos_end_to_end_substrate_009 import (
    MODELS, model_param_hash, download_and_verify, load_verified,
    source_fixture, controlled_prompt, parse_answer, retrieval_bundle,
)

SEED=17
SAMPLE_LENGTH="short_8_records"
SAMPLE_CASES=4
BUDGETS=(18,80)
CONDITIONS=("copy_seed","arithmetic_only","original_009_oracle","structured_011_oracle")

def canonical(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode()

def src_hash(x):
    return hashlib.sha256(canonical(x)).hexdigest()

class CapturingProvider:
    model="synthetic-public-runtime-wiring-fixture"
    def __init__(self):self.prompts=[]
    def generate(self,prompt):
        self.prompts.append(prompt)
        return "FINAL: 999"

def actual_product_wiring_audit():
    """Demonstrate real product CNS dynamic state vs untouched original R12."""
    with tempfile.TemporaryDirectory(prefix="cosmos011-real-product-") as root:
        provider=CapturingProvider()
        runtime=DurableRuntime(Path(root),provider=provider)
        before=runtime.r12_state.copy()
        try:
            persisted=runtime.store_external_memory(
                "Synthetic calibration notebook amber beacon: stored seed 480.",
                kind="synthetic-audit")
            a=runtime.respond("Please identify amber beacon stored seed.")
            b=runtime.respond("Please repeat amber beacon seed with provenance.")
            after=runtime.r12_state.copy()
            before_r12_digest=src_hash(before)
            after_r12_digest=src_hash(after)
            cns_delta=any(abs(float(x)-float(y))>1e-8 for x,y in zip(
                a["cns"]["dyn12"],b["cns"]["dyn12"]))
            memory_seen=any(
                m["id"]==persisted["memory_id"] for m in a["memory_hits"]+b["memory_hits"])
            result={
                "actual_product":"beastbox.durable.DurableRuntime, original public repo",
                "synthetic_memory_seen":memory_seen,
                "actual_cns_step_after_turns":runtime.cns.step,
                "cns_dyn12_changes_with_turns":cns_delta,
                "initial_r12_state_sha256":before["state_sha256"],
                "final_r12_state_sha256":after["state_sha256"],
                "r12_sequence_before":before["sequence"],
                "r12_sequence_after":after["sequence"],
                "r12_transition_occurred":after["state_sha256"]!=before["state_sha256"],
                "r12_initial_and_final_coupling":[
                    before["vector"]["reality_coupling"],
                    after["vector"]["reality_coupling"]],
                "actual_two_turn_route_labels":[a["routing"]["router"],b["routing"]["router"]],
                "actual_route_trace":[a["trace"],b["trace"]],
                "original_product_durable_state_same":before_r12_digest==after_r12_digest,
                "only_synthetic_persistent_memory_tested":True,
            }
            if runtime.cns.step!=2 or not memory_seen or not cns_delta:
                raise RuntimeError("product CNS/stored memory preflight is not operative")
            if "r12_routing" not in a["trace"] or len(provider.prompts)!=2:
                raise RuntimeError("product generation/routing stage missing")
            return result
        finally:runtime.close()

def isolated_009_router_audit():
    """Inspect the exact original wrong-domain weights and inactive R12 state."""
    cases,settings=retrieval_bundle(SEED)
    short=[c for c in cases if c["length"]==SAMPLE_LENGTH]
    if len(short)!=8:
        raise RuntimeError("original source frozen eight-case fixture has changed")
    state=initial_r12_state()
    if state["vector"]["reality_coupling"]!=0.0 or state["sequence"]!=0:
        raise RuntimeError("default initial R12 state source unexpectedly changed")
    # Original harness supplies [0]*12 as dyn12; all 12 dimensions constant.
    dummy=RefractiveMemoryRouter(SimpleNamespace(memory=None))
    q=dummy.query_position(short[0]["arms"]["oracle"]["prompt"],sequence=0,
                           dyn12=[0.0]*12)
    reflected,rho=dummy.refract(q,state["vector"])
    no_refraction=max(abs(x-y) for x,y in zip(q,reflected))<1e-12
    return {
        "fixture_seed":SEED,"static_sequence_used_by_009":0,
        "static_dyn12_used_by_009":[0.0]*12,
        "r12_initial_reality_coupling":rho,
        "refractive_reflection_inactive_in_009":no_refraction,
        "original_009_controller_training_corpus_sha256":settings["training_corpus_sha256"],
        "original_009_controller_weights":settings["adapted_weights"],
        "short_eight_original_exact_retrieval":{arm:sum(
            row["arms"][arm]["retrieval_correct"] is True for row in short)
            for arm in ("lexical","frozen_r12","adaptive_r12","oracle")},
        "original_009_retrieval_cases":8,
        "actual_product_adaptive_weights_auto_enabled":False,
        "claim_boundary":"Actual 009 called isolated AdaptiveControl; DurableRuntime routing "
            "calls static WEIGHTS without opt-in AdaptiveControl.fit. This source audit "
            "is not a fresh pretrained generator benchmark."
    }

def format_prompts(case,record):
    """Four frozen, deliberately distinct diagnostic tasks per actual case."""
    source=record["text"]
    seed=record["seed"]
    return {
        "copy_seed":(
            "This is an artificial test. Read exactly this RECORD and answer "
            "with just its stored seed integer. No calculation.\n"
            "RECORD: "+source+"\n"
            "Stored seed number:"),
        "arithmetic_only":(
            "Calculate this arithmetic expression. Reply with the final "
            "integer only, no explanation.\n"
            f"{seed} + {case['offset']} ="),
        "original_009_oracle":controlled_prompt(case,{"text":source}),
        "structured_011_oracle":(
            "This is an artificial record-and-calculation test.\n"
            "The relevant exact record is:\n"
            f"Notebook: {record['name']}\n"
            f"Stored seed: {seed}\n"
            f"Add: {case['offset']}\n"
            "Calculate Stored seed + Add. Return the final integer only."),
    }

def first_line_semantic(raw,seed,offset):
    """Report separately from unchanged prior STRICT parser. No gold substring credit."""
    strict=parse_answer(raw)
    if strict is not None:return strict
    first=next((s.strip() for s in raw.splitlines() if s.strip()),"")
    variants=[
        r"(?i:the\s+(?:final\s+)?answer\s+is\s*)(\d{1,5})[.!]?",
        r"(?i:(?:result|answer)\s*[:=]\s*)(\d{1,5})[.!]?",
        r"(\d{1,5})\s*\+\s*(\d{1,5})\s*(?:=|is)\s*(\d{1,5})[.!]?",
    ]
    for pattern in variants:
        m=re.fullmatch(pattern,first)
        if not m:continue
        if len(m.groups())==1:return m.group(1)
        if int(m.group(1))==seed and int(m.group(2))==offset:
            return m.group(3)
    return None

def generate(model,tokenizer,prompt,budget):
    import torch
    if budget not in BUDGETS:
        raise ValueError("not preregistered oracle calibration budget")
    tokens=tokenizer.apply_chat_template([
        {"role":"user","content":prompt}],tokenize=True,add_generation_prompt=True)
    if not isinstance(tokens,list) or len(tokens)+budget>384:
        raise ValueError("oracle diagnostic does not fit original 384-token evaluation envelope")
    initial=torch.tensor([tokens],dtype=torch.long)
    with torch.inference_mode():
        output=model.generate(
            input_ids=initial,do_sample=False,max_new_tokens=budget,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,use_cache=True,
        )
    return {
        "text":tokenizer.decode(output[0,len(tokens):].tolist(),
                                skip_special_tokens=True,clean_up_tokenization_spaces=False),
        "input_tokens":len(tokens),
        "output_tokens":len(output[0])-len(tokens),
    }

def real_oracle_diagnostic(label,model,tokenizer):
    if label not in ("qwen2.5-0.5b","smollm2-135m"):
        raise ValueError("unknown original published calibration checkpoint")
    docs,cases=source_fixture(SEED,SAMPLE_LENGTH)
    cases=cases[:SAMPLE_CASES]
    first_hash=model_param_hash(model)
    results=[]
    for case in cases:
        source=docs[case["gold_doc_idx"]]
        prompts=format_prompts(case,source)
        for budget in BUDGETS:
            for condition in CONDITIONS:
                actual=generate(model,tokenizer,prompts[condition],budget)
                want=str(source["seed"] if condition=="copy_seed" else case["gold"])
                strict=parse_answer(actual["text"])
                semantic=first_line_semantic(actual["text"],source["seed"],case["offset"])
                results.append({
                    "case_id":case["case_id"],"condition":condition,"budget":budget,
                    "expected":want,"input_tokens":actual["input_tokens"],
                    "output_tokens":actual["output_tokens"],
                    "strict_correct":strict==want,
                    "semantic_correct":semantic==want,
                    "strict_parseable":strict is not None,
                    "semantic_parseable":semantic is not None,
                    "prompt_sha256":hashlib.sha256(prompts[condition].encode()).hexdigest(),
                    # All 011 inputs are random synthetic nonsense, not owner memory.
                    # Keep bounded literal diagnostics for independent scorer audit.
                    "synthetic_only_literal_model_output":actual["text"][:256],
                })
    if model_param_hash(model)!=first_hash:
        raise RuntimeError("original checkpoint was modified in oracle diagnostic")
    aggregate={}
    for budget in BUDGETS:
        aggregate[str(budget)]={}
        for cond in CONDITIONS:
            matches=[x for x in results if x["budget"]==budget and x["condition"]==cond]
            aggregate[str(budget)][cond]={
                "strict_correct":sum(x["strict_correct"] for x in matches),
                "semantic_correct":sum(x["semantic_correct"] for x in matches),
                "count":len(matches),
                "strict_parseable":sum(x["strict_parseable"] for x in matches),
                "semantic_parseable":sum(x["semantic_parseable"] for x in matches),
            }
    return {
        "schema":"cosmos-wiring-real-oracle-calibration-011-v1",
        "subject":label,
        "original_model_revision":MODELS[label]["revision"],
        "original_full_weights_sha256":MODELS[label]["weights_sha256"],
        "original_parameter_digest_unchanged":first_hash,
        "fixture_seed":SEED,"evaluated_cases":SAMPLE_CASES,
        "input_context_max_tokens":384,
        "budgets":list(BUDGETS),"conditions":list(CONDITIONS),
        "aggregate":aggregate,"observations":results,
        "calibration_gate":(
            "Reporting only. If correct source SEED COPY is poor, do not "
            "interpret low sum accuracy as a pure R12 retrieval failure. "
            "If seed copy succeeds but standalone arithmetic fails, arithmetic "
            "is a bottleneck. If structured oracle succeeds but original oracle "
            "fails, original prompt/format is a bottleneck. Even all gates "
            "passing would NOT prove an adaptive COSMOS retrieval advantage."
        ),
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audit-only",action="store_true")
    p.add_argument("--model",choices=("qwen2.5-0.5b","smollm2-135m"))
    p.add_argument("--directory",type=Path)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        p.error("do not overwrite any original research receipt")
    if args.audit_only:
        if args.model is not None or args.directory is not None:
            p.error("source-only audit cannot load models")
        report={
            "schema":"cosmos-real-product-routing-audit-011-v1",
            "durable_original_runtime":actual_product_wiring_audit(),
            "isolated_original_009_harness":isolated_009_router_audit(),
        }
    else:
        if args.model is None or args.directory is None:
            p.error("oracle calibration requires exact published model and empty directory")
        import os,torch
        torch.set_num_threads(2)
        receipt=download_and_verify(args.model,args.directory)
        if receipt["actual_safetensors_sha256"]!=MODELS[args.model]["weights_sha256"]:
            raise RuntimeError("original full source checkpoint hash mismatch")
        os.environ["HF_HUB_OFFLINE"]="1"
        os.environ["TRANSFORMERS_OFFLINE"]="1"
        model,tokenizer,_=load_verified(args.model,args.directory)
        report=real_oracle_diagnostic(args.model,model,tokenizer)
    payload=canonical(report)+b"\n"
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("xb") as f:f.write(payload)
    print("COSMOS011_EVIDENCE="+json.dumps({
        "schema":report["schema"],
        "original_receipt_sha256":hashlib.sha256(payload).hexdigest(),
        "source_commit":__import__("os").environ.get("GITHUB_SHA","local-unattested"),
        "results":report if args.audit_only else report["aggregate"],
    },sort_keys=True))
if __name__=="__main__":
    main()
