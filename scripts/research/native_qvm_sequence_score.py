"""Preregistered SECONDARY proper multi-token native scoring, NOT initial numerical-test outcome."""
import argparse, hashlib, importlib.util, json, math, statistics, time
from pathlib import Path
import torch
from rawrphos.inference.engine import Engine

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--fixture",type=Path,required=True)
    p.add_argument("--first-report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    # Use the same exact upstream state computation exercised in the successful primary test.
    spec=importlib.util.spec_from_file_location("frozen_primary_native_qvm",Path(__file__).with_name("unified_qvm_native_benchmark.py"))
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    data=json.loads(args.fixture.read_text())
    first=json.loads(args.first_report.read_text())
    assert original.sha(data["scenario_records"])==data["public_rows_sha256"]==original.SOURCE_SHA
    assert first["model_sha256"]==original.WEIGHT_SHA and first["model_weights_unchanged"] is True
    assert first["source_digest"]==original.SOURCE_SHA and first["real_native_forward_passes"]==160
    rows=data["scenario_records"];assert len(rows)==8
    state=[]
    for row,primary in zip(rows,first["per_scenario_state"]):
        history=row["batches"][:2]
        actual,_=original.state_of(history)
        assert actual==primary["actual_dyn12"] and row["scenario"]==primary["scenario"]
        other_matched,_=original.state_of(history,matched=True)
        reversed_state,_=original.state_of(history[::-1])
        final_matched=original.matched_classical_control(actual)
        assert math.isclose(sum(a*a for a in actual),sum(b*b for b in final_matched),abs_tol=1e-12)
        state.append({"actual":actual,"matched":other_matched,"reversed":reversed_state,"final":final_matched})
    torch.set_num_threads(2)
    engine=Engine(args.checkpoint,threads=2,max_new_tokens=32,expected_sha256=original.WEIGHT_SHA)
    assert engine.metadata["checkpoint_sha256"]==original.WEIGHT_SHA
    model=engine.model;baseline=[p.detach().cpu().clone() for p in model.parameters()]
    prompt=original.PROMPTS[0]
    prompt_ids=engine.tokenizer.encode(prompt,add_bos=True)
    continuation={s:engine.tokenizer.encode(s,add_bos=False) for s in ("00","11")}
    assert len(continuation["00"])==1 and len(continuation["11"])==2
    options=("reference","actual","matched_input","final_norm_matched","reverse_time",
             "other_scenario","zero_gate","shuffled_state")
    scored=[]; started=time.perf_counter()
    try:
        with torch.inference_mode():
            prefix=torch.tensor([prompt_ids],dtype=torch.long)
            for index,item in enumerate(rows):
                v=state[index]
                arms={
                    "reference":(None,"dyn12"),
                    "actual":(v["actual"],"dyn12"),
                    "matched_input":(v["matched"],"dyn12"),
                    "final_norm_matched":(v["final"],"dyn12"),
                    "reverse_time":(v["reversed"],"dyn12"),
                    "other_scenario":(state[(index+3)%8]["actual"],"dyn12"),
                    "zero_gate":(v["actual"],"zero_gate"),
                    "shuffled_state":(v["actual"],"shuffled_state"),
                }
                for arm in options:
                    vec,mode=arms[arm]
                    model.config.attention_mode=mode
                    cv=None if vec is None else torch.tensor([vec],dtype=torch.float32)
                    first_logits=model(prefix,control_vector=cv)["logits"][0,-1,:].float().log_softmax(-1)
                    path00=float(first_logits[continuation["00"][0]])
                    path11=float(first_logits[continuation["11"][0]])
                    prefix11=torch.tensor([prompt_ids+[continuation["11"][0]]],dtype=torch.long)
                    second=model(prefix11,control_vector=cv)["logits"][0,-1,:].float().log_softmax(-1)
                    path11+=float(second[continuation["11"][1]])
                    score=math.exp(path11-max(path00,path11))/(math.exp(path00-max(path00,path11))+
                                                               math.exp(path11-max(path00,path11)))
                    assert math.isfinite(score) and 0<=score<=1
                    scored.append({"scenario":item["scenario"],"arm":arm,"forced_candidate00_logp":path00,
                                   "forced_candidate11_logp":path11,"exploratory_constrained_p11":score})
    finally:
        model.config.attention_mode="dyn12"
    assert all(torch.equal(x.detach().cpu(),y) for x,y in zip(model.parameters(),baseline))
    assert len(scored)==8*len(options)
    # Strict held-out boundary: only after the LAST model pass.
    future={r["scenario"]:r["batches"][2]["counts"]["11"]/128.0 for r in rows}
    private_ideal={r["scenario"]:math.sin(r["theta_rad"]/2)**2 for r in rows}
    jeffreys={r["scenario"]:(sum(b["counts"]["11"] for b in r["batches"][:2])+.5)/129 for r in rows}
    summary={}
    for arm in options:
        subset=[v for v in scored if v["arm"]==arm]
        assert len(subset)==8 and len(set(v["scenario"] for v in subset))==8
        summary[arm]={
            "future_empirical_MSE":round(statistics.mean((v["exploratory_constrained_p11"]-future[v["scenario"]])**2 for v in subset),10),
            "private_ideal_MAE":round(statistics.mean(abs(v["exploratory_constrained_p11"]-private_ideal[v["scenario"]]) for v in subset),10),
            "mean_constrained_p11":round(statistics.mean(v["exploratory_constrained_p11"] for v in subset),10)
        }
    paired={r["scenario"]:{v["arm"]:v["exploratory_constrained_p11"] for v in scored if v["scenario"]==r["scenario"]}
            for r in rows}
    result={
        "schema":"unified-real14k-original-cloud-qvm-secondary-multitoken-score-v1",
        "protocol":"docs/research/NATIVE14K_SECONDARY_SEQUENCE_SCORE_PROTOCOL.md",
        "original_primary_run":"36486840893","prior_original_primary_artifact":"10999592486",
        "original_source_sha256":original.SOURCE_SHA,"actual_model_sha256":original.WEIGHT_SHA,
        "native_token_lengths":{k:len(v) for k,v in continuation.items()},
        "scenarios":8,"real_native_forward_passes":len(scored)*2,
        "new_azure_jobs":0,"new_qpu_jobs":0,"owner_memory_accessed":False,"model_weights_unchanged":True,
        "no_future_access_until_after_all_model_passes":True,
        "arms":list(options),"by_arm":summary,"individual_scores":scored,"per_scenario_p11":paired,
        "classical_Jeffreys_future_empirical_MSE":round(statistics.mean((jeffreys[s]-future[s])**2 for s in future),10),
        "classical_Jeffreys_private_ideal_MAE":round(statistics.mean(abs(jeffreys[s]-private_ideal[s]) for s in future),10),
        "elapsed_seconds":round(time.perf_counter()-started,3),
        "claim_boundary":"CONSTRAINED_TEXT_CONTINUATION_NOT_CALIBRATED_PHYSICAL_PROBABILITY_OR_QUANTUM_ADVANTAGE"
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("NATIVE14K_SECONDARY_MULTITOKEN_SCORE_PASS",json.dumps({"by_arm":summary,
          "classical_Jeffreys_future_MSE":result["classical_Jeffreys_future_empirical_MSE"],
          "model_sha":original.WEIGHT_SHA,"scenarios":8},sort_keys=True))
if __name__=="__main__":main()
