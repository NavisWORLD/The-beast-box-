"""Publish an inference-only, hash-verified RAWRPHØS 12K snapshot to its owner's HF repo.

Run explicitly with --confirm and an HF_TOKEN with model-repository write access.
This deliberately does not upload the resumable optimizer/RNG state or COSMOS data.
A Hub model repository is NOT a deployed inference endpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from rawrphos.scripts.install_pinned_12k import install, verify, WEIGHT_SHA, TAG

DEFAULT_REPO = "phera-ra/rawrphos-native-12k"
SOURCE_COMMIT = "4054d675c4ef85d1343890f2e956dbc2fe88b2e6"
FILES = (
    "model.safetensors",
    "config.json",
    "metadata.json",
    "tokenizer/tokenizer.json",
    "tokenizer/metadata.json",
)
SOURCE_FILES = (
    "models/rawrphos/architecture/model.py",
    "models/rawrphos/architecture/generation.py",
    "models/rawrphos/tokenizer/tokenizer.py",
    "models/rawrphos/inference/engine.py",
    "models/rawrphos/inference/snapshot.py",
    "models/rawrphos/inference/server.py",
    "models/rawrphos/training/checkpoint.py",
    "models/rawrphos/pyproject.toml",
    "models/rawrphos/data/acquisition.json",
    "LICENSE",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def make_card(repo_id: str, metadata: dict) -> str:
    return f"""---
language: en
license: other
tags:
- pytorch
- safetensors
- text-generation
- custom-architecture
- experimental
- rawrphos
---

# RAWRPHØS native 12K — Cory Davis / COSMOS

This is the inference-only snapshot of the **native-from-scratch RAWRPHØS**
PyTorch model trained for 12,000 cumulative optimizer steps. It is an
experimental, small, story-continuation candidate, not a general assistant
or a Transformers AutoModel-compatible architecture.

- Model ID: `rawrphos-native`
- Training steps: **12000**
- Model-weights SHA-256: `{WEIGHT_SHA}`
- Model parameter count: {metadata["parameter_count"]}
- Original release: https://github.com/NavisWORLD/The-beast-box-/releases/tag/{TAG}
- Pinned research source: https://github.com/NavisWORLD/The-beast-box-/tree/{SOURCE_COMMIT}/models/rawrphos
- Integration docs: https://github.com/NavisWORLD/The-beast-box-/blob/feature/rawrphos-native-model-001/docs/RAWRPHOS_LOCAL_12K.md

## Usage

Use the original custom `rawrphos` Python package at the pinned research
source. The model uses its own tokenizer/config; do not feed this checkpoint
to a generic Transformers model class. After installing the package, download
the snapshot and verify each member against `inference-manifest.json`.
For full original-release provenance verification, use the pinned GitHub
release and its full manifest (including the separate, deliberately omitted
training state). The original inference server exposes private
`/v1/chat/completions`, `/v1/models` and `/model/info` locally after
loading the original checkpoint.

**Uploading this model to the Hugging Face Hub does not create an inference
endpoint.** For a hosted API, deploy compatible serving code on an approved
service, verify that it loads this exact weights hash, then explicitly
configure COSMOS Brain Bay to use that service's actual HTTPS URL.

## Training data / limitations

Training used attributed TinyStories (Ronen Eldan and Yuanzhi Li,
CDLA-Sharing-1.0) and WikiText-2 (Salesforce/Merity et al., CC-BY-SA-3.0
with upstream GFDL considerations). See `source/acquisition.json` for pinned
revisions and data provenance. The model may repeat, produce errors, or
hallucinate. No language quality, consciousness, novel physics, or production
safety is established by the checkpoint or its repository.

The inference snapshot excludes `training_state.pt` and any owner
credentials, private memory, and operational records. This publication
does not grant model tool authority.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", default=DEFAULT_REPO)
    parser.add_argument("--checkpoint", type=Path,
                        help="Optional pre-installed official 12K step directory")
    parser.add_argument("--public", action="store_true",
                        help="Explicitly publish publicly (default is a private repo)")
    parser.add_argument("--confirm", action="store_true",
                        help="Actually create/update the Hugging Face model repository")
    args = parser.parse_args()
    if args.repo_id != DEFAULT_REPO:
        parser.error("refusing non-owner repository; use the canonical phera-ra target")
    root = Path(__file__).resolve().parents[3]
    if not (root / "models/rawrphos/config/model.json").is_file():
        parser.error("run from the intact Beast Box repository checkout")
    token = os.environ.get("HF_TOKEN", "")
    if args.confirm and (len(token) < 20 or any(c in token for c in "\r\n")):
        parser.error("HF_TOKEN with model-repo write permission must be set privately")
    with tempfile.TemporaryDirectory(prefix="rawrphos-hf-") as temp:
        base = Path(temp)
        checkpoint = args.checkpoint or base / "checkpoint" / "step-00012000"
        # The installer verifies pinned public archive SHA, checkpoint manifest,
        # parameter identity, tokenizer and model metadata without reading RNG.
        installed_sha = install(checkpoint) if args.checkpoint is None else verify(checkpoint)
        if installed_sha != WEIGHT_SHA:
            raise ValueError("checkpoint hash mismatch")
        metadata = json.loads((checkpoint / "metadata.json").read_text())
        if (metadata.get("model_id") != "rawrphos-native"
                or metadata.get("lineage") != "native-from-scratch"
                or metadata.get("training_steps") != 12000):
            raise ValueError("incorrect checkpoint metadata")
        stage = base / "upload"
        stage.mkdir()
        digests = {}
        for rel in FILES:
            source = checkpoint / rel
            dest = stage / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            digests[rel] = sha256(dest)
        if digests["model.safetensors"] != WEIGHT_SHA:
            raise ValueError("staged model hash mismatch")
        for rel in SOURCE_FILES:
            source = root / rel
            dest = stage / "source" / (rel.removeprefix("models/rawrphos/"))
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            digests[str(dest.relative_to(stage))] = sha256(dest)
        (stage / "README.md").write_text(make_card(args.repo_id, metadata))
        (stage / "inference-manifest.json").write_text(
            json.dumps({"schema": "rawrphos-inference-snapshot-v1",
                        "model_id": "rawrphos-native", "training_steps": 12000,
                        "original_release": TAG, "checkpoint_sha256": WEIGHT_SHA,
                        "files": digests}, indent=2, sort_keys=True) + "\n"
        )
        if any(p.name == "training_state.pt" for p in stage.rglob("*")):
            raise ValueError("refusing to publish optimizer/RNG state")
        print(json.dumps({"repo_id": args.repo_id, "weight_sha256": installed_sha,
                          "files": sorted(p.as_posix()[len(str(stage))+1:]
                                          for p in stage.rglob("*") if p.is_file()),
                          "mode": "PUBLIC" if args.public else "PRIVATE",
                          "upload": "REQUESTED" if args.confirm else "DRY_RUN"},
                         indent=2))
        if not args.confirm:
            return
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        who = api.whoami()
        if who.get("name") != "phera-ra":
            raise PermissionError("the HF token is not for the expected owner account")
        api.create_repo(repo_id=args.repo_id, repo_type="model",
                        private=not args.public, exist_ok=True)
        commit = api.upload_folder(
            repo_id=args.repo_id, repo_type="model", folder_path=str(stage),
            commit_message="Publish verified native RAWRPHØS 12K inference snapshot"
        )
        print(json.dumps({"model_url": f"https://huggingface.co/{args.repo_id}",
                          "commit_url": getattr(commit, "commit_url", None),
                          "checkpoint_sha256": WEIGHT_SHA,
                          "hosted_inference": False}, indent=2))


if __name__ == "__main__":
    main()
