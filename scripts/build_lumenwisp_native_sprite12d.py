#!/usr/bin/env python3
"""Derived measured-source Wraith offspring: native pixel sprite -> fresh QPU.

Parent's actual 48-step classical action trace is metadata/control, not optical
game vision. Original IBM source remains distinct from this NEW IBM job.
"""
import hashlib
import json
import math
from pathlib import Path

PARENT=Path("build/lumenwisp-parent-wraith")
OUT=Path("build/lumenwisp-pre-qpu")
ACTIONS=("explore","inspect","listen","wander")
ID="bb-4a61a8d5"
IBM="db4rg5klf4us73c34tqg"
AZURE="3c9e2a90-c45f-11f1-ae67-7ced8dda8a51"

def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def features(pixels):
 # Native sprite 64x64 RGBA. Measure actual pixels, not hallucinated scene objects.
 n=len(pixels);assert n>0
 rgb=[((r*a/255),(g*a/255),(b*a/255)) for r,g,b,a in pixels]
 y=[(.2126*r+.7152*g+.0722*b)/255 for r,g,b in rgb]
 mean=sum(y)/n
 contrast=math.sqrt(sum((v-mean)**2 for v in y)/n)
 hist=[0]*16
 for z in y:hist[min(15,int(z*16))]+=1
 entropy=-sum((c/n)*math.log2(c/n) for c in hist if c)/4
 edgeh=sum(abs(y[i]-y[i-1]) for i in range(n) if i%64>0)/max(1,n-n//64)
 edgev=sum(abs(y[i]-y[i-64]) for i in range(64,n))/max(1,n-64)
 return [mean,min(1,contrast*2.0),sum(z>.55 for z in y)/n,sum(z<.10 for z in y)/n,
  sum(max(0,b-r/2-g/2) for r,g,b in rgb)/(255*n),
  sum(r for r,g,b in rgb)/(255*n),sum(g for r,g,b in rgb)/(255*n),sum(b for r,g,b in rgb)/(255*n),
  sum(1 for r,g,b,a in pixels if a>64)/n,min(1,edgeh*4),min(1,edgev*4),max(0,min(1,entropy))]

def main():
 data=json.loads((PARENT/"wraith-data.json").read_text())
 art=(PARENT/"wraith-64x64-rgba.bin").read_bytes()
 if len(art)!=64*64*4:raise ValueError("Verified native Wraith sprite must contain 64x64 RGBA pixels")
 if (data.get("identity",{}).get("qbeast_id")!=ID or
    data.get("quantum",{}).get("ibm_job_id")!=IBM or
    data.get("quantum",{}).get("azure_qvm_job_id")!=AZURE or
    data.get("provenance",{}).get("save_load_replay_exact") is not True):
  raise ValueError("Wrong parent Wraith QBEAST, fabricated physics source or unverified save")
 observed=data.get("behavior",{}).get("action_counts",{})
 if sum(observed.values())!=48 or not all(type(observed.get(a)) is int and observed[a]>=0 for a in ACTIONS):
  raise ValueError("Parent 48-step ACTUAL classical behavior receipt missing")
 pix=[tuple(art[i:i+4]) for i in range(0,len(art),4)]
 global12=features(pix)
 quadrants=[]
 for row in (0,32):
  for col in (0,32):
   segment=[pix[y*64+x] for y in range(row,row+32) for x in range(col,col+32)]
   # Features expects a continuous row; edge measures are bounded, but 64 is
   # preserved in this published preprocessor as a fixed deterministic transform.
   quadrants.append(features(segment))
 controls=[observed[a]/48 for a in ACTIONS]
 core={"schema":"beastbox-measured-qbeast-lineage-native-sprite12d-v1",
  "offspring_name":"Lumenwisp","source_kind":"REAL_WRAITH_QBEAST_NATIVE_SPRITE_PLUS_CLASSICAL_BEHAVIOR",
  "parent_qbeast_id":ID,"parent_ibm_job_id":IBM,"parent_azure_job_id":AZURE,
  "parent_sprite_sha256":hashlib.sha256(art).hexdigest(),
  "parent_data_sha256":hashlib.sha256((PARENT/"wraith-data.json").read_bytes()).hexdigest(),
  "parent_action_counts":{a:observed[a] for a in ACTIONS},
  "behavior_mix":controls,
  "global_12d":[round(x,9) for x in global12],
  "quarter_means_12d":[[round(x,9) for x in q] for q in quadrants],
  "pixels_are_measured_from_verified_qbeast":True,
  "physical_game_frame_was_observed":False,
  "original_parent_physics_is_ibm_hardware":True,
  "raw_source_is_a_quantum_state":False,
  "not_a_new_user_photo":True}
 packet=dict(core,feature_packet_sha256=digest(core))
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/"feature_packet.json").write_text(json.dumps(packet,indent=2,sort_keys=True)+'\n')
 print("LUMENWISP_TRUE_NATIVE_SPRITE_PRE_QPU="+json.dumps({"parent":ID,"sha256":packet["feature_packet_sha256"],"source_pixels_sha256":packet["parent_sprite_sha256"],"behavior_mix":controls},sort_keys=True),flush=True)

if __name__=="__main__":main()
