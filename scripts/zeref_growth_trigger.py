#!/usr/bin/env python3
"""Capacity-saturation trigger for bb-deada969 repeatable growth (never a gate input).

Reads the last N completed zeref-continuous-learning-006 runs and fires when ALL of them were
rejected AND their best in-cycle chat NLL plateaued (spread < PLATEAU_SPREAD and no run within
the unchanged pin bar). Output: {"grow": bool, "add_layers": k, ...} to stdout / $GITHUB_OUTPUT.
Growth is function-preserving (rawrphos.architecture.model.grow_depth); the grown candidate
still has to pass the SAME promotion gate. A cap on total size keeps CPU runners feasible."""
import json,os,re,subprocess,sys
N=int(os.environ.get("ZEREF_GROW_PLATEAU_CYCLES","6"))
SPREAD=float(os.environ.get("ZEREF_GROW_PLATEAU_SPREAD","0.05"))
MAX_LAYERS=int(os.environ.get("ZEREF_GROW_MAX_LAYERS","16"))  # CPU runner budget (7 GB RAM, 2-4 vCPU)
ADD=int(os.environ.get("ZEREF_GROW_ADD_LAYERS","2"))
def runs(repo):
 out=subprocess.run(["gh","run","list","--repo",repo,"-w","zeref-continuous-learning-006.yml","-L","40",
  "--json","databaseId,conclusion,event"],capture_output=True,text=True,check=True).stdout
 return [r["databaseId"] for r in json.loads(out) if r["conclusion"]=="success" and r["event"]!="pull_request"][:N]
def summary(repo,rid):
 log=subprocess.run(["gh","run","view",str(rid),"--repo",repo,"--log"],capture_output=True,text=True).stdout
 nll=[float(x) for x in re.findall(r'ZEREF_006_INCYCLE_CHAT=\{[^}]*"chat_nll": ([0-9.]+)',log)]
 gate=re.findall(r'ZEREF_006_REAL_TRAINING_GATE=\{"approved": (true|false)',log)
 return {"run":rid,"best_chat_nll":min(nll) if nll else None,"approved":(gate[-1]=="true") if gate else None}
def decide(hist,bar,layers):
 vals=[h["best_chat_nll"] for h in hist if h["best_chat_nll"] is not None]
 full=len(hist)>=N and len(vals)==len(hist) and all(h["approved"] is False for h in hist)
 plateau=full and max(vals)-min(vals)<SPREAD and min(vals)>bar
 room=layers+ADD<=MAX_LAYERS
 return {"schema":"zeref-growth-trigger-v1","grow":bool(plateau and room),"add_layers":ADD if plateau and room else 0,
  "plateau":bool(plateau),"capacity_room":room,"cycles":hist,"pin_bar":bar,"spread_limit":SPREAD,"max_layers":MAX_LAYERS}
if __name__=="__main__":
 repo=os.environ.get("GITHUB_REPOSITORY","NavisWORLD/The-beast-box-")
 pin=json.load(open("apps/beastbox-cloud/lib/rawrphos-public-pin.json"))
 bar=pin["promotion"]["candidate_ref_nll"]*1.005; layers=int(sys.argv[1]) if len(sys.argv)>1 else 6
 try:d=decide([summary(repo,r) for r in runs(repo)],bar,layers)
 except Exception as e:d={"schema":"zeref-growth-trigger-v1","grow":False,"add_layers":0,"error":type(e).__name__}
 print("ZEREF_GROWTH_TRIGGER="+json.dumps(d),flush=True)
 if os.environ.get("GITHUB_OUTPUT"):open(os.environ["GITHUB_OUTPUT"],"a").write(f"add_layers={d['add_layers']}\n")
