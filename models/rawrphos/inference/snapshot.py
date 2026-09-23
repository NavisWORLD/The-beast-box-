"""Verify and load the published HF inference-only snapshot without optimizer state.

Unlike the resumable GitHub release, the Hub snapshot omits training_state.pt.
Every staged file is bound by inference-manifest.json and the trained parameter
identity; never use torch.load or execute arbitrary code from the model repo.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch
from safetensors.torch import load_file
from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
from rawrphos.training.checkpoint import parameter_hash

MANDATORY = frozenset({"model.safetensors", "config.json", "metadata.json",
                       "tokenizer/tokenizer.json", "tokenizer/metadata.json"})
PINNED_12K_SHA = "339fb8e1d6f3950e2aa15a6e33bf8c0f28dd655cefc93b7926fb7545e7e97601"


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_inference_snapshot(checkpoint: str | Path, expected_checkpoint_sha256: str | None = None) -> dict:
    directory = Path(checkpoint)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("unsafe or missing checkpoint directory")
    index = directory / "inference-manifest.json"
    if index.is_symlink() or index.stat().st_size > 65536:
        raise ValueError("unsafe inference manifest")
    manifest = json.loads(index.read_text())
    files = manifest.get("files")
    if (manifest.get("schema") != "rawrphos-inference-snapshot-v1"
            or manifest.get("model_id") != "rawrphos-native"
            or type(manifest.get("training_steps")) is not int
            or not isinstance(files, dict) or not MANDATORY.issubset(files)
            or len(files) > 30):
        raise ValueError("invalid inference snapshot manifest")
    for rel, digest in files.items():
        if (not isinstance(rel, str) or not rel or rel.startswith("/")
                or ".." in Path(rel).parts or Path(rel).is_absolute()
                or not isinstance(digest, str) or len(digest) != 64):
            raise ValueError("unsafe inference member")
        target = directory / rel
        if any(parent.is_symlink() for parent in (target, *target.parents)
               if parent != directory.parent and parent != directory.parent.parent):
            raise ValueError("symlink inference member")
        if not target.is_file() or file_sha256(target) != digest:
            raise ValueError("inference member hash mismatch: " + rel)
    metadata = json.loads((directory / "metadata.json").read_text())
    config = RawrphosConfig.from_dict(json.loads((directory / "config.json").read_text()))
    sha = metadata.get("checkpoint_sha256")
    if (metadata.get("model_id") != "rawrphos-native"
            or metadata.get("lineage") != "native-from-scratch"
            or metadata.get("training_steps") != manifest["training_steps"]
            or sha != files["model.safetensors"]
            or sha != manifest.get("checkpoint_sha256")
            or (expected_checkpoint_sha256 is not None and sha != expected_checkpoint_sha256)):
        raise ValueError("inference snapshot identity mismatch")
    tokenizer = RawrphosTokenizer.load(directory / "tokenizer")
    if tokenizer.sha256 != metadata.get("tokenizer_sha256") or tokenizer.vocab_size != config.vocab_size:
        raise ValueError("inference tokenizer/model mismatch")
    model = RawrphosLM(config)
    model.load_state_dict(load_file(str(directory / "model.safetensors")), strict=True)
    if (not all(bool(torch.isfinite(tensor).all()) for tensor in model.state_dict().values())
            or model.parameter_count() != metadata.get("parameter_count")
            or parameter_hash(model) != metadata.get("parameter_sha256")):
        raise ValueError("inference parameter identity mismatch")
    return {"model": model, "tokenizer": tokenizer, "metadata": metadata,
            "config": config, "manifest": manifest, "state": None}
