#!/usr/bin/env python3
"""ZEREF 012C: real CPU mixed GAME + LANGUAGE neural-weight training (research only).

Resumes only the independently approved 006 cycle-3 parent. Compares game-only,
joint game+dialogue, and joint with shuffled game targets. All arms receive
equal update/batch budgets, original native-controller rehearsal, and true
heldout tests. No weights are silently deployed or made canonical. No quantum
measurements are misrepresented as game/action supervision.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

import torch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zeref_experiment_011 as E
import zeref_experience_bridge as B
import zeref_012c_joint_dialogue as D
from rawrphos.training.checkpoint import (parameter_hash, save_checkpoint,
                                           load_checkpoint, rng_state, hash_file)

ZEREF = E.ZEREF
APPROVED_PARENT = E.PARENT_SHA
GAME_SCHEMA = "zeref-012b-pocket-action-candidate/v1"
GAME_MANIFEST = "zeref-012b-game-measurement-alignment/v1"
ARM_NAMES = ("game_only", "game_language", "game_language_shuffled_game")
EXPERIMENT = "zeref-012c-joint-game-dialogue/v1"
ACCEPTED_TO_PRODUCTION = False

def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verified_game(game_dir: Path):
    manifest_bytes = (game_dir / "manifest.json").read_bytes()
    metadata = json.loads(manifest_bytes)
    data = (game_dir / "pocket-outcome-selected-train.jsonl").read_bytes()
    key = "pocket-outcome-selected-train.jsonl"
    expected = metadata["outputs"][key]
    if (metadata.get("schema") != GAME_MANIFEST or
        metadata.get("qbeast_id") != ZEREF or
        metadata.get("verified_quantum_game_training_pairs") != 0 or
        metadata.get("model_weights_updated") is not False or
        metadata.get("user_private_data_used") is not False or
        metadata.get("simulation_origin") != "deterministic_pocket_simulation" or
        metadata.get("real_native_game_progress_claimed") is not False or
        metadata.get("training", {}).get("layouts") != 32 or
        metadata.get("evaluation", {}).get("layouts") != 24 or
        metadata["training"].get("record_count") != 3840 or
        expected["sha256"] != sha(data) or expected["bytes"] != len(data)):
        raise ValueError("Unverified 012B game source or false quantum/game claim")
    rows = [json.loads(line) for line in data.splitlines() if line.strip()]
    if len(rows) != 2254 or len(rows) != metadata["training"]["outcome_selected_action_candidates"]:
        raise ValueError("012B observed positive-action census changed")
    seen_hash = set()
    for r in rows:
        obs = r.get("observation")
        if (r.get("schema") != GAME_SCHEMA or
            r.get("qbeast_id") != ZEREF or
            r.get("origin") != "deterministic_pocket_simulation" or
            r.get("source_policy") not in ("random", "pocket-learner", "greedy-frontier") or
            r.get("label_kind") != "computed_reward" or
            r.get("label") not in B.POCKET_KEYS[:4] or
            not isinstance(obs, dict) or set(obs.get("neighbors", {})) != set(B.POCKET_KEYS[:4]) or
            not r.get("source_episode", "").startswith("exp012b-train-") or
            r.get("measurement_source") is not None or
            r.get("quantum_action_pair_verified") is not False or
            r.get("real_native_game_progress") is not False or
            float(r.get("observed_reward", 0)) <= .5 or
            not isinstance(r.get("hash_chain_record"), str) or len(r["hash_chain_record"]) != 64):
            raise ValueError("Game row cannot be used as a valid observed simulation target")
        if r["hash_chain_record"] in seen_hash:
            raise ValueError("Identical source action repeated in training")
        seen_hash.add(r["hash_chain_record"])
    return rows, sha(data), sha(manifest_bytes), metadata


def verified_native(native_dir: Path):
    manifest_bytes = (native_dir / "native-evidence-manifest.json").read_bytes()
    m = json.loads(manifest_bytes)
    data = (native_dir / "native-observation-actions.jsonl").read_bytes()
    if (m.get("schema") != "beastbox-observed-native-play-v1" or
        m.get("source_class") != "ORIGINAL_EMULATOR_NATIVE_PIXEL_OBSERVATIONS" or
        m.get("qbeast_id") != ZEREF or m.get("events") != 56 or
        m.get("jsonl_sha256") != sha(data) or
        m.get("dataset_has_human_labels") is not False or
        m.get("goal_reward_observed") is not False):
        raise ValueError("Invalid original emulator observation evidence")
    rows = [json.loads(line) for line in data.splitlines() if line.strip()]
    if len(rows) != 56 or {r["episode"] for r in rows} != {0,1,2,3}:
        raise ValueError("Invalid native episode allocation")
    for r in rows:
        if (r.get("qbeast_id") != ZEREF or
            r.get("teacher") != "OBSERVATION_CONDITIONED_SCRIPTED_HEURISTIC_NOT_HUMAN_NOT_MODEL" or
            r.get("reward_is_not_native_progress") is not True or
            r.get("action") not in B.NATIVE_KEYS or
            len(r.get("native_ack_digest", "")) != 64):
            raise ValueError("Native row falsely labeled or incompatible")
    records = B.native_rows_to_records(rows,m,ZEREF)
    audit = B.verify_stream(records)
    if not audit["ok"]:
        raise ValueError("Native canonical hash-chain failed")
    train = B.native_examples(records,ZEREF,{0,1,2})
    held = B.native_examples(records,ZEREF,{3})
    if len(train)!=42 or len(held)!=14:
        raise ValueError("Native train/heldout count changed")
    return train,held,sha(data),sha(manifest_bytes)


def dialogue_rows():
    train, held = D.corpus()
    for r in train+held:
        if (r["schema"]!=D.SCHEMA or r["source_class"]!=D.PROVENANCE or
            r["raw_user_conversation"] is not False or
            r["private_scope"] is not False):
            raise ValueError("Non-public or unverified dialogue source")
    if len(train)!=60 or len(held)!=20 or {r["user"] for r in train}&{r["user"] for r in held}:
        raise ValueError("Dialogue train/eval contamination")
    return train,held,D.manifest()


def talk_tokens(tok, rows):
    return [E.tokens(tok,"User: "+r["user"]+"\nAssistant: ",r["answer"])
            for r in rows]


def game_tokens(tok,rows,shuffled=False,seed=0):
    targets=[r["label"] for r in rows]
    if shuffled:
        random.Random(seed+117).shuffle(targets)
        if targets==[r["label"] for r in rows]:
            raise ValueError("Shuffled game targets unexpectedly identical")
    return [E.tokens(tok,B.pocket_prompt(r["observation"]), "ACTION: "+target)
            for r,target in zip(rows,targets)]


def eval_text(model,tok,rows):
    # Report exact model utterances (not a claim of semantic correctness).
    samples=[]
    for r in rows:
        if len(samples)>=8:break
        prompt="User: "+r["user"]+"\nAssistant: "
        samples.append({"id":r["id"],"prompt":r["user"],
                        "reply":E.reply(model,tok,prompt,max_new=25),
                        "reference_for_nll_only":r["answer"]})
    return samples


def evaluate_model(model,tok,talk_held,native_held,pocket_keys,policy_name):
    talk_score=round(E.nll(model,talk_tokens(tok,talk_held)),6)
    retention=round(E.retention_nll(model,tok),6)
    native=E.native_eval(model,tok,native_held)
    pocket=E.Pocket()
    try:
        exploration=E.run_policy(pocket,pocket_keys,40,policy_name,model=model,tok=tok)
    finally:
        pocket.close()
    return {"language_heldout_nll":talk_score,
            "language_basic_retention_nll":retention,
            "native":{k:v for k,v in native.items() if k!="replies"},
            "pocket":{k:v for k,v in exploration.items() if k not in ("per_episode",)},
            "language_samples":eval_text(model,tok,talk_held),
            "native_replies":native["replies"]}


def train_arm(parent_dir,game,language,native,arm,updates,seed,lr,threads):
    torch.manual_seed(seed);random.seed(seed)
    package=E.load_parent(parent_dir)
    model,tok=package["model"],package["tokenizer"]
    initial=parameter_hash(model)
    if initial!=package["metadata"]["parameter_sha256"]:
        raise ValueError("Approved parent params changed")
    if arm not in ARM_NAMES:
        raise ValueError("Unknown arm")
    game_data=game_tokens(tok,game,shuffled=(arm=="game_language_shuffled_game"),seed=seed)
    talk_data=talk_tokens(tok,language)
    native_data=[E.tokens(tok,r["prompt"],r["target"]) for r in native]
    optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=.01)
    optimizer.load_state_dict(package["state"]["optimizer"])
    for group in optimizer.param_groups:group["lr"]=lr
    if not all("exp_avg" in m and "exp_avg_sq" in m for m in optimizer.state.values()):
        raise ValueError("Missing saved AdamW moments; refused to restart")
    generator=torch.Generator().manual_seed(seed)
    loss_logs=[]
    for i in range(updates):
        optimizer.zero_grad(set_to_none=True)
        game_count=7 if arm=="game_only" else 3
        n_game=torch.randint(len(game_data),(game_count,),generator=generator).tolist()
        examples=[game_data[k] for k in n_game]
        if arm!="game_only":
            picks=torch.randint(len(talk_data),(4,),generator=generator).tolist()
            examples.extend(talk_data[k] for k in picks)
        nat_id=int(torch.randint(len(native_data),(1,),generator=generator).item())
        examples.append(native_data[nat_id])
        if len(examples)!=8:
            raise AssertionError("Mismatched optimizer batch budget")
        x,y,mask=E.collate(examples)
        loss=model(x,targets=y,attention_mask=mask)["loss"]
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError("Nonfinite joint loss")
        loss.backward()
        g=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
        if not bool(torch.isfinite(g)):
            raise FloatingPointError("Nonfinite gradient")
        optimizer.step()
        if (i+1)%32==0 or i==0:
            row={"arm":arm,"step":i+1,"loss":round(float(loss.detach()),6),
                 "gradient_norm":round(float(g),6)}
            loss_logs.append(row)
            print("ZEREF_012C_TRAIN_STEP="+json.dumps(row,sort_keys=True),flush=True)
    trained=parameter_hash(model)
    if trained==initial:
        raise AssertionError("No real neural model parameter updates happened")
    return package,model,tok,optimizer,generator,initial,trained,loss_logs


def experiment(parent_dir,game_dir,native_dir,out,*,updates=160,lr=1e-5,
               seed=20261012,threads=3,eval_layouts=8):
    if updates<1 or updates>384 or eval_layouts<2 or eval_layouts>24 or not(1e-7<=lr<=5e-5) or not(1<=threads<=8):
        raise ValueError("Experiment resource bound")
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(seed);random.seed(seed)
    game,game_sha,game_manifest_sha,game_manifest=verified_game(game_dir)
    native_train,native_held,native_sha,native_manifest_sha=verified_native(native_dir)
    talk_train,talk_held,talk_manifest=dialogue_rows()
    parent=E.load_parent(parent_dir)
    pm,pt=parent["model"],parent["tokenizer"]
    approved_parameter_hash=parameter_hash(pm)
    parent_lang_score=E.nll(pm,talk_tokens(pt,talk_held))
    parent_retention=E.retention_nll(pm,pt)
    eval_keys=[f"exp012b-eval-{i}" for i in range(eval_layouts)]
    if any(x in {r["source_episode"] for r in game} for x in eval_keys):
        raise ValueError("Training and heldout pocket layouts overlap")
    pocket=E.Pocket()
    try:
        heuristics={name:E.run_policy(pocket,eval_keys,40,name)
                    for name in ("random","pocket-learner","greedy-frontier")}
    finally:
        pocket.close()
    print("ZEREF_012C_BASELINE="+json.dumps({"language_nll":parent_lang_score,
          "basic_retention":parent_retention,"pocket_learner":heuristics["pocket-learner"]["mean"]}),flush=True)
    baseline=evaluate_model(pm,pt,talk_held,native_held,eval_keys,"012c-approved-parent")
    assert baseline["language_heldout_nll"]==round(parent_lang_score,6)
    del pm,parent
    out.mkdir(parents=True,exist_ok=False)
    metrics={}
    shadow_sha=None
    for arm in ARM_NAMES:
        package,model,tok,opt,gen,start_hash,end_hash,logs=train_arm(
            parent_dir,game,talk_train,native_train,arm,updates,seed,lr,threads)
        score=evaluate_model(model,tok,talk_held,native_held,eval_keys,"012c-"+arm)
        metrics[arm]={"parent_parameter_sha256":start_hash,
                      "trained_parameter_sha256":end_hash,"optimizer_updates":updates,
                      "supervision_mix":{"game":7 if arm=="game_only" else 3,
                         "language":0 if arm=="game_only" else 4,"native":1},
                      "shuffled_game_targets":arm=="game_language_shuffled_game",
                      "steps":logs,"evaluation":score}
        if arm=="game_language":
            meta={"schema":"zeref-012c-joint-language-game-shadow/v1",
                  "qbeast_id":ZEREF,"parent_checkpoint_sha256":APPROVED_PARENT,
                  "training_steps":package["metadata"]["training_steps"]+updates,
                  "research_only":True,"production_promoted":False,
                  "canonical_training_parent_eligible":False,
                  "quantum_action_pairs":0,"public_synthetic_dialogue_only":True,
                  "source_game_sha256":game_sha,"source_native_sha256":native_sha,
                  "source_dialogue_train_sha256":talk_manifest["train_sha256"]}
            saved=save_checkpoint(out/"shadow-joint-checkpoint",model,tok,meta,
                                  {"optimizer":opt.state_dict(),"rng":rng_state(),
                                   "data_rng":gen.get_state()})
            shadow_sha=saved["checkpoint_sha256"]
            reloaded=load_checkpoint(out/"shadow-joint-checkpoint",
                                     expected_checkpoint_sha256=shadow_sha,
                                     load_training_state=True)
            if parameter_hash(reloaded["model"])!=end_hash:
                raise AssertionError("Saved/reloaded research checkpoint mismatch")
        del model,package,opt
    reloaded_parent=E.load_parent(parent_dir)
    if parameter_hash(reloaded_parent["model"])!=approved_parameter_hash:
        raise AssertionError("Canonical approved parent was changed")
    mixed=metrics["game_language"]["evaluation"]
    gameonly=metrics["game_only"]["evaluation"]
    scrambled=metrics["game_language_shuffled_game"]["evaluation"]
    learner=heuristics["pocket-learner"]
    # PREREGISTERED strict gates (not determined from heldout outcomes).
    gates={
      "G1_language_heldout_no_regression_vs_parent":
         mixed["language_heldout_nll"]<=baseline["language_heldout_nll"],
      "G2_language_heldout_better_than_game_only":
         mixed["language_heldout_nll"]<gameonly["language_heldout_nll"],
      "G3_basic_chat_retention_within_10pct":
         mixed["language_basic_retention_nll"]<=baseline["language_basic_retention_nll"]*1.10,
      "G4_game_coverage_exceeds_parent":
         mixed["pocket"]["mean"]["cells_visited"]>baseline["pocket"]["mean"]["cells_visited"],
      "G5_game_coverage_beats_pocket_learner":
         mixed["pocket"]["mean"]["cells_visited"]>learner["mean"]["cells_visited"],
      "G6_blocked_not_worse_than_pocket_learner":
         mixed["pocket"]["mean"]["blocked"]<=learner["mean"]["blocked"],
      "G7_native_legal_commands_not_worse_than_parent":
         mixed["native"]["legal"]>=baseline["native"]["legal"],
      "G8_native_teacher_matches_not_worse_than_parent":
         mixed["native"]["teacher_matches"]>=baseline["native"]["teacher_matches"],
      "G9_native_heldout_nll_within_5pct":
         mixed["native"]["nll"]<=max(.01,baseline["native"]["nll"]*1.05),
      "G10_game_score_beats_shuffled_target_control":
         mixed["pocket"]["mean"]["cells_visited"]>scrambled["pocket"]["mean"]["cells_visited"],
    }
    allpass=all(gates.values())
    report={"schema":EXPERIMENT,"mode":"REAL_CPU_FULL_PARAMETER_JOINT_OPTIMIZATION",
      "research_qbeast_id":ZEREF,"canonical_parent_checkpoint_sha256":APPROVED_PARENT,
      "canonical_parent_parameter_sha256":approved_parameter_hash,
      "parent_unchanged":True,"training_performed":True,
      "full_model_neural_weights_updated_in_shadow":True,
      "production_promoted":False,"training_parent_promoted":False,
      "shadow_checkpoint":shadow_sha,"seed":seed,"lr":lr,"updates_per_arm":updates,
      "optimizer_arms":list(ARM_NAMES),"same_optimizer_budget":True,
      "game_source":{"sha256":game_sha,"manifest_sha256":game_manifest_sha,
                     "count":len(game),"origin":"deterministic_pocket_simulation"},
      "native_source":{"sha256":native_sha,"manifest_sha256":native_manifest_sha,
        "train_count":len(native_train),"heldout_count":len(native_held),
        "source":"REPLAY_011_ORIGINAL_NATIVE_EMULATOR_FRAMES_NOT_NEW_CAPTURE"},
      "dialogue_source":talk_manifest,
      "language_training_examples":len(talk_train),
      "language_heldout_examples":len(talk_held),
      "evidence_quantum_action_pairs":0,"new_ibm_hardware_jobs":0,"new_rigetti_jobs":0,
      "private_user_chats_used":False,"guest_personal_state_used":False,
      "measured_quantum_advantage_claimed":False,"real_native_game_objectives_claimed":False,
      "heldout_layouts":eval_keys,
      "heuristic_baselines":{k:v["mean"] for k,v in heuristics.items()},
      "approved_parent_evaluation":baseline,
      "arms":metrics,
      "acceptance_gates":gates,
      "passes_this_bounded_pilot":allpass,
      "approved_as_next_canonical_parent":False,
      "claim_boundary":"Even all gates passing on only 8 layouts and one seed would require independent full-sized replication.",
      "limitations":["Language references are authored examples, not conversations from visitors.",
        "Native evidence is archived real emulator observations with a scripted teacher, not earned game objectives.",
        "Action labels originate from classical pocket simulation and do not establish quantum-game causality.",
        "A lower heldout NLL does not by itself demonstrate fluent multi-turn conversation.",
        "All saved weights are isolated research shadow output; unchanged parent remains approved."]
    }
    (out/"report.json").write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print("ZEREF_012C_FINAL="+json.dumps({"sha256":hash_file(out/"report.json"),
      "gates":gates,"allpass":allpass,
      "parent":{"game":baseline["pocket"]["mean"],"language":baseline["language_heldout_nll"]},
      "arms":{k:{"game":v["evaluation"]["pocket"]["mean"],
                 "language":v["evaluation"]["language_heldout_nll"],
                 "retention":v["evaluation"]["language_basic_retention_nll"]}
                for k,v in metrics.items()}},sort_keys=True),flush=True)
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--parent",type=Path,required=True)
    ap.add_argument("--game",type=Path,required=True)
    ap.add_argument("--native",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=Path("build/zeref-012c-training"))
    ap.add_argument("--updates",type=int,default=160)
    ap.add_argument("--lr",type=float,default=1e-5)
    ap.add_argument("--seed",type=int,default=20261012)
    ap.add_argument("--threads",type=int,default=3)
    ap.add_argument("--eval-layouts",type=int,default=8)
    a=ap.parse_args()
    experiment(a.parent,a.game,a.native,a.out,updates=a.updates,lr=a.lr,
               seed=a.seed,threads=a.threads,eval_layouts=a.eval_layouts)

if __name__=="__main__":
    main()
