"""Immutable, verified measurement snapshots. No training, gate, or promotion policy here."""
import argparse
import json
import os
import shutil
from pathlib import Path


def save_snapshot(root, model, tokenizer, parent, optimizer, generator, *, candidate, attempted, applied, state=None):
    from rawrphos.training.checkpoint import save_checkpoint, rng_state
    root = Path(root)
    label = "baseline" if candidate is None else f"candidate-{candidate}"
    relative = f"recovery/{label}-{attempted:06d}"
    names = {id(p): name for name, p in model.named_parameters()}
    groups = ([[names[id(p)] for p in g["params"]] for g in optimizer.param_groups]
              if optimizer is not None else parent.get("optimizer_group_param_names"))
    metadata = {"schema": "zeref-measurement-recovery-v1", "qbeast_id": "bb-deada969",
                "parent_checkpoint_sha256": parent["checkpoint_sha256"],
                "training_steps": parent["training_steps"] + applied,
                "production_promoted": False, "optimizer_group_param_names": groups}
    if state is None:
        state = {"optimizer": optimizer.state_dict(), "rng": rng_state(), "data_rng": generator.get_state()}
    saved = save_checkpoint(root / relative, model, tokenizer, metadata, state)
    progress = {"schema": "zeref-measurement-progress-v1", "checkpoint": relative,
                "checkpoint_sha256": saved["checkpoint_sha256"], "candidate": candidate,
                "attempted_updates": attempted, "applied_optimizer_steps": applied,
                "parent_checkpoint_sha256": parent["checkpoint_sha256"],
                "status": "candidate_not_started" if candidate is None else "candidate_in_progress"}
    # Publish the pointer only after checkpoint fsync + atomic rename has completed.
    temporary = root / "recovery-progress.json.tmp"
    with temporary.open("w") as handle:
        json.dump(progress, handle, sort_keys=True, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(root / "recovery-progress.json")
    print("ZEREF_ROUND_SNAPSHOT=" + json.dumps(progress, sort_keys=True), flush=True)
    return progress


def load_snapshot(root):
    from rawrphos.training.checkpoint import load_checkpoint
    root = Path(root)
    progress = json.loads((root / "recovery-progress.json").read_text())
    attempted, applied = progress["attempted_updates"], progress["applied_optimizer_steps"]
    if type(attempted) is not int or type(applied) is not int or not 0 <= applied <= attempted:
        raise ValueError("invalid recovery update counts")
    relative = Path(progress["checkpoint"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("invalid recovery checkpoint path")
    checkpoint = load_checkpoint(root / relative,
                                 expected_checkpoint_sha256=progress["checkpoint_sha256"],
                                 load_training_state=True)
    if checkpoint["metadata"].get("parent_checkpoint_sha256") != progress["parent_checkpoint_sha256"]:
        raise ValueError("recovery parent mismatch")
    return checkpoint, progress


def prepare_bundle(root, parent_path, destination):
    """Copy only latest complete snapshot + public inputs. NEVER copy private chat/teacher text."""
    root, parent_path, destination = Path(root), Path(parent_path), Path(destination)
    _, progress = load_snapshot(root)  # verify before sharing with the independent scorer
    out = destination / "zeref-006"
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(root / progress["checkpoint"], out / "recovery-checkpoint")
    progress["checkpoint"] = "recovery-checkpoint"
    (out / "recovery-progress.json").write_text(json.dumps(progress, sort_keys=True, indent=2))
    shutil.copytree(parent_path, out / "previous" / "accepted-checkpoint")
    shutil.copy2(parent_path.parent / "approval.json", out / "previous" / "approval.json")
    shutil.copytree(root / "inputs", out / "inputs")
    reference = root.parent / "public-14k"
    if reference.is_dir():
        shutil.copytree(reference, destination / "public-14k")
    # Spark input is public SIMULATED evidence, not a private sensor or transcript.
    ticks = root / "spark-ticks.jsonl"
    if ticks.is_file():
        shutil.copy2(ticks, out / ticks.name)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-bundle", action="store_true", required=True)
    args = parser.parse_args()
    prepare_bundle("build/zeref-006", os.environ["BEAST_006_PARENT_PATH"], "build/zeref-recovery-bundle")
