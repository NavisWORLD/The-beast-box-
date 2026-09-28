"""Verify and freeze a genuinely trained RAWRPHØS checkpoint for release.

This does not train, alter, promote, or overwrite any checkpoint.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tarfile

from rawrphos.inference.engine import Engine
from rawrphos.training.checkpoint import load_checkpoint, hash_file


def freeze(checkpoint: Path, output: Path, expected_step: int):
    if output.exists():
        raise FileExistsError(f"release staging directory already exists: {output}")
    loaded = load_checkpoint(checkpoint, require_trained=True, load_training_state=True)
    meta = loaded["metadata"]
    pinned = Path(__file__).resolve().parents[1]
    corpus = json.loads((pinned / "data/dataset_manifest.json").read_text())
    training = json.loads((pinned / "config/training.json").read_text())
    architecture = json.loads((pinned / "config/model.json").read_text())
    if meta["dataset_manifest_sha256"] != corpus["dataset_sha256"]:
        raise ValueError("training dataset differs from pinned corpus")
    if meta["training_config"] != training or meta["requested_model_config"] != architecture:
        raise ValueError("model/training configuration differs from committed configuration")
    if meta["training_steps"] != expected_step or expected_step < 1:
        raise ValueError("unexpected or untrained optimizer step count")
    if meta["parameter_count"] != 3_909_956:
        raise ValueError("native candidate parameter count differs")
    if meta["initial_parameter_sha256"] == meta["parameter_sha256"]:
        raise ValueError("parameters have not changed from initialization")
    validation = meta["validation_history"][-1]
    if validation["step"] != expected_step:
        raise ValueError("no held-out validation at requested checkpoint")
    for field in ("loss", "perplexity"):
        if not math.isfinite(validation[field]):
            raise ValueError(f"nonfinite held-out {field}")
    if not math.isfinite(meta["last_train_loss"]):
        raise ValueError("nonfinite training loss")
    source = meta["source"]
    if source["dirty"] is not False or source["commit"] != os.environ.get("GITHUB_SHA"):
        raise ValueError("checkpoint does not originate from this clean source commit")
    if "optimizer" not in loaded["state"] or "rng" not in loaded["state"] or "data_rng" not in loaded["state"]:
        raise ValueError("resume state is absent")

    sample = Engine(checkpoint, max_new_tokens=32, threads=4,
                    expected_sha256=meta["checkpoint_sha256"]).complete(
                        "Once upon a time,", max_tokens=32, temperature=0, timeout=90)
    output.mkdir(parents=True)
    archive = output / f"rawrphos-native-step-{expected_step:08d}.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(checkpoint, arcname=checkpoint.name, recursive=True)
    receipt = {
        "schema": "rawrphos-native-release-receipt-v1",
        "model_id": "rawrphos-native",
        "lineage": "native-from-scratch",
        "source_commit": source["commit"],
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "training_steps": expected_step,
        "training_tokens": meta["training_tokens"],
        "train_loss": meta["last_train_loss"],
        "heldout_validation": validation,
        "parameter_count": meta["parameter_count"],
        "initial_parameter_sha256": meta["initial_parameter_sha256"],
        "parameter_sha256": meta["parameter_sha256"],
        "checkpoint_sha256": meta["checkpoint_sha256"],
        "tokenizer_sha256": meta["tokenizer_sha256"],
        "dataset_manifest_sha256": meta["dataset_manifest_sha256"],
        "checkpoint_file_sha256": loaded["manifest"]["files"],
        "archive_filename": archive.name,
        "archive_sha256": hash_file(archive),
        "generated_text": sample,
        "generated_prompt": "Once upon a time,",
        "generation_settings": {"max_tokens": 32, "temperature": 0},
        "release_status": "trained-research-candidate-not-production",
        "limits": "Synthetic story corpus plus WikiText; held-out loss is not a capability or safety benchmark.",
    }
    receipt_path = output / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    (output / "SHA256SUMS").write_text(
        f"{hash_file(archive)}  {archive.name}\n{hash_file(receipt_path)}  receipt.json\n"
    )
    (output / "RELEASE_NOTES.md").write_text(
        "# RAWRPHØS native CPU checkpoint\n\n"
        f"Source commit: {source['commit']}\n\n"
        f"Optimizer steps: {expected_step}\n\n"
        f"Training tokens: {meta['training_tokens']}\n\n"
        f"Train loss: {meta['last_train_loss']:.6f}\n\n"
        f"Held-out validation loss: {validation['loss']:.6f}\n\n"
        f"Weight SHA-256: {meta['checkpoint_sha256']}\n\n"
        f"Archive SHA-256: {receipt['archive_sha256']}\n\n"
        "Includes CPU model, tokenizer, full optimizer/RNG resume state, metadata and hashes. "
        "Extract into an empty directory and call rawrphos.training.checkpoint.load_checkpoint "
        "on the step directory; it verifies the full manifest. The archive contains no private "
        "memory or provider credentials. Corpus: Ronen Eldan/Yuanzhi Li TinyStories "
        "(CDLA-Sharing-1.0) and Salesforce WikiText-2 (CC-BY-SA-3.0 / upstream GFDL); "
        "see models/rawrphos/data/acquisition.json for pinned source revisions and attribution. "
        "This is an experimental candidate, not a production or general-capability release.\n"
    )
    print(json.dumps(receipt, sort_keys=True, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-step", type=int, required=True)
    args = parser.parse_args()
    freeze(args.checkpoint, args.output, args.expected_step)
