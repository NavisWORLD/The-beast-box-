#!/usr/bin/env python3
"""007: per-round free pretraining slice from TinyStories (CDLA-Sharing-1.0, Eldan & Li 2023).
The workflow fetches a 2 MB byte range at an offset rotated by run id, always past the first
50,000 stories (~45 MB) already used for the 14k corpus. Partial stories at both ends are dropped."""
import json,sys,hashlib
raw,out,offset=sys.argv[1],sys.argv[2],int(sys.argv[3])
text=open(raw,"rb").read().decode("utf-8","ignore")
parts=[p.strip() for p in text.split("<|endoftext|>")][1:-1]
rows=[{"text":p,"source":"roneneldan/TinyStories@f54c09fd TinyStories-train.txt","license":"CDLA-Sharing-1.0","byte_offset":offset}
      for p in parts if 80<=len(p)<=1600][:1500]
data="".join(json.dumps(r,sort_keys=True)+"\n" for r in rows)
open(out,"w").write(data)
print("ZEREF_PRETRAIN_SLICE_BUILT="+json.dumps({"stories":len(rows),"byte_offset":offset,"sha256":hashlib.sha256(data.encode()).hexdigest()}))
