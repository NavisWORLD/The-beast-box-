#!/usr/bin/env python3
"""Zeref 012D: continue language weights, retrain isolated game weights, test explicit routing.

Two distinct descendant weight sets from one verified Zeref 006 ancestor. No
single-model success claim, no unverified quantum/game labels, no live switch.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

import torch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zeref_experiment_011 as E
import zeref_experience_bridge as B
import zeref_012c_joint_training as C
from rawrphos.training.checkpoint import load_checkpoint,save_checkpoint,parameter_hash,rng_state,hash_file

SCHEMA="zeref-012d-dual-route-research/v1"
LANG_SOURCE_REPORT_SHA="347345a6aaccb21a7b693c9932e52ec3a3f3bbeffb89145f842b1ea689bde032"
PARENT=E.PARENT_SHA
ROLE_BRANCH={"pocket":"game","native":"game","dialogue":"language"}
NEW_DIALOGUE_PROBES=(
 ("Can you explain what a saved model is?","It is a recorded checkpoint of a model's learned parameters."),
 ("What if you did not see the screen?","I should ask for the current observation instead of guessing."),
 ("Give me a greeting without a long story.","Hello! What would you like to try?"),
 ("What do I do when a command fails?","Check the result, remember the failure, and choose another action."),
 ("Can you describe your memory boundaries?","My model and each visitor's saved experiences are different things."),
 ("I want a short cosmic joke.","My spaceship had a syntax error, so it took the scenic route."),
 ("You have no timestamp. Is that a live IBM result?","No. I cannot verify a live run without provider evidence."),
 ("Explain what a simulation proves.","It measures behavior under simulated rules, not physical hardware outcomes."),
 ("What if you make a wrong claim?","Correct it and explain the evidence behind the correction."),
 ("Why test unfamiliar levels?","Unseen levels reveal whether learned behavior generalizes."),
 ("Can I use my own companion history privately?","Yes. Your saved experience should stay isolated from other visitors."),
 ("What is the difference between a game policy and chat?","A game policy chooses actions; chat generates conversational replies."),
)

def route(task:str)->str:
    if task not in ROLE_BRANCH:
        raise ValueError("Explicit trusted task type required; no guessed or owner-memory routing")
    return ROLE_BRANCH[task]

def guarded_choice(raw:str,obs:dict):
    key=B.valid_action(raw,B.POCKET_KEYS)
    neighbors=obs.get("neighbors",{})
    if key=="WAIT": return "WAIT","model_wait"
    if key in neighbors and neighbors[key].get("kind")=="open":
        return key,"model_safe"
    open_=[k for k in ("UP","DOWN","LEFT","RIGHT")
           if neighbors.get(k,{}).get("kind")=="open"]
    if not open_: return "WAIT","no_open_neighbor"
    frontier=obs.get("frontier")
    if frontier in open_:
        return frontier,"guard_frontier"
    ranked=sorted(open_,key=lambda k:(neighbors[k].get("visits",999),k))
    return ranked[0],"guard_unvisited_first"

def run_guarded(pocket,keys,model,tok):
    episodes=[];overrides=0;legal=0;total=0;decisions={}
    for layout in keys:
        obs=pocket.reset(layout,40)
        while True:
            response=E.reply(model,tok,B.pocket_prompt(obs))
            predicted=B.valid_action(response,B.POCKET_KEYS)
            if predicted is not None:legal+=1
            action,reason=guarded_choice(response,obs)
            decisions[reason]=decisions.get(reason,0)+1
            if reason not in ("model_safe","model_wait"):overrides+=1
            total+=1
            event=pocket.call(op="step",action=action,policy="zeref-012d-explicit-guard")
            obs=event["obs"]
            if event["done"]:break
        episodes.append({"key":layout,**pocket.call(op="metrics")["metrics"]})
    result=E.summarize(episodes,legal,total)
    return {**result,"guarded":True,"override_count":overrides,"decision_reason_counts":decisions}

def verify_language_source(folder:Path):
    report_file=folder/"report.json"
    data=report_file.read_bytes()
    if hashlib.sha256(data).hexdigest()!=LANG_SOURCE_REPORT_SHA:
        raise ValueError("012C report does not match published experiment proof")
    report=json.loads(data)
    if (report.get("schema")!="zeref-012c-joint-game-dialogue/v1"
        or report.get("canonical_parent_checkpoint_sha256")!=PARENT
        or report.get("shadow_checkpoint") is None
        or report.get("passes_this_bounded_pilot") is not False
        or report.get("production_promoted") is not False
        or report.get("private_user_chats_used") is not False
        or report.get("evidence_quantum_action_pairs")!=0):
        raise ValueError("Untrusted 012C language descendant")
    shadow=folder/"shadow-joint-checkpoint"
    ck=load_checkpoint(shadow,expected_checkpoint_sha256=report["shadow_checkpoint"],load_training_state=True)
    m=ck["metadata"]
    if (m.get("schema")!="zeref-012c-joint-language-game-shadow/v1"
        or m.get("qbeast_id")!=E.ZEREF
        or m.get("parent_checkpoint_sha256")!=PARENT
        or m.get("production_promoted") is not False
        or m.get("canonical_training_parent_eligible") is not False
        or m.get("public_synthetic_dialogue_only") is not True
        or m.get("quantum_action_pairs")!=0):
        raise ValueError("012C shadow checkpoint is not research-only Zeref lineage")
    return ck,report

def formatted_language(tok):
    return [E.tokens(tok,"User: "+question+"\nAssistant: ",answer) for question,answer in NEW_DIALOGUE_PROBES]

def score_language(model,tok,held):
    s={"previous_20_heldout_nll":round(E.nll(model,C.talk_tokens(tok,held)),6),
       "fresh_12_probe_nll":round(E.nll(model,formatted_language(tok)),6),
       "basic_retention_nll":round(E.retention_nll(model,tok),6)}
    samples=[]
    for q,_ in NEW_DIALOGUE_PROBES[:6]:
        text=E.reply(model,tok,"User: "+q+"\nAssistant: ",max_new=28)
        samples.append({"user":q,"actual_generated_reply":text})
    s["generated_replies"]=samples
    return s

def optimize(model,opt,data,steps,seed,label,batch=8):
    if not 1<=steps<=192:raise ValueError("Bounded updates required")
    rng=torch.Generator().manual_seed(seed)
    logs=[]
    for step in range(steps):
        model.train()
        picks=torch.randint(len(data),(batch,),generator=rng).tolist()
        selected=[data[k] for k in picks]
        x,y,m=E.collate(selected)
        opt.zero_grad(set_to_none=True)
        loss=model(x,targets=y,attention_mask=m)["loss"]
        if not bool(torch.isfinite(loss)):raise FloatingPointError("Nonfinite "+label+" loss")
        loss.backward()
        g=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        if not bool(torch.isfinite(g)):raise FloatingPointError("Nonfinite "+label+" gradient")
        opt.step()
        if step==0 or (step+1)%32==0:
            x={"arm":label,"step":step+1,"loss":round(float(loss.detach()),6),
               "grad_norm":round(float(g),6)}
            logs.append(x);print("ZEREF_012D_UPDATE="+json.dumps(x),flush=True)
    return rng,logs

def new_optimizer(ck,lr):
    model=ck["model"]
    opt=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=.01)
    opt.load_state_dict(ck["state"]["optimizer"])
    for p in opt.param_groups:p["lr"]=lr
    if not all("exp_avg" in x and "exp_avg_sq" in x for x in opt.state.values()):
        raise ValueError("The approved optimizer moments were not resumed")
    return opt

def snapshot(path,ck,opt,rng,source_sha,updates,task):
    model,tok=ck["model"],ck["tokenizer"]
    parent_sha=ck["metadata"]["checkpoint_sha256"]
    meta={"schema":"zeref-012d-research-branch/v1","qbeast_id":E.ZEREF,
          "parent_checkpoint_sha256":parent_sha,"origin_approved_checkpoint_sha256":PARENT,
          "task_branch":task,"explicit_route_only":True,
          "training_steps":ck["metadata"]["training_steps"]+updates,
          "research_only":True,"production_promoted":False,
          "canonical_training_parent_eligible":False,
          "source_sha256":source_sha,"quantum_action_pairs":0,
          "private_visitor_data_used":False}
    saved=save_checkpoint(path,model,tok,meta,{"optimizer":opt.state_dict(),"rng":rng_state(),"data_rng":rng.get_state()})
    reloaded=load_checkpoint(path,expected_checkpoint_sha256=saved["checkpoint_sha256"],load_training_state=True)
    if parameter_hash(reloaded["model"])!=parameter_hash(model):
        raise AssertionError("Research branch cannot reload with equal neural parameters")
    return saved["checkpoint_sha256"]

def experiment(parent_dir:Path,previous_dir:Path,game_dir:Path,native_dir:Path,out:Path,
               *,game_steps=160,language_steps=64,seed=12026,eval_count=8,threads=3):
    if not(1<=threads<=8 and 1<=game_steps<=192 and 1<=language_steps<=128 and 4<=eval_count<=24):
        raise ValueError("Bounded trial only")
    torch.set_num_threads(threads);torch.use_deterministic_algorithms(True)
    torch.manual_seed(seed);random.seed(seed)
    game,game_sha,_,_=C.verified_game(game_dir)
    native_train,native_held,native_sha,_=C.verified_native(native_dir)
    train_lang,held_lang,lang_manifest=C.dialogue_rows()
    previous,old_report=verify_language_source(previous_dir)
    ancestor=E.load_parent(parent_dir)
    approved_hash=parameter_hash(ancestor["model"])
    if ancestor["tokenizer"].sha256!=previous["tokenizer"].sha256:
        raise ValueError("Branches must use identical tokenizer and model ancestry")
    parent_language=score_language(ancestor["model"],ancestor["tokenizer"],held_lang)
    previous_language=score_language(previous["model"],previous["tokenizer"],held_lang)
    baseline_native=E.native_eval(ancestor["model"],ancestor["tokenizer"],native_held)
    keys=["exp012d-fresh-eval-"+str(k) for k in range(eval_count)]
    pocket=E.Pocket()
    try:
        heuristic={name:E.run_policy(pocket,keys,40,name)
                   for name in ("random","pocket-learner","greedy-frontier")}
        approved_raw=E.run_policy(pocket,keys,40,"approved-zeref-parent",
                                   model=ancestor["model"],tok=ancestor["tokenizer"])
        approved_guarded=run_guarded(pocket,keys,ancestor["model"],ancestor["tokenizer"])
    finally:pocket.close()

    out.mkdir(parents=True,exist_ok=False)
    game_ck=E.load_parent(parent_dir)
    game_model,game_tok=game_ck["model"],game_ck["tokenizer"]
    game_opt=new_optimizer(game_ck,1e-5)
    game_tokens=C.game_tokens(game_tok,game)
    native_tokens=[E.tokens(game_tok,r["prompt"],r["target"]) for r in native_train]
    game_batches=game_tokens+[native_tokens[i%len(native_tokens)] for i in range(max(1,len(game_tokens)//7))]
    game_hash_before=parameter_hash(game_model)
    gen_g,game_logs=optimize(game_model,game_opt,game_batches,game_steps,seed,"game")
    game_hash_after=parameter_hash(game_model)
    if game_hash_before==game_hash_after:raise AssertionError("Game neural branch did not update")
    game_native=E.native_eval(game_model,game_tok,native_held)
    pocket=E.Pocket()
    try:
        game_raw=E.run_policy(pocket,keys,40,"012d-game-raw",model=game_model,tok=game_tok)
        game_guarded=run_guarded(pocket,keys,game_model,game_tok)
    finally:pocket.close()
    game_sha_ck=snapshot(out/"game-checkpoint",game_ck,game_opt,gen_g,game_sha,game_steps,"game")
    del game_ck,game_model,game_opt

    lang_model,lang_tok=previous["model"],previous["tokenizer"]
    lang_opt=new_optimizer(previous,7e-6)
    lang_before=parameter_hash(lang_model)
    lang_tokens=C.talk_tokens(lang_tok,train_lang)
    gen_l,lang_logs=optimize(lang_model,lang_opt,lang_tokens,language_steps,seed+17,"language")
    lang_after=parameter_hash(lang_model)
    if lang_before==lang_after:raise AssertionError("Language neural branch did not update")
    lang_final=score_language(lang_model,lang_tok,held_lang)
    lang_sha_ck=snapshot(out/"language-checkpoint",previous,lang_opt,gen_l,
                         lang_manifest["train_sha256"],language_steps,"language")
    del previous,lang_model,lang_opt

    reloaded=E.load_parent(parent_dir)
    if parameter_hash(reloaded["model"])!=approved_hash:
        raise AssertionError("Approved canonical Zeref checkpoint modified")
    # Each branch must be independently addressable. No heuristic chat auto-routing.
    assert route("pocket")==route("native")=="game" and route("dialogue")=="language"
    if game_sha_ck==lang_sha_ck:raise AssertionError("Two skills incorrectly share weight identity")
    gates={
      "G1_game_raw_coverage_beats_approved_parent":
        game_raw["mean"]["cells_visited"]>approved_raw["mean"]["cells_visited"],
      "G2_game_guarded_coverage_beats_heuristic_learner":
        game_guarded["mean"]["cells_visited"]>heuristic["pocket-learner"]["mean"]["cells_visited"],
      "G3_game_guarded_blocked_no_worse_than_learner":
        game_guarded["mean"]["blocked"]<=heuristic["pocket-learner"]["mean"]["blocked"],
      "G4_game_raw_coverage_not_due_only_to_guard":
        game_raw["mean"]["cells_visited"]>=game_guarded["mean"]["cells_visited"]*.65,
      "G5_archived_native_legal_not_worse_than_parent":
        game_native["legal"]>=baseline_native["legal"],
      "G6_archived_native_teacher_match_not_worse_than_parent":
        game_native["teacher_matches"]>=baseline_native["teacher_matches"],
      "G7_language_previous_heldout_no_regression":
        lang_final["previous_20_heldout_nll"]<=previous_language["previous_20_heldout_nll"],
      "G8_language_fresh_probes_better_than_parent":
        lang_final["fresh_12_probe_nll"]<parent_language["fresh_12_probe_nll"],
      "G9_basic_language_retention_within_parent_10pct":
        lang_final["basic_retention_nll"]<=parent_language["basic_retention_nll"]*1.10,
      "G10_two_distinct_reloadable_branches_with_explicit_routes":
        game_sha_ck!=lang_sha_ck and route("dialogue")!=route("pocket"),
    }
    report={"schema":SCHEMA,"research_qbeast_id":E.ZEREF,
      "approved_parent_checkpoint_sha256":PARENT,"approved_parent_weights_unchanged":True,
      "training_executed":True,"language_continuation_updates":language_steps,
      "game_branch_updates_from_approved_parent":game_steps,
      "total_new_optimizer_updates":game_steps+language_steps,
      "model_weights_updated_in_isolated_branches":True,
      "route":{"version":"zeref-012d-explicit-task-router/v1","task_to_branch":ROLE_BRANCH,
               "untrusted_free_text_inference_disabled":True,
               "game_safe_move_guard":"OBSERVATION_RULES_CLASSICAL_NOT_NEURAL",
               "the_guard_is_applied_to_parent_and_game_branch":True},
      "new_heldout_layouts":keys,"game_training_source_sha256":game_sha,
      "native_source_sha256":native_sha,"authored_dialogue_manifest":lang_manifest,
      "language_parent_012c_shadow_sha256":old_report["shadow_checkpoint"],
      "saved_research_game_checkpoint":game_sha_ck,
      "saved_research_language_checkpoint":lang_sha_ck,
      "game_parameter_sha256_before":game_hash_before,"game_parameter_sha256_after":game_hash_after,
      "language_parameter_sha256_before":lang_before,"language_parameter_sha256_after":lang_after,
      "game_optimizer_trace":game_logs,"language_optimizer_trace":lang_logs,
      "heuristic_baselines":{k:v["mean"] for k,v in heuristic.items()},
      "approved_parent_raw_pocket":approved_raw["mean"],
      "approved_parent_guarded_pocket":approved_guarded["mean"],
      "trained_game_raw_pocket":game_raw["mean"],
      "trained_game_guarded_pocket":game_guarded["mean"],
      "game_legal_action_rate_raw":game_raw["legal_action_rate"],
      "game_legal_action_rate_guarded":game_guarded["legal_action_rate"],
      "game_guard_overrides":game_guarded["override_count"],
      "baseline_guard_overrides":approved_guarded["override_count"],
      "native_baseline":{k:v for k,v in baseline_native.items() if k!="replies"},
      "native_game_branch":{k:v for k,v in game_native.items() if k!="replies"},
      "language_frozen_approved_parent":parent_language,
      "language_original_012c_research":previous_language,
      "language_continued_branch":lang_final,
      "acceptance_gates":gates,"research_pilot_passed":all(gates.values()),
      "canonical_descendant_approved":False,"production_promoted":False,
      "model_live_guest_switch":False,"user_private_chat_data_used":False,
      "new_quantum_jobs":0,"verified_quantum_action_pairs":0,
      "claim_boundary":"Two routed model weight sets are NOT one multitask checkpoint; rule-based guard gains are not neural gains. One-seed research, not a production acceptance.",
      "limitations":["Historical IBM state is not causally paired to pocket actions.",
       "Language supervision is authored public synthetic dialogue, not conversations from guests.",
       "Heldout 20-prompt language set was used in 012C development; the new 12 prompts are fresh probes.",
       "The original native ROM controller corpus is historical and not a new play session.",
       "Only the explicit trusted task router may select a branch; no user-controlled model authority.",
       "Changes to perception-based safe-move guard are deterministic software, not pure model learning."]
    }
    (out/"report.json").write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("ZEREF_012D_RESULT="+json.dumps({
        "report_sha256":hash_file(out/"report.json"),"gates":gates,
        "game_raw":game_raw["mean"],"game_guarded":game_guarded["mean"],
        "heuristic":heuristic["pocket-learner"]["mean"],
        "language_old":previous_language["fresh_12_probe_nll"],
        "language_new":lang_final["fresh_12_probe_nll"],
        "accepted":False},sort_keys=True),flush=True)
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("parent","previous","game","native","out"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--game-steps",type=int,default=160)
    p.add_argument("--language-steps",type=int,default=64)
    p.add_argument("--eval-count",type=int,default=8)
    p.add_argument("--seed",type=int,default=12026)
    args=p.parse_args()
    experiment(args.parent,args.previous,args.game,args.native,args.out,
               game_steps=args.game_steps,language_steps=args.language_steps,
               eval_count=args.eval_count,seed=args.seed)
