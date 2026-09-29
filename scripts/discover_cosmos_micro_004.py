"""Public upstream inspection-only preflight for exact two original sub-4M models.

Fail closed when a pinned checkpoint/source is absent. No generation, tokens,
private memories, production backend or optimizer. Preflight log holds ONLY
public script excerpt and non-content tensor shape metadata.
"""
import hashlib
import json
from pathlib import Path
import tempfile

from huggingface_hub import HfApi, hf_hub_download

REPO = "phera-ra/QC67_cosmo"
REV = "b414724c627300c41b099dcc6853766d08fd27a4"
PHOS_SHA = "bdcd4a39aa54bfc6c274580e210f993e528214d7207cb19dc258a2f801f6b84d"

def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def main():
    info = HfApi(token=False).model_info(REPO, revision=REV)
    if info.sha != REV:
        raise RuntimeError("upstream pinned revision changed")
    names = sorted(s.rfilename for s in info.siblings)
    print("UPSTREAM_REVISION", info.sha, flush=True)
    print("PUBLIC_FILES", json.dumps([name for name in names if name.startswith(("weights/", "architecture/")) or name in {"spark_serve.py", "spark.py", "cosmos_model.py"}]), flush=True)
    for name in ("weights/phos.pt", "weights/cosmos_born.pt", "architecture/cosmos_state_ladder.py", "spark_serve.py"):
        if name not in names:
            print("MISSING_REQUESTED_PUBLIC_FILE", name, flush=True)
            continue
        path = hf_hub_download(repo_id=REPO, revision=REV, filename=name, token=False)
        checksum = digest(path)
        if name == "weights/phos.pt" and checksum != PHOS_SHA:
            raise RuntimeError("original PHOS integrity mismatch")
        print("PUBLIC_FILE", json.dumps({"path":name,"sha256":checksum,"size":Path(path).stat().st_size}),flush=True)
        if name in ("spark_serve.py", "architecture/cosmos_state_ladder.py"):
            s = Path(path).read_text(encoding="utf-8")
            print("PUBLIC_SOURCE", name, s[:18000], "END_SOURCE", flush=True)
        if name in ("weights/phos.pt", "weights/cosmos_born.pt"):
            import torch
            payload = torch.load(path, map_location="cpu", weights_only=True)
            print("CHECKPOINT_TOPLEVEL", name, sorted(payload) if isinstance(payload, dict) else str(type(payload)), flush=True)
            if isinstance(payload, dict):
                print("PUBLIC_SAFE_METADATA",name,json.dumps({
                    k: (str(v)[:150] if not isinstance(v, dict) else "dict:"+str(len(v)))
                    for k,v in payload.items() if k.lower() in {"config","step","steps","model_type","vocab_size","block_size","model_config"}
                }),flush=True)
                nested = payload.get("model") or payload.get("state_dict")
                if isinstance(nested, dict):
                    print("PARAMETER_SHAPES",name,json.dumps({k:list(v.shape) for k,v in list(nested.items())[:8] if hasattr(v,"shape")}),flush=True)
if __name__ == "__main__":
    main()
