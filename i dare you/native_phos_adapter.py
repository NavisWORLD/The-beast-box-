"""Native published PHOS serving adapter. Import ORIGINAL server source; no reimplementation."""
from __future__ import annotations
import hashlib
import importlib.util
import os
from pathlib import Path
import sys

MODEL_ID="phera-ra/QC67_cosmo"
EXPECTED_PIN="bdcd4a39aa54bfc6c274580e210f993e528214d7207cb19dc258a2f801f6b84d"

def load_native(checkpoint, root, revision, ledger, *, temperature=.8, top_p=.95, n=120):
    checkpoint,root=Path(checkpoint),Path(root)
    if not checkpoint.is_file(): raise FileNotFoundError(str(checkpoint))
    actual=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    expected=os.getenv("PHOS_EXPECTED_SHA256","")
    if not expected or actual != expected or actual != EXPECTED_PIN:
        raise ValueError("native PHOS checkpoint fails pinned SHA-256")
    serving=root/"serving"/"cosmos_serve.py"
    architecture=root/"architecture"/"cosmos_state_ladder.py"
    if not serving.is_file() or not architecture.is_file():
        raise FileNotFoundError("original serving/cosmos_serve.py and architecture/cosmos_state_ladder.py required")
    for folder in (root/"architecture",root/"serving"):
        if str(folder) not in sys.path:sys.path.insert(0,str(folder))
    spec=importlib.util.spec_from_file_location("phos_official_server",serving)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    native=m.NativeModel("cosmos-phos", checkpoint,"phos")
    if native.block != 128:
        raise ValueError(f"unexpected official PHOS block {native.block}; refusing ambiguous context")
    if not 0 <= temperature <= 2 or not 0 < top_p <= 1 or not 1 <= n <= 1024:
        raise ValueError("invalid generation parameters")
    ledger.emit("B0","native_provider_loaded",provider=MODEL_ID,revision=revision,
                checkpoint_sha256=actual, source_file="serving/cosmos_serve.py",
                context_chars=native.block, sample_chars=n, temperature=temperature,top_p=top_p,
                original_server_class="NativeModel", model_weight_training_performed=False)
    def answer(prompt):
        return native.generate(prompt,n=n,temperature=temperature,top_p=top_p)
    return answer, native.block
