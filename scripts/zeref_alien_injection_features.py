#!/usr/bin/env python3
"""Alien Injection 001: derive a public feature packet from the TALK-006 alien corpus.
The packet only SEEDS/TAGS a quantum run (and the QVM rotation vector). Quantum hardware
cannot learn text; nothing here claims it does. Writes evidence/zeref-alien-injection-001/."""
import hashlib,json,statistics as st,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"evidence/zeref-alien-injection-001"
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 tmp=Path(tempfile.mkdtemp());subprocess.run([sys.executable,str(ROOT/"scripts/build_zeref_talk006_alien_corpus.py"),"--out-dir",str(tmp)],check=True,capture_output=True)
 train=(tmp/"train.jsonl").read_bytes();hold=(tmp/"holdout.jsonl").read_bytes()
 rows=[json.loads(l) for l in (train+hold).splitlines() if l.strip()]
 replies=[r["text"].split("\nZeref: ",1)[1] for r in rows];words=[len(x.split()) for x in replies];chars=[len(x) for x in replies]
 vocab={w.lower().strip(".,!?;:") for x in replies for w in x.split()};uniq=[len(set(x.lower().split()))/max(1,len(x.split())) for x in replies]
 nulls=[json.loads((ROOT/f"experiments/zeref/talk006-alien/NULL_RUN_00{i}.json").read_text()) for i in (1,2)]
 style=[c["alien_style_score"] for c in nulls[0]["candidates"] if "alien_style_score" in c];parent_style=nulls[0].get("parent_alien_style_score")
 cats={};[cats.__setitem__(r["category"],cats.get(r["category"],0)+1) for r in rows]
 feat={"corpus_train_sha256":sha(train),"corpus_holdout_sha256":sha(hold),"bytes_train":len(train),"bytes_holdout":len(hold),
  "examples":len(rows),"train_examples":sum(r["split"]=="train" for r in rows),"categories":cats,
  "reply_words":{"mean":round(st.mean(words),3),"stdev":round(st.pstdev(words),3),"min":min(words),"max":max(words)},
  "reply_chars":{"mean":round(st.mean(chars),3),"max":max(chars)},"vocab_size":len(vocab),"type_token_ratio_mean":round(st.mean(uniq),4),
  "style_score_stats":{"source":"experiments/zeref/talk006-alien/NULL_RUN_001.json","parent":parent_style,"candidates":style,"mean":round(st.mean(style),6),"max":max(style)},
  "null_runs":[{"file":f"NULL_RUN_00{i+1}.json","selection_status":n["selection_status"]} for i,n in enumerate(nulls)]}
 nums=[feat["reply_words"]["mean"]/40,feat["reply_words"]["stdev"]/20,feat["reply_chars"]["mean"]/240,feat["vocab_size"]/1000,feat["type_token_ratio_mean"],feat["style_score_stats"]["mean"]/2,
  feat["style_score_stats"]["max"]/2,(parent_style or 1)/2,len(cats)/12,feat["train_examples"]/100,int(feat["corpus_train_sha256"][:8],16)/2**32,int(feat["corpus_holdout_sha256"][:8],16)/2**32]
 vec=[round(min(.95,max(.05,v)),4) for v in nums]
 body={"schema":"beastbox-alien-injection-features-v1","creature_id":"bb-deada969","features":feat,"alien_vector_12":vec,
  "label":"Alien corpus features SEED and TAG the quantum run only. Quantum hardware cannot learn text. Unusual style is model behaviour, not alien intelligence.",
  "raw_dialogue_in_packet":False}
 raw=json.dumps(body,sort_keys=True).encode();body["packet_sha256"]=sha(raw)
 OUT.mkdir(parents=True,exist_ok=True);(OUT/"alien-features.json").write_text(json.dumps(body,indent=1,sort_keys=True)+"\n")
 print("ALIEN_PACKET="+json.dumps({"packet_sha256":body["packet_sha256"],"examples":feat["examples"],"vector":vec}))
if __name__=="__main__":main()
