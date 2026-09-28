"""Real pinned 14K native RAWRPHOS, ORIGINAL archived Azure QVM, 12D internal ablation.
Research only: no new cloud jobs, production, owner memory, weight updates or QPU measurements.
The future batch is sealed until all state vectors and model probes have been computed.
"""
import argparse, hashlib, json, math, statistics, time
from pathlib import Path
import torch
from beastbox.bridge import BridgePacket
from beastbox.cns import CNS
from beastbox.signal_fusion import fuse_sources, matched_classical_control, source_from_soul_token
from beastbox.soul.token import SoulToken
from beastbox.state import MissionState
from rawrphos.inference.engine import Engine

SOURCE_SHA="7ef23c00005a2053d1fc830985330f4db322b3bf6144fd79fd1561d14c425599"
WEIGHT_SHA="4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"
ARMS=("reference","zero","actual","matched_input","reverse_time","final_norm_matched",
      "other_scenario","zero_gate","frozen_state","shuffled_state")
PROMPTS=("user: Prior simulator measurements are encoded in the internal state. Predict 00 or 11.\nassistant:",
         "user: Describe what you learned from the observations.\nassistant:")
def sha(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def distance(a,b): return float(torch.linalg.vector_norm(a.float()-b.float()))
def state_of(history, matched=False):
    assert len(history)==2
    controller=CNS()
    mission=MissionState(mission_id="archived-QVM-isolated",objective="temporally ordered archived measurements")
    states=[]
    for batch in history:
        counts,shots=batch["counts"],batch["shots"]
        p=[counts[name]/shots for name in ("00","01","10","11")]
        h=-sum(x*math.log2(x) for x in p if x)/2
        token=SoulToken.from_qbt({
            "qbt_version":"archived-original-stage015-replay",
            "normalized_vector":p+[h],"execution_mode":"ARCHIVED_AZURE_QVM_SIMULATOR",
            "provider":"azure_quantum","backend":"rigetti.sim.qvm",
            "shots":shots,"result_digest":sha({"counts":counts,"shots":shots,
                                                  "source":"azure_cloud_qvm_simulator"}),
            "provenance":{"original_receipt":SOURCE_SHA,"job_id":batch["job_id"],"new_jobs":0}},
            source_type="SIMULATED_SHOT_COUNTS_NOT_PHYSICAL")
        source=source_from_soul_token(token,source_id="history-"+batch["phase"])
        drive=list(fuse_sources([source],mode="pure_quantum")["vector"])
        if matched: drive=matched_classical_control(drive)
        state=controller.tick(mission,BridgePacket(conditioning_vector=drive,
            conditioning_provenance={"original_receipt":SOURCE_SHA,
                                     "software_authority":"DATA_ONLY"}).safe_dict())["dyn12"]
        assert len(state)==12 and all(math.isfinite(v) and abs(v)<=1 for v in state)
        states.append(list(state))
    return states[-1],states
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fixture",required=True,type=Path)
    parser.add_argument("--checkpoint",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    raw=json.loads(args.fixture.read_text())
    rows=raw["scenario_records"]
    assert sha(rows)==raw["public_rows_sha256"]==SOURCE_SHA
    assert len(rows)==8 and raw["completed_provider_jobs"]==24
    assert raw["source_class"]=="NEW_AZURE_CLOUD_QVM_SIMULATION_NOT_QPU"
    seen=set(); computed=[]
    for r in rows:
        batches=r["batches"]
        assert [b["phase"] for b in batches]==["history_a","history_b","future_held_out"]
        assert [b["shots"] for b in batches]==[64,64,128]
        assert len({b["program_sha256"] for b in batches})==1
        for b in batches:
            assert b["target"]=="rigetti.sim.qvm"
            assert sum(b["counts"].values())==b["shots"] and b["counts"]["01"]==b["counts"]["10"]==0
            assert b["job_id"] not in seen
            seen.add(b["job_id"])
        # Strict two HISTORY batches; future is not read until post-probe scoring.
        past=batches[:2]
        actual,trace=state_of(past)
        matched,_=state_of(past,matched=True)
        reversed_state,_=state_of(past[::-1])
        permuted=matched_classical_control(actual)
        assert abs(sum(x*x for x in actual)-sum(x*x for x in permuted))<1e-12
        computed.append({"actual":actual,"matched":matched,"reversed":reversed_state,
                         "permuted":permuted,"trace":trace})
    assert len(seen)==24 and len({sha(c["actual"]) for c in computed})>1
    torch.set_num_threads(2)
    engine=Engine(args.checkpoint,threads=2,max_new_tokens=32,expected_sha256=WEIGHT_SHA)
    model=engine.model
    info=engine.info()
    assert info["checkpoint_sha256"]==WEIGHT_SHA and info["training_steps"]==14000
    assert model.config.state_dim==12 and model.config.attention_mode=="dyn12"
    before=[p.detach().cpu().clone() for p in model.parameters()]
    records=[]; start=time.perf_counter()
    token_choices={v:engine.tokenizer.encode(v,add_bos=False) for v in ("00","11")}
    try:
        with torch.inference_mode():
            for pnum,prompt in enumerate(PROMPTS):
                ids=engine.tokenizer.encode(prompt,add_bos=True)
                assert len(ids)>1 and len(ids)<128
                inp=torch.tensor([ids],dtype=torch.long)
                for index,r in enumerate(rows):
                    c=computed[index]
                    controls={
                        "reference":(None,"dyn12"),
                        "zero":([0.0]*12,"dyn12"),
                        "actual":(c["actual"],"dyn12"),
                        "matched_input":(c["matched"],"dyn12"),
                        "reverse_time":(c["reversed"],"dyn12"),
                        "final_norm_matched":(c["permuted"],"dyn12"),
                        "other_scenario":(computed[(index+3)%8]["actual"],"dyn12"),
                        "zero_gate":(c["actual"],"zero_gate"),
                        "frozen_state":(c["actual"],"frozen_state"),
                        "shuffled_state":(c["actual"],"shuffled_state"),
                    }
                    observed={}
                    for arm in ARMS:
                        vector,mode=controls[arm]
                        model.config.attention_mode=mode
                        cv=None if vector is None else torch.tensor([vector],dtype=torch.float32)
                        t0=time.perf_counter()
                        result=model(inp,control_vector=cv,return_attention=True)
                        logit=result["logits"][0,-1].float().clone()
                        attention=[x["attention"].float().clone() for x in result["telemetry"]]
                        telemetry=[{k:float(x[k]) for k in ("gate","sigma","state_norm","omega_mean")}
                                   for x in result["telemetry"]]
                        observed[arm]=(logit,attention,telemetry,(time.perf_counter()-t0)*1000)
                    base=observed["reference"]; real=observed["actual"]
                    for arm in ARMS:
                        logit,attention,telemetry,ms=observed[arm]
                        score=None
                        if all(len(token_choices[k])==1 for k in ("00","11")):
                            logits2=logit[[token_choices["00"][0],token_choices["11"][0]]]
                            score=float(torch.softmax(logits2,dim=-1)[1])
                        records.append({
                            "scenario":r["scenario"],"prompt_index":pnum,"arm":arm,
                            "logit_l2_vs_reference":distance(logit,base[0]),
                            "logit_l2_vs_actual":distance(logit,real[0]),
                            "attention_l2_vs_reference":statistics.mean(distance(a,b) for a,b in zip(attention,base[1])),
                            "attention_l2_vs_actual":statistics.mean(distance(a,b) for a,b in zip(attention,real[1])),
                            "state_norm":statistics.mean(x["state_norm"] for x in telemetry),
                            "gate_mean":statistics.mean(x["gate"] for x in telemetry),
                            "sigma_mean":statistics.mean(x["sigma"] for x in telemetry),
                            "omega_mean":statistics.mean(x["omega_mean"] for x in telemetry),
                            "elapsed_ms":ms,"two_token_forced_readout_P11":score,
                        })
    finally:
        model.config.attention_mode="dyn12"
    assert len(records)==8*len(PROMPTS)*len(ARMS)
    assert all(torch.equal(p.detach().cpu(),v) for p,v in zip(model.parameters(),before))
    assert all(math.isfinite(v) for r in records for v in r.values() if type(v) is float)
    by_arm={}
    for arm in ARMS:
        subset=[r for r in records if r["arm"]==arm]
        by_arm[arm]={key:round(statistics.mean(r[key] for r in subset),10)
                     for key in ("logit_l2_vs_reference","logit_l2_vs_actual",
                                 "attention_l2_vs_reference","attention_l2_vs_actual",
                                 "gate_mean","sigma_mean","state_norm","omega_mean","elapsed_ms")}
    assert by_arm["actual"]["logit_l2_vs_reference"]>1e-8
    assert by_arm["zero_gate"]["logit_l2_vs_actual"]>1e-8
    # All inference finished. Read held-out future ONLY for descriptive exploratory scoring.
    future={r["scenario"]:r["batches"][2]["counts"]["11"]/128 for r in rows}
    classical={}
    for r in rows:
        classical[r["scenario"]]=(sum(b["counts"]["11"] for b in r["batches"][:2])+.5)/129.0
    for arm in ARMS:
        selected=[r for r in records if r["arm"]==arm]
        if all(r["two_token_forced_readout_P11"] is not None for r in selected):
            by_arm[arm]["exploratory_unvalidated_binary_token_mse"]=round(statistics.mean(
                (r["two_token_forced_readout_P11"]-future[r["scenario"]])**2 for r in selected),10)
    report={
        "schema":"isolated-authentic-14k-archived-azure-qvm-neural-ablation-v1",
        "source_digest":SOURCE_SHA,"cloud_source":"24_ORIGINAL_AZURE_QVM_SIMULATOR_JOBS_NO_NEW_PROVIDER_JOBS",
        "new_azure_jobs":0,"new_qpu_jobs":0,"model_sha256":WEIGHT_SHA,"training_steps":14000,
        "parameter_count":info["parameter_count"],"real_native_forward_passes":len(records),
        "model_weights_unchanged":True,"owner_memory_accessed":False,
        "no_heldout_leak_in_model_input":True,"prompts":list(PROMPTS),"arms":list(ARMS),
        "token_candidate_lengths":{k:len(v) for k,v in token_choices.items()},
        "classical_Jeffreys_empirical_future_MSE":round(statistics.mean(
            (classical[s]-future[s])**2 for s in future),10),
        "per_scenario_state":[{"scenario":r["scenario"],"actual_dyn12":c["actual"],
              "last_tick_state_L2":math.dist(*c["trace"]),
              "reversed_history_state_L2":math.dist(c["actual"],c["reversed"]),
              "past_job_ids":[b["job_id"] for b in r["batches"][:2]]}
              for r,c in zip(rows,computed)],
        "by_arm":by_arm,"individual_forward_probes":records,
        "elapsed_s":round(time.perf_counter()-start,3),
        "limit":"Internal numerical responsiveness, not validated task benefit or physical quantum advantage"
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("ACTUAL_NATIVE14K_ARCHIVED_AZURE_QVM_PASS",json.dumps({
        "source":SOURCE_SHA,"model":WEIGHT_SHA,"forward_passes":len(records),
        "mean_actual_logit_L2":by_arm["actual"]["logit_l2_vs_reference"],
        "mean_zero_gate_logit_L2":by_arm["zero_gate"]["logit_l2_vs_actual"],
        "classical_MSE":report["classical_Jeffreys_empirical_future_MSE"]}))
if __name__=="__main__":main()
