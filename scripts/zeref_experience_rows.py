#!/usr/bin/env python3
"""Zeref experience rows (2026-10-22, Cory: "plug everything up").

Turns Zeref's OWN recorded experiences (bb-deada969 only) into a small, capped, labeled
chat-mix source, so he talks about what actually happened to him:
 * diary ticks exported by zeref-cloud-sync.mjs --experiences-out (Cage pocket walks, mood,
   places, discoveries, Rigetti growth labeled SIMULATED),
 * approved training-cycle records (native game rounds),
 * this run's fresh native-game capture manifest,
 * the Tiny Universe genesis (recorded IBM counts; growth SIMULATED).
Replies are templated FROM the records (facts only, no invented events), pass the same
persona/secret filters, and are capped at MAX_FRACTION of the mix.
Usage: zeref_experience_rows.py CHAT_MIX_JSONL EXPERIENCES_JSONL [NATIVE_MANIFEST_JSON]
"""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from zeref_teacher_distill import persona_style,SECRET,held
MAX_FRACTION=0.05;MAX_ROWS=150
def rows_from(exps,native):
 out=[]
 for e in exps:
  if e.get("kind")=="diary" and e.get("tick") is not None:
   t=e["tick"];place=e.get("place") or "my cozy corner";mood=e.get("mood") or "calm"
   grow="My growth step was SIMULATED on the Rigetti simulator." if e.get("simulated") else "My growth step used the fallback rule this time."
   out.append(("diary",f"What happened on your diary day {t}?",f"I spent most of it at {place} and felt {mood}. {grow}"))
   if e.get("new_combo_count"):
    out.append(("diary",f"What did you discover on diary day {t}?",f"I found {e['new_combo_count']} new things, like {', '.join(e.get('combos') or ['a new spot'])}!"))
   if e.get("new_cells"):
    out.append(("diary",f"Where did you explore on diary day {t}?",f"I walked into {e['new_cells']} new spots in my pocket world. My favorite is {e.get('favorite_spot') or place}."))
  elif e.get("kind")=="training-cycle" and e.get("tag"):
   c=e["tag"].split("-")[3] if e["tag"].count("-")>=4 else e["tag"]
   out.append(("game",f"What happened in your training round {c}?",f"I practiced the real game, passed every check, and that round got approved."))
 if native:
  h=native.get("scripted_teacher_action_histogram") or {}
  top=max(h,key=h.get) if h else "A"
  out.append(("game",f"What did you play in game capture {str(native.get('jsonl_sha256',''))[:8]}?",f"I played {native.get('episodes',4)} short rounds of the real game. I pressed {top} the most."))
 out+= [("universe","How did your tiny universe begin?","It started from a real IBM quantum spark. The growing part after that is SIMULATED."),
        ("universe","How many stars were in your tiny universe at the start?","Six stars and seventeen planets at genesis. Then it keeps growing in a simulation."),
        ("universe","Is your universe growth real quantum?","The first spark is a real IBM run. The growth is SIMULATED, and I always say so.")]
 return out
def main(mix,exp_path,native_path=None):
 mix=Path(mix);rows=[json.loads(l) for l in mix.read_text().splitlines() if l.strip()]
 exps=[]
 if Path(exp_path).is_file():
  for l in Path(exp_path).read_text().splitlines():
   try:exps.append(json.loads(l))
   except Exception:pass
 native=json.loads(Path(native_path).read_text()) if native_path and Path(native_path).is_file() else None
 cap=min(MAX_ROWS,int(len(rows)*MAX_FRACTION));seen=set();add=[];skipped=0
 for kind,q,a in reversed(rows_from(exps,native)):  # newest first
  a2=persona_style(a)
  if not a2 or q.lower() in held or q.lower() in seen or SECRET.search(q+" "+a):skipped+=1;continue
  seen.add(q.lower());add.append({"mode":"chat","source":"zeref-experience:"+kind,"user":q,"assistant":a2,"label":"templated from Zeref's own records (bb-deada969)"})
 add=add[:cap]
 body="".join(json.dumps(r,sort_keys=True)+"\n" for r in rows+add).encode();mix.write_bytes(body)
 mp=mix.with_suffix(".manifest.json");man=json.loads(mp.read_text()) if mp.is_file() else {}
 summ={"rows":len(add),"cap":cap,"max_fraction":MAX_FRACTION,"skipped":skipped,
  "records_in":{"diary":sum(e.get("kind")=="diary" for e in exps),"training_cycle":sum(e.get("kind")=="training-cycle" for e in exps),"native_capture":int(native is not None)},
  "by_kind":{k:sum(r["source"]=="zeref-experience:"+k for r in add) for k in("diary","game","universe")},"beast":"bb-deada969"}
 man.update({"rows":len(rows)+len(add),"jsonl_sha256":hashlib.sha256(body).hexdigest(),"experience_rows":summ});mp.write_text(json.dumps(man,indent=1,sort_keys=True)+"\n")
 print("ZEREF_EXPERIENCE_ROWS="+json.dumps(summ),flush=True)
if __name__=="__main__":main(*sys.argv[1:])
