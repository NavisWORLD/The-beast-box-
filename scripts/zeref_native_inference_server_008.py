#!/usr/bin/env python3
"""Local-only isolated original vs candidate RAWRPHOS inference for live ROM trial.
Checkpoint has no authority to mutate creature, SRAM, production or local user files.
"""
from __future__ import annotations
import hashlib,json,os,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from rawrphos.inference.engine import Engine
from rawrphos.training.checkpoint import load_checkpoint

ORIGINAL_SHA="4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5"
CANDIDATE_SHA="37ca3f8fc9cdc0e78175508fc816ed02d5a12da1f3b106505715b7366fde5a48"
BASE=Path("build/verified-rawrphos-14k")
CAND=Path(os.environ.get("BEAST_008_CANDIDATE_PATH","build/zeref-008-model/candidate-actual-native-frame-imitation-001"))
CHECKPOINTS={"original":(BASE,ORIGINAL_SHA),"candidate":(CAND,CANDIDATE_SHA)}
ENGINES={}
LOCK=threading.Lock()
def load():
 for kind,(path,expected) in CHECKPOINTS.items():
  if not path.is_dir():raise FileNotFoundError("Required pinned model not available: "+kind)
  check=load_checkpoint(path,expected_checkpoint_sha256=expected,load_training_state=False)
  if check["metadata"]["checkpoint_sha256"]!=expected:raise ValueError("Unexpected candidate lineage: "+kind)
  del check
  model=Engine(path,max_new_tokens=12,threads=2,expected_sha256=expected)
  if model.info()["checkpoint_sha256"]!=expected:raise RuntimeError("Engine did not load immutable SHA")
  ENGINES[kind]=model
  print("PINNED_RAWRPHOS_008_READY="+json.dumps({"model":kind,"checkpoint":expected}),flush=True)

def prompt(o):
 return (f"User: Native screen numerical signals: brightness {o['brightness']}/100, "
   f"contrast {o['contrast']}/100, dominant {o['dominant']}, "
   f"frame-change {o['frameChange']}/100. Propose one cautious game key. "
   "Reply exactly ACTION: UP, DOWN, LEFT, RIGHT, A, B, or WAIT. "
   "No object recognition.\nAssistant: ")
def check(o):
 return isinstance(o,dict) and o.get("status")=="observed" and o.get("source")=="native-emulator-display" and (
  o.get("dominant") in ("red","green","blue","mixed")) and all(type(o.get(k)) is int and 0<=o[k]<=100 for k in ("brightness","contrast","frameChange"))
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def respond(self,status,data):
  raw=(json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
  self.send_response(status);self.send_header("Content-Type","application/json");
  self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  if self.path!="/health":return self.respond(404,{"error":"unknown route"})
  self.respond(200,{"ready":len(ENGINES)==2,"models":{k:v.info()["checkpoint_sha256"] for k,v in ENGINES.items()}})
 def do_POST(self):
  if self.path!="/infer":return self.respond(404,{"error":"unknown route"})
  try:
   n=int(self.headers.get("Content-Length","0"))
   if n<=0 or n>4096:raise ValueError("Oversized inference request")
   r=json.loads(self.rfile.read(n))
   model=r.get("model");o=r.get("observation");step=r.get("step")
   if model not in ENGINES or r.get("qbeast_id")!="bb-deada969" or not check(o) or type(step)is not int or not 0<=step<128:
    raise ValueError("Model, owner source, episode or optical observation outside contract")
   text=prompt(o)
   with LOCK:
    result=ENGINES[model].complete(text,max_tokens=12,temperature=0,seed=20261011+step,timeout=20)
   self.respond(200,{"model":model,"literal_reply":result,"prompt_sha256":hashlib.sha256(text.encode()).hexdigest(),
                     "checkpoint_sha256":CHECKPOINTS[model][1],"response_source":"ACTUAL_CPU_MODEL_INFERENCE"})
  except Exception as exc:
   self.respond(422,{"error_type":type(exc).__name__,"error":str(exc)[:200],"no_action_taken":True})
if __name__=="__main__":
 load()
 server=ThreadingHTTPServer(("127.0.0.1",8778),Handler)
 print("ZEREF_REAL_NATIVE_POLICY_INFERENCE_READY=127.0.0.1:8778",flush=True)
 server.serve_forever()
