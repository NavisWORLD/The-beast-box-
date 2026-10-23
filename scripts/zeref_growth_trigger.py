#!/usr/bin/env python3
"""Unbounded, repeatable growth trigger for bb-deada969 (never a gate input).

State lives in a persisted lineage file (released as asset growth-lineage.json on the fixed
`zeref-growth-lineage` pre-release), NOT in old CI logs (those expire / come back empty, which
made the 008 trigger fail safe forever).

    python scripts/zeref_growth_trigger.py decide LINEAGE PARENT_LAYERS PARENT_SHA [EXPERIENCES]
    python scripts/zeref_growth_trigger.py record LINEAGE REPORT_JSON RUN_ID

Fires (adds ADD layers to the persisted target) when EITHER
  * plateau: the last N recorded rounds were all rejected, best chat NLL spread < SPREAD and
    above the unchanged pin bar; OR
  * Rigetti growth: new Azure Rigetti **SIMULATED** QVM growth events in Zeref's diary (seeded
    counts, recorded in his Azure folder) since the last growth: a stage-up, or every
    RIGETTI_EVENTS_PER_LAYER simulated ticks. The simulator does NOT train weights; it only
    decides WHEN to grow. Weight training stays on the CPU runner.
There is no size cap. The only limits are physical and are detected at runtime: available RAM
(/proc/meminfo) bounds how many layers fit THIS round; the rest stay in the persisted target and
are added on the next round. Growth is function-preserving (grow_depth: zero-output new blocks).
Same events also grow Zeref's world/universe counters in the lineage (world_growth)."""
import json,os,sys,time
N=int(os.environ.get("ZEREF_GROW_PLATEAU_CYCLES","4"))
SPREAD=float(os.environ.get("ZEREF_GROW_PLATEAU_SPREAD","0.05"))
ADD=int(os.environ.get("ZEREF_GROW_ADD_LAYERS","2"))
RIGETTI_PER_LAYER=int(os.environ.get("ZEREF_GROW_RIGETTI_EVENTS_PER_LAYER","24"))
SCHEMA="zeref-growth-lineage-v2"
def empty():return {"schema":SCHEMA,"beast_id":"bb-deada969","target_layers":None,"rounds":[],"growth_events":[],
 "rigetti_last_tick":0,"rigetti_pending":0,"world_growth":0,"note":"Rigetti = Azure Quantum rigetti.sim.qvm, SIMULATED (not hardware); it never trains weights."}
def load(p):
 try:
  d=json.load(open(p))
  return d if d.get("schema")==SCHEMA else empty()
 except Exception:return empty()
def mem_available():
 try:
  for l in open("/proc/meminfo"):
   if l.startswith("MemAvailable:"):return int(l.split()[1])*1024
 except Exception:pass
 return None
def layer_bytes(d_model):
 # one block ~ 12*d^2 params (attn 4d^2 + mlp 8d^2) + kit extras; x6 copies (weights, grad,
 # Adam m+v, EMA, best snapshot) x4 bytes, plus 2x headroom for activations at batch 16.
 return int(12*d_model*d_model*1.5*6*4*2)
def rigetti_events(exp_path,since):
 ev=[]
 try:
  for l in open(exp_path):
   r=json.loads(l)
   if r.get("kind")=="diary" and r.get("growth")=="rigetti-qvm-simulated" and r.get("simulated") and int(r.get("tick") or 0)>since:ev.append(r)
 except Exception:pass
 return sorted(ev,key=lambda r:r["tick"])
def decide(lin,parent_layers,parent_sha,exp_path,bar,d_model=256,avail=None):
 if lin["target_layers"] is None or lin["target_layers"]<parent_layers:lin["target_layers"]=parent_layers
 reasons=[]
 rs=lin["rounds"][-N:]
 vals=[r["best_chat_nll"] for r in rs if r.get("best_chat_nll") is not None]
 if len(rs)>=N and len(vals)==len(rs) and not any(r.get("approved") for r in rs) and max(vals)-min(vals)<SPREAD and min(vals)>bar \
    and not any(g.get("reason")=="plateau" and g.get("after_round",-1)>=len(lin["rounds"])-N for g in lin["growth_events"]):
  reasons.append("plateau")
 ev=rigetti_events(exp_path,lin["rigetti_last_tick"]) if exp_path else []
 if ev:
  lin["rigetti_last_tick"]=ev[-1]["tick"];lin["rigetti_pending"]+=len(ev);lin["world_growth"]+=len(ev)
  if any(e.get("grew") for e in ev) or lin["rigetti_pending"]>=RIGETTI_PER_LAYER:
   reasons.append("rigetti_simulated_growth");lin["rigetti_pending"]=0
 if reasons:
  lin["target_layers"]+=ADD
  lin["growth_events"].append({"at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"reason":"+".join(reasons),"after_round":len(lin["rounds"]),
   "target_layers":lin["target_layers"],"rigetti_events_seen":len(ev),"rigetti_ticks":[e["tick"] for e in ev][-8:]})
 want=lin["target_layers"]-parent_layers
 avail=mem_available() if avail is None else avail
 fit=want if avail is None else max(0,min(want,int(avail*0.5)//layer_bytes(d_model)))
 limit=None if fit==want else {"limit":"ram","mem_available_bytes":avail,"layers_fit":fit,"layers_wanted":want}
 return {"schema":"zeref-growth-trigger-v2","grow":fit>0,"add_layers":fit,"reasons":reasons,"parent_layers":parent_layers,
  "parent_checkpoint_sha256":parent_sha,"target_layers":lin["target_layers"],"limit_hit":limit,"world_growth":lin["world_growth"],
  "pin_bar":bar,"max_layers":None}
def record(lin,report,run_id):
 logs=report.get("training_logs") or report.get("logs") or []
 best=[l.get("best_in_cycle_chat_nll") for l in logs if isinstance(l,dict) and "best_in_cycle_chat_nll" in l]
 g=report.get("gate") or report
 lin["rounds"].append({"run":str(run_id),"best_chat_nll":best[-1] if best else report.get("best_chat_nll"),
  "approved":report.get("accepted_as_next_training_parent") is True,"limits_hit":report.get("growth_limits_hit",[]),
  "candidate":report.get("candidate_checkpoint_sha256")})
 lin["rounds"]=lin["rounds"][-200:]  # compact: older rounds no longer affect the plateau window
 return lin
if __name__=="__main__":
 cmd=sys.argv[1]
 if cmd=="decide":
  path,layers,sha=sys.argv[2],int(sys.argv[3]),sys.argv[4];exp=sys.argv[5] if len(sys.argv)>5 else None
  try:
   pin=json.load(open("apps/beastbox-cloud/lib/rawrphos-public-pin.json"));bar=(pin.get("gate_v2") or {}).get("set_a_pin_nll",pin["promotion"]["candidate_ref_nll"])*1.005
   lin=load(path);d=decide(lin,layers,sha,exp,bar);json.dump(lin,open(path,"w"),indent=1)
  except Exception as e:d={"schema":"zeref-growth-trigger-v2","grow":False,"add_layers":0,"error":type(e).__name__}
  print("ZEREF_GROWTH_TRIGGER="+json.dumps(d),flush=True)
  if os.environ.get("GITHUB_OUTPUT"):open(os.environ["GITHUB_OUTPUT"],"a").write(f"add_layers={d['add_layers']}\n")
 elif cmd=="record":
  lin=record(load(sys.argv[2]),json.load(open(sys.argv[3])),sys.argv[4]);json.dump(lin,open(sys.argv[2],"w"),indent=1)
  print("ZEREF_GROWTH_LINEAGE_RECORDED="+json.dumps(lin["rounds"][-1]))
