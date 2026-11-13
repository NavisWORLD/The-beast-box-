#!/usr/bin/env python3
"""Mix the RECORDED English foundation corpus (evidence/zeref-english-001) into the existing
007 pretraining slice (build/zeref-006/pretrain-slice.jsonl) as a language-foundation share.

Nothing else changes: the trainer still draws ZEREF_006_PRETRAIN_PER_BATCH (default 2) rows per
batch from this one pool, next to 4 game rows and 12 chat rows (authored identity lessons, served
shape, Dolly). So the per-batch token budget for plain text is unchanged; only what fills it changes.

Share: ZEREF_ENGLISH_SHARE (default 0.5) of the pool rows are English corpus rows. 0 disables
(exact old pool). Rows rotate per cycle: order = sha256(seed + row_sha256), seed derived from the
cycle this round trains toward, so successive cycles walk through the corpus. Books and dialogue
are drawn ZEREF_ENGLISH_BOOK_SHARE (default 0.6) : rest. Held-out rows are never in the train file.

Usage: zeref_english_mix.py CORPUS_TRAIN_GZ MANIFEST PRETRAIN_JSONL SEED RECEIPT_JSON
"""
from __future__ import annotations
import gzip,hashlib,json,os,sys
from pathlib import Path
DEFAULT_SHARE=0.5
DEFAULT_BOOK_SHARE=0.6
DEFAULT_ROWS_IF_EMPTY=1500
def sha(b):return hashlib.sha256(b).hexdigest()
def pick(rows,seed,n_total,book_share):
 key=lambda r:sha((seed+":"+r["row_sha256"]).encode())
 books=sorted((r for r in rows if r.get("kind")=="book"),key=key)
 dia=sorted((r for r in rows if r.get("kind")!="book"),key=key)
 nb=min(len(books),round(n_total*book_share));nd=min(len(dia),n_total-nb)
 return books[:nb]+dia[:nd]
def mix(corpus_gz,manifest,pretrain,seed,receipt,share=None,book_share=None):
 share=float(os.environ.get("ZEREF_ENGLISH_SHARE",DEFAULT_SHARE)) if share is None else share
 book_share=float(os.environ.get("ZEREF_ENGLISH_BOOK_SHARE",DEFAULT_BOOK_SHARE)) if book_share is None else book_share
 if not 0<=share<1 or not 0<=book_share<=1:raise ValueError("share out of range")
 pretrain=Path(pretrain)
 existing=pretrain.read_text().splitlines() if pretrain.is_file() else []
 existing=[l for l in existing if l.strip()]
 man=json.loads(Path(manifest).read_text())
 raw=Path(corpus_gz).read_bytes()
 if sha(raw)!=man["files"]["train.jsonl.gz"]["sha256"]:raise ValueError("English corpus sha256 does not match the manifest")
 if man.get("label")!="RECORDED_CORPUS":raise ValueError("corpus must be labelled RECORDED_CORPUS")
 rows=[json.loads(l) for l in gzip.decompress(raw).decode().splitlines() if l.strip()]
 held={r["row_sha256"] for r in map(json.loads,Path(manifest).with_name("clarity-heldout.jsonl").read_text().splitlines())} if Path(manifest).with_name("clarity-heldout.jsonl").is_file() else set()
 rows=[r for r in rows if r["row_sha256"] not in held]
 n=0 if share==0 else (round(len(existing)*share/(1-share)) if existing else DEFAULT_ROWS_IF_EMPTY)
 chosen=pick(rows,seed,n,book_share) if n else []
 add=[json.dumps({"text":r["text"],"source":r["source"],"license":r["licence"],"label":"RECORDED_CORPUS","kind":r["kind"],"english_foundation":True},sort_keys=True) for r in chosen]
 lines=existing+add
 pretrain.parent.mkdir(parents=True,exist_ok=True)
 data="".join(l+"\n" for l in lines);pretrain.write_text(data)
 by={}
 for r in chosen:by[r["kind"]]=by.get(r["kind"],0)+1
 rec={"schema":"zeref-english-mix-v1","report_only":False,"gate_changed":False,"seed":seed,"share_setting":share,"book_share_setting":book_share,
  "pool_rows_before":len(existing),"english_rows_added":len(add),"english_rows_by_kind":by,"pool_rows_after":len(lines),
  "english_share_of_pool":round(len(add)/max(1,len(lines)),4),"corpus_train_sha256":man["files"]["train.jsonl.gz"]["sha256"],
  "pretrain_slice_sha256":sha(data.encode()),"label":"RECORDED_CORPUS (public English written by people; not Zeref's experience)"}
 Path(receipt).write_text(json.dumps(rec,indent=1,sort_keys=True)+"\n")
 print("ZEREF_ENGLISH_MIX="+json.dumps(rec,sort_keys=True),flush=True)
 return rec
if __name__=="__main__":mix(*sys.argv[1:6])
