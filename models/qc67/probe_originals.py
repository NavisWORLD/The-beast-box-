"""Read-only provenance/shape compatibility probe for two published QC67 weights.

Only the published owner repositories and immutable revisions are fetched.
No optimizer, service, secrets, owner memory or external paid APIs are used.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import urllib.request

from huggingface_hub import hf_hub_download

HF_REPO = "phera-ra/QC67_cosmo"
HF_REV = "b414724c627300c41b099dcc6853766d08fd27a4"
SOURCE_REPO = "NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2"
SOURCE_REV = "c8219c3f27bf8f1319a687d6b22b29ca29c8fde0"
WEIGHTS = {
    "phos": ("weights/phos.pt", "bdcd4a39aa54bfc6c274580e210f993e528214d7207cb19dc258a2f801f6b84d"),
    "samgo": ("weights/samgo_weights.pt", "871c265c062430c77d5528ee5fb9119f7d86668ebd81cfa4951db6a906a92b5a"),
}


def _download_hf(path: str) -> Path:
    return Path(hf_hub_download(HF_REPO, path, revision=HF_REV, token=False))


def _download_original_54d(root: Path) -> None:
    for name in ("cosmos_config.py", "cosmos_model.py"):
        rel = "cosmos/web/cosmosynapse/model/" + name
        url = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_REV}/{rel}"
        request = urllib.request.Request(url, headers={"User-Agent": "QC67-source-shape-probe"})
        with urllib.request.urlopen(request, timeout=25) as response:
            source = response.read(110_001)
            if response.status != 200 or len(source) > 110_000:
                raise RuntimeError("original 54D source unavailable")
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source)
        print("PINNED_54D_SOURCE", rel, "sha256", hashlib.sha256(source).hexdigest(), flush=True)


def _verified_weight(name: str) -> Path:
    path, expected = WEIGHTS[name]
    filename = _download_hf(path)
    actual = hashlib.file_digest(filename.open("rb"), "sha256").hexdigest()
    if actual != expected:
        raise RuntimeError(f"{name} published weight digest mismatch")
    print("WEIGHT_SHA256_VERIFIED", name, actual, flush=True)
    return filename


def main() -> None:
    import torch
    with tempfile.TemporaryDirectory(prefix="qc67-shape-probe-") as td:
        root = Path(td)
        for name in ("cosmos_state_ladder.py", "cosmos_spark_cst.py"):
            source = _download_hf("architecture/" + name).read_bytes()
            (root / name).write_bytes(source)
            print("PINNED_PHOS_SOURCE", name, "sha256", hashlib.sha256(source).hexdigest(), flush=True)
        sys.path.insert(0, str(root))
        _download_original_54d(root)
        sys.path.insert(0, str(root))
        import cosmos_state_ladder as ladder
        from cosmos.web.cosmosynapse.model.cosmos_config import CosmosConfig
        from cosmos.web.cosmosynapse.model.cosmos_model import CosmosTransformer
        print("TORCH", torch.__version__, flush=True)
        phos = torch.load(_verified_weight("phos"), map_location="cpu", weights_only=True)
        print("PHOS_KEYS", sorted(phos.keys()) if isinstance(phos, dict) else type(phos).__name__, flush=True)
        vocab = phos["vocab_list"]
        model = ladder.Ladder(len(vocab), "dyn12", "harmonic")
        missing, unexpected = model.load_state_dict(phos["model"], strict=True)
        assert not missing and not unexpected
        model.eval()
        with torch.inference_mode():
            logits, _loss = model(torch.tensor([[0, 1, 0]], dtype=torch.long))
        assert torch.isfinite(logits).all()
        print("PHOS_STRICT_LOAD_AND_FORWARD_PASS", "vocab", len(vocab), "shape", list(logits.shape), flush=True)
        del model, phos
        samgo = torch.load(_verified_weight("samgo"), map_location="cpu", weights_only=True)
        print("SAMGO_KEYS", sorted(samgo.keys()) if isinstance(samgo, dict) else type(samgo).__name__, flush=True)
        cfg = CosmosConfig()
        for key, value in samgo.get("config", {}).items():
            if hasattr(cfg, key) and isinstance(value, (int, float, str, bool)):
                try:
                    setattr(cfg, key, value)
                except AttributeError:
                    pass
        m = CosmosTransformer(cfg)
        missing, unexpected = m.load_state_dict(samgo["model_state_dict"], strict=True)
        assert not missing and not unexpected
        m.eval()
        with torch.inference_mode():
            out = m(torch.tensor([[1, 2, 3]], dtype=torch.long))
        assert torch.isfinite(out["logits"]).all()
        print("SAMGO_STRICT_LOAD_AND_FORWARD_PASS", "config", json.dumps(cfg.to_dict(), sort_keys=True), "shape", list(out["logits"].shape), flush=True)


if __name__ == "__main__":
    main()
