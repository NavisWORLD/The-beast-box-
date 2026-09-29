"""COSMOS 009: actual generative usefulness of external, model-independent R12 memory.

Four retrieval regimes plus no evidence and an oracle. Every run uses the
IDENTICAL immutable actual pretrained model and identical synthetic questions.
Real product ReconciliationMemory, R12 RefractiveMemoryRouter and AdaptiveControl
do the routing; external reference information is not model training. Synthetic
facts are newly generated and disjoint from the controller's training documents.
No owner memory, no provider API, no production services and no model promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from beastbox.adaptive_control import AdaptiveControl
from beastbox.memory import ReconciliationMemory
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import RefractiveMemoryRouter, WEIGHTS
from scripts.cosmos_learning_challenge import TRAIN_CORPUS, FIXTURE_CLOCK
from scripts.cosmos_public_small_controls_003 import (
    MODELS, download_and_verify, load_verified, model_param_hash,
)

SEEDS=(17,41)
MODELS_UNDER_TEST=("smollm2-135m","qwen2.5-0.5b")
ARMS=("no_evidence","lexical","frozen_r12","adaptive_r12","oracle")
LENGTHS={"short_8_records":8,"long_32_records":32}
GENERATIONS=18
TESTED_PER_LENGTH={"short_8_records":8,"long_32_records":16}
# Synthetic labels invented by fixture generator; tests neither use external
# public data nor rely on published owner memories.
COLORS=("amber","azure","coral","ivory","lime","plum","silver","teal")
OBJECTS=("beacon","cabinet","compass","engine","garden","harbor","lantern","station")

def canonical(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode()

def sha(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def source_fixture(seed:int,length:str):
    """Distinct docs and unambiguous gold computed solely by the evaluator."""
    if seed not in SEEDS or length not in LENGTHS:
        raise ValueError("unregistered research seed or sequence length")
    rng=random.Random(seed*10000 + LENGTHS[length])
    pairs=[(color,obj) for color in COLORS for obj in OBJECTS]
    rng.shuffle(pairs)
    selected=pairs[:LENGTHS[length]]
    # Unique multiples of 10 as stored seeds; the final gold (seed + [2..7])
    # NEVER occurs as the literal documented number in any source snippet.
    numbers=rng.sample(list(range(110,990,10)),LENGTHS[length])
    rows=[{
        "id":index, "name":f"{color} {obj}",
        "seed":numbers[index],
        "text":f"Synthetic notebook for the {color} {obj}. Stored seed number: {numbers[index]}.",
    } for index,(color,obj) in enumerate(selected)]
    # Exactly one query per target document; other records are distractors.
    tests=rng.sample(list(range(len(rows))),TESTED_PER_LENGTH[length])
    cases=[{
        "case_id":f"{length}:{idx}",
        "gold_doc_idx":idx,
        "query":f"For the {rows[idx]['name']} notebook, add {2+(idx%6)} to its stored seed. What is the result?",
        "offset":2+(idx%6),
        "gold":numbers[idx]+2+(idx%6),
    } for idx in tests]
    if len({r["text"] for r in rows})!=len(rows) or len({x["query"] for x in cases})!=len(cases):
        raise RuntimeError("duplicated scientific fixtures")
    if any(str(x["gold"]) in rows[x["gold_doc_idx"]]["text"] for x in cases):
        raise RuntimeError("answer leaked verbatim from target record")
    return rows,cases

def new_control(memory,*, weights=None):
    controller=AdaptiveControl(
        RefractiveMemoryRouter(SimpleNamespace(memory=memory)),
        r12_state=initial_r12_state(),dyn12=[0.0]*12)
    if weights is not None:
        if set(weights)!=set(WEIGHTS):
            raise ValueError("incomplete original product-routing weights")
        controller.weights=dict(weights)
    return controller

def learn_independent_router(seed):
    # Same real synthetic corpus and actual product fit API as original 001;
    # never uses any generated eval memory text, eval query or eval label.
    with tempfile.TemporaryDirectory(prefix="cosmos009-train-") as temp:
        mem=ReconciliationMemory(Path(temp)/"train.sqlite3")
        try:
            order=list(range(len(TRAIN_CORPUS)))
            random.Random(seed).shuffle(order)
            ids={}
            with patch("time.time",return_value=FIXTURE_CLOCK):
                for idx in order:
                    ids[idx]=mem.store(TRAIN_CORPUS[idx][0],kind="synthetic-training")
                control=new_control(mem)
                samples=[{
                    "query":TRAIN_CORPUS[i][1],
                    "preferred_memory_id":ids[i],
                    "reviewed":True,  # Synthetic simulated pseudo-review only.
                } for i in range(len(TRAIN_CORPUS))]
                random.Random(seed+200).shuffle(samples)
                receipt=control.fit(samples)
            if dict(WEIGHTS)!=receipt["frozen_weights"]:
                raise RuntimeError("global original weights changed")
            return control.weights,receipt
        finally:mem.close()

def context_from(row):
    return row["text"] if row is not None else "No notebook record is available."

def controlled_prompt(case, retrieved):
    # Identical template for every condition, only retrieved evidence differs;
    # the final answer is NEVER supplied verbatim in any context.
    return (
        "Use the supplied record, if relevant. If there is no matching record, "
        "do not invent the seed value. Calculate the requested sum. "
        "Answer exactly one line: FINAL: <integer> or FINAL: UNKNOWN.\n"
        "RECORD: "+context_from(retrieved)+"\n"
        "QUESTION: "+case["query"]+"\n"
        "FINAL:"
    )

def retrieval_bundle(seed):
    """Generate reusable records/prompts once: same for BOTH public models."""
    if seed not in SEEDS:
        raise ValueError("research seed must be preregistered")
    weights,training=learn_independent_router(seed)
    out=[]
    for length in LENGTHS:
        documents,problems=source_fixture(seed,length)
        with tempfile.TemporaryDirectory(prefix="cosmos009-holdout-") as temp:
            db=Path(temp)/"holdout.sqlite3"
            mem=ReconciliationMemory(db)
            try:
                ids={}
                order=list(range(len(documents)))
                random.Random(seed+LENGTHS[length]).shuffle(order)
                with patch("time.time",return_value=FIXTURE_CLOCK):
                    for i in order:
                        ids[i]=mem.store(documents[i]["text"],kind="synthetic-evaluation")
                    control=new_control(mem,weights=weights)
                    results=[]
                    for case in problems:
                        ranked=control._candidates(case["query"])
                        if len(ranked)!=len(documents):
                            raise RuntimeError("frozen router did not return complete corpus")
                        frozen=control._rank(ranked,WEIGHTS)
                        adapted=control._rank(ranked,weights)
                        lexical=sorted(ranked,key=lambda r:(
                            r["components"]["lexical"],r["memory_id"]),reverse=True)
                        index={int(row["memory_id"]):row for row in ranked}
                        gold=ids[case["gold_doc_idx"]]
                        if gold not in index:raise RuntimeError("oracle gold document not present")
                        retrieved={
                            "no_evidence":None,
                            "lexical":lexical[0],
                            "frozen_r12":frozen[0],
                            "adaptive_r12":adapted[0],
                            "oracle":index[gold],
                        }
                        records={}
                        for arm in ARMS:
                            row=retrieved[arm]
                            records[arm]={
                                "doc_id":None if row is None else int(row["memory_id"]),
                                "retrieval_correct":None if row is None else int(row["memory_id"])==gold,
                                "prompt":controlled_prompt(case,row),
                                "context":context_from(row),
                            }
                        results.append({
                            "case_id":case["case_id"],"length":length,
                            "gold":case["gold"],"gold_memory_id":gold,
                            "arms":records,
                        })
                    # Preserve data through a real fresh SQLite handle; this
                    # is process-independent on-disk substrate, NOT proof of
                    # an entire live model swap across server restarts.
                    before=hashlib.sha256(db.read_bytes()).hexdigest()
                    mem.close()
                    reopened=ReconciliationMemory(db)
                    try:
                        count=int(reopened.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
                        if count!=len(documents):raise RuntimeError("durable memory reopen mismatch")
                        for idx,id_ in ids.items():
                            row=reopened.db.execute("SELECT text FROM memories WHERE id=?",(id_,)).fetchone()
                            if row is None or row[0]!=documents[idx]["text"]:
                                raise RuntimeError("persistent on-disk original record changed")
                    finally:reopened.close()
                    if not before:raise RuntimeError("empty record state")
                    out.extend(results)
                    continue
            finally:
                try:mem.close()
                except Exception:pass
    if len(out)!=sum(TESTED_PER_LENGTH.values()) or len({r["case_id"] for r in out})!=len(out):
        raise RuntimeError("frozen source task cardinality changed")
    # Report only static synthetic prompt fingerprints; no owner state.
    return out,{"training_corpus_sha256":sha(TRAIN_CORPUS),
                "train_sample_count":training["examples"],
                "frozen_weights":dict(WEIGHTS),"adapted_weights":weights,
                "fit_mistakes":training["mistakes_during_training"]}

def parse_answer(text):
    # Deterministic, first nonempty final line only. A correct number buried
    # in verbose/incorrect text is not strict instruction adherence.
    first=next((s.strip() for s in text.splitlines() if s.strip()),"")
    m=re.fullmatch(r"(?:FINAL:\s*)?([0-9]{1,5}|UNKNOWN)\s*[.]?",first,re.I)
    return m.group(1).upper() if m else None

def model_call(model,tokenizer,prompt):
    import torch
    tokens=tokenizer.apply_chat_template(
        [{"role":"user","content":prompt}],tokenize=True,add_generation_prompt=True)
    if not tokens or len(tokens)+GENERATIONS>384:
        raise RuntimeError("unregistered model context budget exceeded")
    x=torch.tensor([tokens],dtype=torch.long)
    with torch.inference_mode():
        generated=model.generate(
            input_ids=x,do_sample=False,max_new_tokens=GENERATIONS,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,use_cache=True,
        )
    return tokenizer.decode(generated[0,len(tokens):].tolist(),
        skip_special_tokens=True,clean_up_tokenization_spaces=False)

def run_real(seed,label,model,tokenizer):
    if label not in MODELS_UNDER_TEST:
        raise ValueError("model swap is not precommitted")
    all_cases,setup=retrieval_bundle(seed)
    initial=model_param_hash(model)
    started=time.monotonic()
    results=[]
    # Same matched model weights for all routing arms on each query.
    for case in all_cases:
        scores={}
        for arm in ARMS:
            record=case["arms"][arm]
            answer=model_call(model,tokenizer,record["prompt"])
            parsed=parse_answer(answer)
            scores[arm]={
                "retrieved_doc_id":record["doc_id"],
                "retrieval_correct":record["retrieval_correct"],
                "strict_generated_answer_correct":parsed==str(case["gold"]),
                "explicit_abstention":parsed=="UNKNOWN",
                "strict_output_parseable":parsed is not None,
                "synthetic_prompt_sha256":hashlib.sha256(record["prompt"].encode()).hexdigest(),
                "actual_generated_output":answer[:400],
            }
        results.append({"id":case["case_id"],"length":case["length"],
                        "gold":case["gold"],"arms":scores})
    if model_param_hash(model)!=initial:
        raise RuntimeError("public source model parameter tensors changed")
    summary={}
    for length in LENGTHS:
        observed=[r for r in results if r["length"]==length]
        summary[length]={}
        for arm in ARMS:
            rows=[r["arms"][arm] for r in observed]
            summary[length][arm]={
                "correct":sum(r["strict_generated_answer_correct"] for r in rows),
                "count":len(rows),
                "retrieval_correct":None if arm=="no_evidence" else sum(r["retrieval_correct"] for r in rows),
                "abstained":sum(r["explicit_abstention"] for r in rows),
                "parseable":sum(r["strict_output_parseable"] for r in rows),
            }
    return {
        "schema":"cosmos-original-generative-external-substrate-009-seed-model-v1",
        "seed":seed,"subject":label,
        "public_model_repo":MODELS[label]["repo_id"],
        "original_model_revision":MODELS[label]["revision"],
        "original_safetensors_sha256":MODELS[label]["weights_sha256"],
        "trained_model_parameter_sha256_unchanged":initial,
        "fixture_sha256":sha({"seeds":SEEDS,"generator":"009-v1",
                              "labels":COLORS,"objects":OBJECTS,
                              "tests":TESTED_PER_LENGTH}),
        "source_commit":os.environ.get("GITHUB_SHA","local-unattested"),
        "trained_retrieval_on_disjoint_synthetic_pseudo_feedback":setup,
        "arm_order":list(ARMS),
        "memory_sizes":dict(LENGTHS),
        "generated_tokens_cap":GENERATIONS,
        "same_model_all_conditions":True,
        "no_model_weight_training":True,
        "elapsed_wall_seconds":round(time.monotonic()-started,3),
        "summary":summary,"cases":results,
        "limits":(
            "Novel arbitrary synthetic seeded facts (not real external world). "
            "Evidence is required for answerability, so comparing ANY correct "
            "retrieval to no context is partly trivial; conventional strong lexical "
            "and original frozen R12 controls isolate incremental routing gain. "
            "Source document contains seed but NOT final sum, which requires "
            "model computation. Source feedback 'reviewed' is synthetic simulated "
            "retrieval supervision, NOT model-originated feedback; this tests "
            "tool-augmented generative performance, NOT autonomous self-correction. "
            "Longer group is MORE stored records (8 vs 32), NOT transformer "
            "long-context length generalization. Same original disk corpus "
            "is independently recreated for both models; no live service "
            "model-swap continuity test, AGI or 12D native attention benefit."
        )
    }

def summarize(reports):
    expected={(seed,label) for seed in SEEDS for label in MODELS_UNDER_TEST}
    identity={(r["seed"],r["subject"]) for r in reports}
    if len(reports)!=len(expected) or identity!=expected:
        raise ValueError("missing original model/seed evidence or duplicated result")
    if len({r["fixture_sha256"] for r in reports})!=1:
        raise RuntimeError("model-swap test used unmatched synthetic fixtures")
    results=[]
    for label in MODELS_UNDER_TEST:
        for length in LENGTHS:
            rows=[r["summary"][length] for r in reports if r["subject"]==label]
            scores={arm:{
                "correct":sum(r[arm]["correct"] for r in rows),
                "count":sum(r[arm]["count"] for r in rows),
                "retrieval_correct":None if arm=="no_evidence" else
                    sum(r[arm]["retrieval_correct"] for r in rows),
            } for arm in ARMS}
            results.append({"model":label,"length":length,"scores":scores,
                 "adaptive_minus_lexical_correct":scores["adaptive_r12"]["correct"]-
                                                  scores["lexical"]["correct"],
                 "adaptive_minus_frozen_correct":scores["adaptive_r12"]["correct"]-
                                                 scores["frozen_r12"]["correct"]})
    # Predeclared candidate requires positive gains against BOTH strong
    # conventional lexical and frozen R12 baselines for BOTH original models,
    # on both small and large store. Even if observed, 2 synthetic seeds
    # are only a candidate for independent replication, not general benefit.
    candidate=all(row["adaptive_minus_lexical_correct"]>=2 and
                  row["adaptive_minus_frozen_correct"]>=2 and
                  row["scores"]["oracle"]["correct"]>=max(
                      row["scores"]["adaptive_r12"]["correct"],6)
                  for row in results)
    return {
        "schema":"cosmos-original-generative-external-substrate-009-summary-v1",
        "sources":[{"seed":r["seed"],"model":r["subject"],"sha256":sha(r)}
                   for r in reports],
        "results":results,
        "preregistered_multimodel_two_length_candidate_pattern":candidate,
        "reliable_general_generative_improvement_proven":False,
        "native_12d_long_context_advantage_proven":False,
        "limits":"Only two related synthetic fixture seeds per public model; "
                 "source matched per model, not human-trial significance or "
                 "matched compute. This result does not prove model generated "
                 "new learning, unprompted self-correction or 12D causal advantage."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed",type=int,choices=SEEDS)
    p.add_argument("--model",choices=MODELS_UNDER_TEST)
    p.add_argument("--directory",type=Path)
    p.add_argument("--summarize-dir",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error("never overwrite original model evidence")
    if a.summarize_dir is not None:
        if a.model is not None or a.seed is not None:
            p.error("summary must not also run inference")
        reports=[json.loads((a.summarize_dir/f"gen-{seed}-{label}.json").read_text())
                 for seed in SEEDS for label in MODELS_UNDER_TEST]
        report=summarize(reports)
    else:
        if a.model is None or a.seed is None or a.directory is None:
            p.error("model inference needs exact model, seed and empty directory")
        import torch
        torch.set_num_threads(2)
        original=download_and_verify(a.model,a.directory)
        if original["actual_safetensors_sha256"]!=MODELS[a.model]["weights_sha256"]:
            raise RuntimeError("original upstream model changed")
        os.environ["HF_HUB_OFFLINE"]="1"
        os.environ["TRANSFORMERS_OFFLINE"]="1"
        model,tokenizer,_=load_verified(a.model,a.directory)
        report=run_real(a.seed,a.model,model,tokenizer)
    payload=canonical(report)+b"\n"
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("xb") as f:f.write(payload)
    print("COSMOS009_REAL_EVIDENCE="+json.dumps({
        "schema":report["schema"],
        "report_sha256":hashlib.sha256(payload).hexdigest(),
        "source_commit":os.environ.get("GITHUB_SHA","local-unattested"),
        "observations":(len(report["cases"]) if "cases" in report else len(report["results"])),
        "result":report["summary"] if "summary" in report else report["results"],
    },sort_keys=True),flush=True)

if __name__=="__main__":
    main()
