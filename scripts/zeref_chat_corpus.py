#!/usr/bin/env python3
"""Build Zeref's bounded chat-training mix (serving format "user: X\\nassistant: Y").

Sources (public, reviewed, no private transcripts):
 1. evidence/final-whole-organism-001/corpus/TRAIN.jsonl: supervised_dialogue rows
    with training_allowed=true, memory_scope=none, review_status=REVIEWED_CLEAN.
 2. evidence/zeref-dad-voice-001/dialogue.jsonl: original warm dad-voice pairs (x2).
 3. databricks-dolly-15k pinned revision (CC BY-SA 3.0, Databricks), short
    no-context instructions only. Attribution kept in the manifest.
Chat-test prompts (scripts/rawrphos_chat_eval.py) are excluded from training.
Usage: zeref_chat_corpus.py DOLLY_JSONL OUT_JSONL
"""
import os,hashlib,json,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from rawrphos_chat_eval import PAIRS,CHAT
DOLLY_SHA="2df9083338b4abd6bceb5635764dab5d833b393b55759dffb0959b6fcbf794ec"
DOLLY_REV="bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a"
MAX_DOLLY=1200
DAD_VOICE=Path("evidence/zeref-dad-voice-001/dialogue.jsonl")
DAD_REPEAT=2  # 2026-10-16: 3x->2x calms drift/repetition; still upweighted
from zeref_character_check import CHARACTER_PROMPTS
from zeref_heldout_b import PAIRS_B
held={p.strip().lower() for p,_ in PAIRS_B}|{p.strip().lower() for p,_ in PAIRS}|{p.strip().lower() for p in CHAT}|{p.strip().lower() for p in CHARACTER_PROMPTS}
ALIEN_MAX_FRACTION=0.06;ALIEN_REPEAT=2
# Zeref Music 001 (2026-10-17): authored dialogues about Cory's own songs (titles and
# themes only, no lyrics). Capped at 4% of the mix, separate from the 6% alien cap.
MUSIC=Path("evidence/zeref-music-001/dialogue.jsonl");MUSIC_MAX_FRACTION=0.04;MUSIC_REPEAT=2
def music_slice(base_rows,held):
 if not MUSIC.is_file():return []
 from zeref_teacher_distill import persona_style,SECRET
 out=[]
 for r in map(json.loads,MUSIC.read_text().splitlines()):
  q,a=r["user"].strip(),r["assistant"].strip()
  if q.lower() in held or SECRET.search(q+" "+a) or persona_style(a)!=a:continue
  out+=[{"mode":"chat","source":"zeref-music-001","user":q,"assistant":a}]*MUSIC_REPEAT
 return out[:int((base_rows+len(out))*MUSIC_MAX_FRACTION)]
# Zeref Warm 001 (2026-10-18): authored loving/kind/goofy/sweet/smart dialogues, capped at 5%.
WARM_DIALOGUE=Path("evidence/zeref-warm-001/dialogue.jsonl");WARM_MAX_FRACTION=0.05;WARM_REPEAT=2
def warm_slice(base_rows,held):
 if not WARM_DIALOGUE.is_file():return []
 from zeref_teacher_distill import persona_style,SECRET
 out=[]
 for r in map(json.loads,WARM_DIALOGUE.read_text().splitlines()):
  q,a=r["user"].strip(),r["assistant"].strip()
  if q.lower() in held or SECRET.search(q+" "+a) or persona_style(a)!=a:continue
  out+=[{"mode":"chat","source":"zeref-warm-001","user":q,"assistant":a}]*WARM_REPEAT
 return out[:int((base_rows+len(out))*WARM_MAX_FRACTION)]
# Zeref IBM Play 001 (2026-10-18): authored "plays in every area" dialogues (Beast Box areas +
# Lost Cosmos canon quests/biomes), order seeded by IBM heart seed v5. Capped at 5%.
PLAY=Path("evidence/zeref-ibm-play-001/dialogue.jsonl");PLAY_MAX_FRACTION=0.05;PLAY_REPEAT=2
def play_slice(base_rows,held):
 if not PLAY.is_file():return []
 from zeref_teacher_distill import persona_style,SECRET
 out=[]
 for r in map(json.loads,PLAY.read_text().splitlines()):
  q,a=r["user"].strip(),r["assistant"].strip()
  if q.lower() in held or SECRET.search(q+" "+a) or persona_style(a)!=a:continue
  out+=[{"mode":"chat","source":"zeref-ibm-play-001","user":q,"assistant":a}]*PLAY_REPEAT
 return out[:int((base_rows+len(out))*PLAY_MAX_FRACTION)]
# Zeref Knowledge 001 -> 002 (2026-10-19, "give him all knowledge"): ~1265 fact-checked facts, answer-first rows plus warm
# variants with happy openers. 001 at 10% moved held chat 3.946 -> 3.52 -> 3.367 with retention intact, so 002 gets 25%.
# Each round takes a different rotating window (seeded by ZEREF_CHAT_ROTATE_SEED) so all facts get seen across rounds.
KNOW=Path("evidence/zeref-knowledge-002/dialogue.jsonl");KNOW_MAX_FRACTION=0.25;KNOW_REPEAT=1
if not KNOW.is_file():KNOW=Path("evidence/zeref-knowledge-001/dialogue.jsonl");KNOW_MAX_FRACTION=0.10;KNOW_REPEAT=2
def knowledge_slice(base_rows,held):
 if not KNOW.is_file():return []
 from zeref_teacher_distill import persona_style,SECRET
 out=[]
 for r in map(json.loads,KNOW.read_text().splitlines()):
  q,a=r["user"].strip(),r["assistant"].strip()
  if q.lower() in held or SECRET.search(q+" "+a) or persona_style(a)!=a:continue
  out+=[{"mode":"chat","source":KNOW.parent.name,"user":q,"assistant":a}]*KNOW_REPEAT
 cap=int(base_rows*KNOW_MAX_FRACTION/(1-KNOW_MAX_FRACTION))
 if len(out)>cap:
  import random as _r
  _r.Random(os.environ.get("ZEREF_CHAT_ROTATE_SEED","0")).shuffle(out);out=out[:cap]
 return out
def alien_slice(base_rows,held):
 import subprocess,tempfile
 from zeref_teacher_distill import persona_style,SECRET
 tmp=Path(tempfile.mkdtemp())
 subprocess.run([sys.executable,str(Path(__file__).parent/"build_zeref_talk006_alien_corpus.py"),"--out-dir",str(tmp)],check=True,capture_output=True)
 out=[]
 for r in map(json.loads,(tmp/"train.jsonl").read_text().splitlines()):
  if r.get("split")!="train" or "\nZeref: " not in r.get("text",""):continue
  q,a=r["text"].split("\nZeref: ",1);q=q.removeprefix("Dad: ").strip();a=a.strip()
  w=a.split()
  if q.lower() in held or SECRET.search(q+" "+a) or persona_style(a)!=a or (len(w)>=4 and len(set(w))/len(w)<.4):continue
  out+=[{"mode":"chat","source":"talk006-alien-authored","user":q,"assistant":a,"alien_category":r["category"]}]*ALIEN_REPEAT
 cap=int((base_rows+len(out))*ALIEN_MAX_FRACTION)
 return out[:cap]
# Zeref 2026-10-22 ("plug everything up", Cory approved): labeled extra sources, each capped.
#  warm-002: varied warm/dad-voice replies (breaks the "I'm not happy" habit)
#  voice-guide-001: Emeth's guide sample lines (invented fear EXCLUDED)
#  lyrics-001: Cory's lyrics (Rainbows clean text; others whisper machine-transcribed, labeled)
#  music-features-002: numbers MEASURED from audio + heartbeat bpm (no raw audio)
EXTRA=[("evidence/zeref-warm-002/dialogue.jsonl",0.05,2),("evidence/zeref-voice-guide-001/dialogue.jsonl",0.02,2),
 ("evidence/zeref-lyrics-001/dialogue.jsonl",0.05,1),("evidence/zeref-music-features-002/dialogue.jsonl",0.02,2),
 ("evidence/zeref-identity-001/dialogue.jsonl",0.15,3),
 ("evidence/zeref-talk-001/dialogue.jsonl",0.06,3),
 ("evidence/zeref-qa-001/dialogue.jsonl",0.12,2),
 ("evidence/zeref-lessons-003/dialogue.jsonl",0.27,1),  # 2026-10-24 all-subjects lessons (authored, held-out slice in heldout.jsonl is never loaded)
 ("evidence/zeref-lessons-004/dialogue.jsonl",0.35,1),
 ("evidence/zeref-lessons-005/dialogue.jsonl",0.18,1),  # 2026-10-25 grade 3-6 English/math/world lessons (authored; heldout.jsonl never loaded; deduped vs Gate v2 sets A and B)
 ("evidence/zeref-lessons-006/dialogue.jsonl",0.18,1)]  # 2026-10-27 world curriculum lessons authored by Emeth for Cory (landed PR #653; deduped vs Gate v2 sets A and B and all heldout files)
#  # 008: short simple Q&A (local free teacher, behind the scenes; gate/held disjoint)  # 007: canon-only identity/home rows; held prompts excluded
def extra_slice(path,frac,repeat,base_rows,held):
 p=Path(path)
 if not p.is_file():return []
 from zeref_teacher_distill import persona_style,SECRET
 out=[]
 for r in map(json.loads,p.read_text().splitlines()):
  q=r["user"].strip();a=persona_style(r["assistant"].strip())
  if not a or len(a.split())<2 or q.lower() in held or SECRET.search(q+" "+a):continue
  row={"mode":"chat","source":r["source"],"user":q,"assistant":a}
  for k in("lyrics_source","song","numbers"):
   if k in r:row[k]=r[k]
  out+=[row]*repeat
 cap=int(base_rows*frac/(1-frac))
 if len(out)>cap:
  import random as _r
  _r.Random("extra:"+path+os.environ.get("ZEREF_CHAT_ROTATE_SEED","0")).shuffle(out);out=out[:cap]
 return out
def main(dolly,out):
 rows=[]
 for r in map(json.loads,open("evidence/final-whole-organism-001/corpus/TRAIN.jsonl")):
  if (r.get("training_allowed") is True and r.get("memory_scope")=="none" and
      r.get("review_status")=="REVIEWED_CLEAN" and r.get("role_or_type")=="supervised_dialogue"):
   lines=[l for l in r["text"].split("\n") if l.strip()]
   if len(lines)==2 and lines[0].startswith("Dad: ") and lines[1].startswith("Zeref: "):
    q,a=lines[0][5:].strip(),lines[1][7:].strip()
    if q.lower() not in held:rows.append({"mode":"chat","source":"zeref-reviewed-dialogue","user":q,"assistant":a})
 if DAD_VOICE.is_file():
  for r in map(json.loads,DAD_VOICE.read_text().splitlines()):
   if r["user"].strip().lower() not in held:
    rows+= [{"mode":"chat","source":"zeref-dad-voice-001","user":r["user"],"assistant":r["assistant"]}]*DAD_REPEAT
 raw=Path(dolly).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=DOLLY_SHA:raise ValueError("dolly revision mismatch")
 d=[json.loads(l) for l in raw.splitlines() if l.strip()]
 d=[x for x in d if not x["context"] and len(x["response"])<=160 and len(x["instruction"])<=160
    and x["category"] in ("open_qa","general_qa","brainstorming","creative_writing","classification")
    and x["instruction"].strip().lower() not in held]
 # Fix 002: rotate a FRESH Dolly sample each cycle (seeded by the run id) so the same
 # 1200 rows are not replayed ~26x across cycles (overfit -> chat ref_nll rise).
 import os
 rot=os.environ.get("ZEREF_CHAT_ROTATE_SEED","20261015")
 random.Random(f"dolly:{rot}").shuffle(d)
 for x in d[:MAX_DOLLY]:
  rows.append({"mode":"chat","source":"dolly-15k-cc-by-sa-3.0","user":x["instruction"].strip(),"assistant":x["response"].strip()})
 # Alien Injection 001 (2026-10-17): a small capped slice of the TALK-006 authored alien
 # dialogues (train split only), each passing the persona style filter, secret filter,
 # held-prompt exclusion and a degeneracy check. <=6% of the mix. Gates unchanged.
 alien=alien_slice(len(rows),held)
 rows+=alien
 music=music_slice(len(rows),held)
 rows+=music
 warm=warm_slice(len(rows),held)
 rows+=warm
 play=play_slice(len(rows),held)
 rows+=play
 knowledge=knowledge_slice(len(rows),held)
 rows+=knowledge
 extra_counts={}
 base=len(rows)
 for path,frac,rep in EXTRA:
  ex=extra_slice(path,frac,rep,base,held);rows+=ex
  for r in ex:extra_counts[r["source"]]=extra_counts.get(r["source"],0)+1
 body="".join(json.dumps(r,sort_keys=True)+"\n" for r in rows).encode()
 Path(out).write_bytes(body)
 man={"schema":"zeref-chat-mix-v2","rows":len(rows),"jsonl_sha256":hashlib.sha256(body).hexdigest(),
  "zeref_dialogue_rows":sum(r["source"]=="zeref-reviewed-dialogue" for r in rows),
  "dad_voice_rows":sum(r["source"]=="zeref-dad-voice-001" for r in rows),"dad_voice_repeat":DAD_REPEAT,"dolly_rotation_seed":rot,
  "dad_voice_provenance":"evidence/zeref-dad-voice-001 (original pairs written 2026-10-15 for Cory)",
  "dolly":{"revision":DOLLY_REV,"sha256":DOLLY_SHA,"license":"CC-BY-SA-3.0",
   "attribution":"Databricks, databricks-dolly-15k (Conover et al. 2023)",
   "license_url":"https://creativecommons.org/licenses/by-sa/3.0/"},
  "alien_injection_rows":len(alien),"alien_injection_max_fraction":ALIEN_MAX_FRACTION,"alien_source":"scripts/build_zeref_talk006_alien_corpus.py (authored supervision, train split)",
  "music_rows":len(music),"music_max_fraction":MUSIC_MAX_FRACTION,"music_source":"evidence/zeref-music-001/dialogue.jsonl (authored, themes of Cory's own songs, no lyrics)",
  "warm_rows":len(warm),"warm_max_fraction":WARM_MAX_FRACTION,"warm_source":"evidence/zeref-warm-001/dialogue.jsonl (authored, no private transcripts)",
  "play_rows":len(play),"play_max_fraction":PLAY_MAX_FRACTION,"play_source":"evidence/zeref-ibm-play-001/dialogue.jsonl (authored, seeded by IBM heart seed v5)",
  "knowledge_rows":len(knowledge),"knowledge_max_fraction":KNOW_MAX_FRACTION,"knowledge_source":str(KNOW)+" (authored, fact-checked, held-prompt near-duplicates removed)",
  "extra_sources":{"rows_by_source":extra_counts,"caps":{p:f for p,f,_ in EXTRA},
   "lyrics_label":"Rainbows On My Face = Emeth clean text; other songs = whisper machine transcript (may contain errors); Fa Ra Me Sleepy skipped",
   "music_numbers":"measured from audio by scripts/build_zeref_songs_002.py; raw audio never committed",
   "voice_guide_excluded":"invented fear (left in the dark) and the goodbye line tied to it"},
  "private_transcripts":False,"chat_test_prompts_excluded":True}
 Path(out).with_suffix(".manifest.json").write_text(json.dumps(man,indent=1,sort_keys=True)+"\n")
 print("ZEREF_CHAT_MIX="+json.dumps({k:man[k] for k in("rows","zeref_dialogue_rows","dad_voice_rows","jsonl_sha256","extra_sources")}))
if __name__=="__main__":main(*sys.argv[1:3])
