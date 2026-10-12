#!/usr/bin/env python3
"""Experiment 012: CPU-only grounded world-vocabulary *research* fork from verified Zeref 006 cycle 5.

Retrieval evidence is always in the prompt, never claimed as learned from IBM/Azure data.
The pinned byte-BPE tokenizer is immutable. This trial NEVER overwrites the accepted 006
lineage, changes the ROM, reads private chat/camera/microphone, or promotes a model.
"""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
import random
import shutil
import time
from pathlib import Path

import torch
from rawrphos.inference.engine import Engine
from rawrphos.training.checkpoint import load_checkpoint, save_checkpoint, parameter_hash, rng_state
from train_rawrphos_from_observed_native_play import tokens, collate, nll, prompt, valid

QBEAST = "bb-deada969"
EXPECTED_PARENT = "460a1a3fbbc16919c5030af16d5bd451ef43e96fd28b8c3201ca7efca1250ef2"
EXPECTED_ROOT = "37ca3f8fc9cdc0e78175508fc816ed02d5a12da1f3b106505715b7366fde5a48"
EXPECTED_NATIVE_CYCLE = 38210153369
CARDS = Path("research/zeref/world-vocab-012/grounded-cards.json")
OUT = Path("build/zeref-world-vocab-012")
UPDATES = 96
SEED = 20261012
LR = 0.000004

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def write(name: str, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/name).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n")

def load_cards():
    data = json.loads(CARDS.read_text(encoding="utf-8"))
    if data.get("schema") != "zeref-world-knowledge-cards/v1" or data.get("training_identity") != QBEAST:
        raise ValueError("World card schema / Zeref identity mismatch")
    rows = data.get("cards")
    if not isinstance(rows, list) or len(rows) < 20:
        raise ValueError("Insufficient factual evidence")
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Overlapping world knowledge IDs")
    parts = {"train": [], "holdout": []}
    for r in rows:
        if r.get("split") not in parts:
            raise ValueError("Unsupported knowledge split")
        if not r.get("source_url", "").startswith(("https://science.nasa.gov/", "https://www.usgs.gov/", "https://www.nist.gov/", "https://oceanservice.noaa.gov/")):
            raise ValueError("Missing or unapproved primary-source URL")
        if not all(isinstance(r.get(k), str) and r[k].strip() for k in ("id", "question", "evidence", "answer", "source_name", "provenance")):
            raise ValueError("Incomplete world evidence card")
        if r["answer"].casefold() not in r["evidence"].casefold():
            raise ValueError("Answer is not present in the evidence text")
        parts[r["split"]].append(r)
    if len(parts["train"]) < 20 or len(parts["holdout"]) < 5:
        raise ValueError("Both independent curriculum splits required")
    return parts, sha(CARDS.read_bytes())

def world_prompt(r):
    return "Evidence: "+r["evidence"]+"\nQuestion: "+r["question"]+"\nAnswer: "

def load_native(native_dir):
    files = list(Path(native_dir).rglob("native-observation-actions.jsonl"))
    manifests = list(Path(native_dir).rglob("native-evidence-manifest.json"))
    if len(files) != 1 or len(manifests) != 1:
        raise ValueError("Pinned original-ROM evidence artifact missing or ambiguous")
    raw = files[0].read_bytes()
    manifest = json.loads(manifests[0].read_text())
    rows = [json.loads(x) for x in raw.splitlines() if x]
    if (manifest.get("qbeast_id") != QBEAST or manifest.get("events") != 56
            or manifest.get("source_class") != "ORIGINAL_EMULATOR_NATIVE_PIXEL_OBSERVATIONS"
            or manifest.get("jsonl_sha256") != sha(raw)
            or len(rows) != 56 or {r.get("episode") for r in rows} != {0,1,2,3}):
        raise ValueError("Original native screen capture or digest did not validate")
    if any(r.get("reward_is_not_native_progress") is not True
           or r.get("teacher") != "OBSERVATION_CONDITIONED_SCRIPTED_HEURISTIC_NOT_HUMAN_NOT_MODEL"
           or len(r.get("native_ack_digest", "")) != 64 for r in rows):
        raise ValueError("Native script teacher or controller evidence invalid")
    return rows, sha(raw)

def verify_parent(path):
    p = Path(path)
    parent = load_checkpoint(p, expected_checkpoint_sha256=EXPECTED_PARENT, load_training_state=True)
    m = parent["metadata"]
    a = json.loads((p.parent/"approval.json").read_text())
    if not (m.get("qbeast_id") == QBEAST and m.get("canonical_lineage_root_sha256") == EXPECTED_ROOT
            and m.get("approved_cycle_count") == 5 and m.get("production_promoted") is False
            and a.get("approved") is True and a.get("checkpoint_sha256") == EXPECTED_PARENT
            and a.get("approved_cycle_count") == 5 and a.get("qbeast_id") == QBEAST
            and "optimizer" in parent["state"] and m.get("training_steps") == 14448):
        raise ValueError("Not the exactly approved Zeref 006 cycle-5 model and AdamW lineage")
    return parent

def exact_answers(model_path, cards):
    engine = Engine(model_path, max_new_tokens=32, threads=2)
    results = []
    for i, r in enumerate(cards):
        answer = engine.complete(world_prompt(r), max_tokens=32, temperature=0,
                                 seed=SEED+i, timeout=35).strip()
        results.append({"id":r["id"], "reply":answer,
                        "exact_answer":answer.casefold().strip(" .") == r["answer"].casefold().strip(" ."),
                        "source":r["source_url"]})
    return results

def stats(items):
    return {"correct":sum(bool(r["exact_answer"]) for r in items),
            "total":len(items)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", required=True)
    parser.add_argument("--native", required=True)
    args = parser.parse_args()
    start = time.perf_counter()
    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    random.seed(SEED)
    torch.use_deterministic_algorithms(True)
    facts, cards_sha = load_cards()
    native, native_sha = load_native(args.native)
    parent = verify_parent(args.parent)
    model, tok = parent["model"], parent["tokenizer"]
    original_tok_sha = tok.sha256
    if tok.vocab_size != 4096:
        raise ValueError("Unexpected tokenizer size; no vocabulary resize authorized")
    # Byte-level coverage means a text can be represented, NOT that words are understood.
    examples = facts["train"] + facts["holdout"]
    roundtrips = [r for r in examples if tok.decode(tok.encode(world_prompt(r)+r["answer"])) != world_prompt(r)+r["answer"]]
    if roundtrips:
        raise ValueError("World terms did not roundtrip through frozen byte-BPE")
    world_train = [tokens(tok, world_prompt(r), r["answer"]) for r in facts["train"]]
    world_eval = [tokens(tok, world_prompt(r), r["answer"]) for r in facts["holdout"]]
    # Provenance-true abstention examples; these are hand-authored, not sourced positive facts.
    abstain_train = []
    for i in range(8):
        a, b = facts["train"][i], facts["train"][-(i+1)]
        abstain_train.append(tokens(tok,
            "Evidence: "+a["evidence"]+"\nQuestion: "+b["question"]+"\nAnswer: ",
            "Not enough evidence."))
    abstain_eval = []
    for i in range(3):
        a,b=facts["holdout"][i],facts["holdout"][-(i+1)]
        abstain_eval.append(tokens(tok,
            "Evidence: "+a["evidence"]+"\nQuestion: "+b["question"]+"\nAnswer: ",
            "Not enough evidence."))
    native_train = [tokens(tok, prompt(r), "ACTION: "+r["action"]) for r in native if r["episode"] < 3]
    native_eval = [tokens(tok, prompt(r), "ACTION: "+r["action"]) for r in native if r["episode"] == 3]
    if len(native_train) != 42 or len(native_eval) != 14:
        raise ValueError("Native heldout split failed")
    retention = [tokens(tok, "User: Say hello.\nAssistant: ", "Hello."),
                 tokens(tok, "User: What is two plus two?\nAssistant: ", "Four.")]
    baseline = {"world_nll":nll(model, world_eval), "abstain_nll":nll(model, abstain_eval),
                "native_nll":nll(model, native_eval), "language_nll":nll(model, retention)}
    parent_hash = parameter_hash(model)
    # Trainer uses genuine previous 006 optimizer moments. The pilot is a separate
    # shadow branch: accepted world weights never overwrite canonical 006 artifacts.
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=.01)
    opt.load_state_dict(parent["state"]["optimizer"])
    for group in opt.param_groups:
        group["lr"] = LR
    gen = torch.Generator().manual_seed(SEED)
    metrics = []
    for i in range(UPDATES):
        opt.zero_grad(set_to_none=True)
        world_batch = [world_train[k] for k in torch.randint(len(world_train),(2,),generator=gen).tolist()]
        ab = abstain_train[int(torch.randint(len(abstain_train),(1,),generator=gen)[0])]
        nav = native_train[int(torch.randint(len(native_train),(1,),generator=gen)[0])]
        x,y,mask=collate(world_batch+[ab,nav])
        loss=model(x,targets=y,attention_mask=mask)["loss"]
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("World vocabulary optimizer produced non-finite loss")
        loss.backward()
        g=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        opt.step()
        if (i+1)%24 == 0:
            event={"update":i+1,"train_loss":round(float(loss.detach()),5),"grad_norm":round(float(g),5)}
            metrics.append(event)
            print("ZEREF_012_CPU_UPDATE="+json.dumps(event),flush=True)
    candidate_parameter_hash = parameter_hash(model)
    if candidate_parameter_hash == parent_hash:
        raise AssertionError("No neural weights were changed")
    result = {"world_nll":nll(model,world_eval),"abstain_nll":nll(model,abstain_eval),
              "native_nll":nll(model,native_eval),"language_nll":nll(model,retention)}
    target = OUT/"shadow-candidate"
    meta={"schema":"rawrphos-zeref-world-vocab-shadow-012",
          "qbeast_id":QBEAST,"parent_checkpoint_sha256":EXPECTED_PARENT,
          "canonical_lineage_root_sha256":EXPECTED_ROOT,
          "training_steps":parent["metadata"]["training_steps"]+UPDATES,
          "cycle_optimizer_updates":UPDATES,"cards_sha256":cards_sha,
          "native_evidence_sha256":native_sha,
          "source":"agency-backed human paraphrases, retrieved in prompt",
          "production_promoted":False,"canonical_training_parent_eligible":False,
          "uses_IBM_quantum_jobs":False,"no_external_camera_or_private_chat":True}
    saved=save_checkpoint(target,model,tok,meta,
                          {"optimizer":opt.state_dict(),"rng":rng_state(),"data_rng":gen.get_state()})
    load_checkpoint(target,expected_checkpoint_sha256=saved["checkpoint_sha256"],load_training_state=True)
    parent_outputs=exact_answers(args.parent,facts["holdout"])
    candidate_outputs=exact_answers(target,facts["holdout"])
    ps,cs=stats(parent_outputs),stats(candidate_outputs)
    gates={
      "G1_world_heldout_nll_improves":result["world_nll"] < baseline["world_nll"],
      "G2_native_heldout_nll_within_5pct":result["native_nll"] <= max(.01,baseline["native_nll"]*1.05),
      "G3_basic_language_retention_within_10pct":result["language_nll"] <= max(.01,baseline["language_nll"]*1.1),
      "G4_unsupported_question_nll_not_worse":result["abstain_nll"] <= baseline["abstain_nll"]*1.05,
      "G5_source_grounded_generated_answers_not_worse":cs["correct"]>=ps["correct"] and cs["correct"]>0,
      "G6_frozen_tokenizer_and_checkpoint_integrity":tok.sha256==original_tok_sha and saved["tokenizer_sha256"]==original_tok_sha
    }
    accepted=all(gates.values())
    report={"schema":"zeref-world-vocab-012-report/v1","accepted_as_research_shadow":accepted,
            "production_promoted":False,"canonical_006_checkpoint_unchanged":True,
            "qbeast_id":QBEAST,"checkpoint_parent":EXPECTED_PARENT,
            "checkpoint_candidate":saved["checkpoint_sha256"],
            "source_cards_sha256":cards_sha,"original_native_run":EXPECTED_NATIVE_CYCLE,
            "original_native_evidence_sha256":native_sha,
            "tokenizer_sha256":original_tok_sha,"vocab_size":tok.vocab_size,
            "token_roundtrip_ok":True,
            "training_updates":UPDATES,"lr":LR,"train_card_count":len(facts["train"]),
            "heldout_card_count":len(facts["holdout"]),
            "source_urls":sorted({r["source_url"] for r in examples}),
            "baseline":baseline,"candidate":result,
            "parent_generation":parent_outputs,"candidate_generation":candidate_outputs,
            "exact_grounded_answers":{"parent":ps,"candidate":cs},
            "gates":gates,"training_logs":metrics,
            "world_knowledge_claim":"small closed-card retrieval test, not general world knowledge",
            "native_progress_proven":False,
            "ibm_jobs_submitted":0,"azure_quantum_jobs_submitted":0,
            "camera_mic_chat_trained":False,"elapsed_seconds":round(time.perf_counter()-start,3)}
    write("report.json",report)
    print("ZEREF_012_WORLD_KNOWLEDGE_GATE="+json.dumps({
        "accepted":accepted,"gates":gates,"baseline":baseline,"candidate":result,
        "exact_grounded_answers":{"parent":ps,"candidate":cs},
        "sha256":saved["checkpoint_sha256"]}),flush=True)
    if accepted:
        target.rename(OUT/"accepted-shadow-checkpoint")
        write("approval.json",{"approved_research_shadow":True,
                               "production_promoted":False,
                               "canonical_training_parent_eligible":False,
                               "candidate_checkpoint_sha256":saved["checkpoint_sha256"]})
    else:
        shutil.rmtree(target)
        write("rejected.json",{"approved":False,"reason":"World answer, native or language gate failed",
                               "do_not_use_as_parent":True,
                               "candidate_checkpoint_sha256":saved["checkpoint_sha256"]})
    return 0

if __name__=="__main__":
    main()
