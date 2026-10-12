#!/usr/bin/env python3
"""RAWRPHOS 012A: bounded adapter-only measurement-conditioning MECHANISM trial.

The source label is explicitly DERIVED from a measurement feature. Learning to
read it tests wiring, not a useful game policy, independent physical dimensions,
quantum advantage, or a meaningful quantum->conversation pairing. The approved
Zeref model, optimizer history, personas and user data remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F
from safetensors.torch import save_file
from rawrphos.training.checkpoint import parameter_hash, hash_file
from zeref_experiment_011 import load_parent, PARENT_SHA, ZEREF

TASK = "measurement_parity_median_readout_only"
ARMS = ("aligned_ibm", "shuffled_ibm", "independent_classical", "constant_classical")
PROMPT = (
    "User: A public measurement feature is attached as numerical state. "
    "For the training-median even-parity probability, report 1 when above "
    "the median, otherwise 0. Reply with only the digit.\nAssistant: "
)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_rows(file: Path, split: str) -> list[dict]:
    raw = file.read_bytes()
    if not raw:
        raise ValueError("Empty pinned corpus: " + str(file))
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    keys = set()
    for row in rows:
        if (row.get("schema") != "rawrphos-recorded-count-conditioning/v1"
                or row.get("role") != "STATE_CONDITIONING_ONLY"
                or row.get("source_class") != "RECORDED_IBM_HARDWARE"
                or row.get("split") != split
                or row.get("action_label") is not None
                or row.get("reward_label") is not None
                or row.get("dialogue_target") is not None
                or row.get("independent_physical_channels_claimed") is not False):
            raise ValueError("Unexpected source, label, or measurement claims")
        v = row.get("features")
        if (not isinstance(v, list) or len(v) != 12
                or any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 or x > 1 for x in v)):
            raise ValueError("Invalid conditioning feature vector")
        if not (isinstance(row.get("counts_sha256"), str) and len(row["counts_sha256"]) == 64):
            raise ValueError("Missing source digest")
        if row["run_key"] in keys:
            raise ValueError("Duplicate source key")
        keys.add(row["run_key"])
    return rows


def load_data(folder: Path):
    manifest_path = folder / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if (manifest.get("schema") != "rawrphos-quantum-conditioning-manifest/v1"
            or manifest.get("model_weights_updated") is not False
            or manifest.get("provider_jobs_submitted") != 0):
        raise ValueError("Untrusted source corpus manifest")
    expected = manifest["exports"]
    partitions = {}
    for split in ("train", "validation", "test"):
        filename = "ibm-" + split + ".jsonl"
        data = (folder / filename).read_bytes()
        if digest_bytes(data) != expected[filename]["sha256"]:
            raise ValueError("Corpus byte digest mismatch: " + filename)
        partitions[split] = read_rows(folder / filename, split)
    seen_jobs, seen_counts = {}, {}
    for split, rows in partitions.items():
        for row in rows:
            job = (row["backend"], row["job_id"])
            counts = row["counts_sha256"]
            if job in seen_jobs and seen_jobs[job] != split:
                raise ValueError("Job leaks across splits")
            if counts in seen_counts:
                raise ValueError("Duplicate count digest in candidate data")
            seen_jobs[job], seen_counts[counts] = split, split
    if sum(len(v) for v in partitions.values()) != manifest["snapshots"]["unique_count_candidates"]["rows"]:
        raise ValueError("Corpus candidate census changed")
    return partitions, digest_bytes(manifest_bytes), manifest


def label_from_feature(features, threshold: float) -> int:
    return int(features[6] > threshold)


def balanced(rows: list, threshold: float, n_per_class: int, seed: int):
    rng = random.Random(seed)
    bins = [[r for r in rows if label_from_feature(r["features"], threshold) == k] for k in (0, 1)]
    if min(map(len, bins)) < n_per_class:
        raise ValueError("Insufficient distinct examples per label")
    picked = rng.sample(bins[0], n_per_class) + rng.sample(bins[1], n_per_class)
    rng.shuffle(picked)
    return picked


def classical_features(key: str) -> list[float]:
    # A deterministic, independent SHA256-based classical control, not a QVM.
    out = []
    for block in (0, 1):
        raw = hashlib.sha256(("control012|" + key + "|" + str(block)).encode()).digest()
        out.extend(int.from_bytes(raw[i:i + 4], "big") / 4294967295 for i in range(0, 24, 4))
    return out[:12]


def arm_rows(rows, arm, seed):
    if arm == "aligned_ibm":
        return [r["features"] for r in rows]
    if arm == "constant_classical":
        return [[.25] * 12 for _ in rows]
    if arm == "independent_classical":
        return [classical_features(r["run_key"]) for r in rows]
    if arm == "shuffled_ibm":
        order = list(range(len(rows)))
        random.Random(seed + 59).shuffle(order)
        if len(rows) > 1 and order == list(range(len(rows))):
            order = order[1:] + order[:1]
        return [rows[i]["features"] for i in order]
    raise ValueError("Unknown arm")


def feature_tensor(features):
    tensor = torch.tensor(features, dtype=torch.float32)
    if tensor.ndim != 2 or tensor.shape[1] != 12 or not bool(torch.isfinite(tensor).all()):
        raise ValueError("Invalid feature tensor")
    return tensor.mul(2).sub(1)


class StateConditionAdapter(nn.Module):
    """A zero-impact 12->32->12 external control; parent weights stay frozen."""
    def __init__(self):
        super().__init__()
        self.project = nn.Sequential(nn.Linear(12, 32), nn.Tanh(), nn.Linear(32, 12))
        nn.init.zeros_(self.project[-1].weight)
        nn.init.zeros_(self.project[-1].bias)

    def forward(self, features):
        return torch.tanh(self.project(feature_tensor(features)))


def evaluation(model, adapter, ids, class_ids, rows, arm, median, seed, batch_size=8):
    model.eval()\n    if adapter is not None:\n        adapter.eval()
    targets = [label_from_feature(r["features"], median) for r in rows]
    features = arm_rows(rows, arm, seed)
    predictions = []
    total_loss = 0.
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            chunk = features[start:start + batch_size]
            y = torch.tensor(targets[start:start + batch_size], dtype=torch.long)
            inp = ids.expand(len(chunk), -1)
            controls = None if adapter is None else adapter(chunk)
            logits = model(inp, control_vector=controls)["logits"][:, -1, class_ids]
            loss = F.cross_entropy(logits.float(), y, reduction="sum")
            total_loss += float(loss)
            predictions.extend(logits.argmax(-1).tolist())
    correct = sum(a == b for a, b in zip(predictions, targets))
    return {"rows": len(rows), "accuracy": round(correct / len(rows), 6),
            "balanced_accuracy": round(sum(
                (sum(predictions[i] == k for i, y in enumerate(targets) if y == k)
                 / sum(y == k for y in targets)) for k in (0, 1)) / 2, 6),
            "two_class_nll": round(total_loss / len(rows), 6)}


def experiment(parent: Path, corpus: Path, out: Path, steps: int = 32,
               seed: int = 20261012, threads: int = 2,
               train_per_class: int = 48, eval_per_class: int = 12):
    if not 1 <= steps <= 128 or not 1 <= threads <= 8:
        raise ValueError("CPU trial bounds violated")
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(seed); random.seed(seed)
    parts, manifest_sha, manifest = load_data(corpus)
    threshold = float(sorted(r["features"][6] for r in parts["train"])[len(parts["train"]) // 2])
    train = balanced(parts["train"], threshold, train_per_class, seed)
    validation = balanced(parts["validation"], threshold, eval_per_class, seed + 101)
    test = balanced(parts["test"], threshold, eval_per_class, seed + 201)
    parent_bundle = load_parent(parent)
    model, tok = parent_bundle["model"], parent_bundle["tokenizer"]
    actual_hash = parameter_hash(model)
    if actual_hash != parent_bundle["metadata"]["parameter_sha256"]:
        raise ValueError("Approved parent parameter identity mismatch")
    for param in model.parameters():
        param.requires_grad_(False)
    model.eval()
    ids = torch.tensor([tok.encode(PROMPT, add_bos=True)], dtype=torch.long)
    zeros, ones = tok.encode("0"), tok.encode("1")
    if len(zeros) != 1 or len(ones) != 1 or zeros == ones:
        raise ValueError("Classification token boundary changed")
    class_ids = [zeros[0], ones[0]]
    test_features = feature_tensor([r["features"] for r in test[:2]])
    sanity_adapter = StateConditionAdapter()
    with torch.no_grad():
        if not torch.equal(sanity_adapter.project[-1](sanity_adapter.project[1](
                sanity_adapter.project[0](test_features))), torch.zeros(2, 12)):
            raise AssertionError("Conditioning adapter is nonzero at initialization")
        base_logits = model(ids)["logits"]
        zero_logits = model(ids, control_vector=sanity_adapter([r["features"] for r in test[:1]]))["logits"]
        if not torch.equal(base_logits, zero_logits):
            raise AssertionError("Adapter was not zero-impact at initialization")

    results = {}
    base = evaluation(model, None, ids, class_ids, test, "aligned_ibm", threshold, seed)
    out.mkdir(parents=True, exist_ok=False)
    for arm in ARMS:
        torch.manual_seed(seed)
        adapter = StateConditionAdapter()
        initial = {k: v.detach().clone() for k, v in adapter.state_dict().items()}
        opt = torch.optim.AdamW(adapter.parameters(), lr=.006, weight_decay=.0)
        trfeatures = arm_rows(train, arm, seed)
        train_labels = [label_from_feature(r["features"], threshold) for r in train]
        losses = []
        for step in range(steps):
            # Uniform class balance with deterministic batch permutation.
            start = (step * 8) % len(train)
            indices = [(start + i) % len(train) for i in range(8)]
            fb = [trfeatures[i] for i in indices]
            y = torch.tensor([train_labels[i] for i in indices], dtype=torch.long)
            opt.zero_grad(set_to_none=True)
            logits = model(ids.expand(len(indices), -1),
                           control_vector=adapter(fb))["logits"][:, -1, class_ids]
            loss = F.cross_entropy(logits.float(), y)
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("Nonfinite model loss")
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(adapter.parameters(), 1., error_if_nonfinite=True)
            if not bool(torch.isfinite(norm)):
                raise FloatingPointError("Nonfinite adapter gradient")
            opt.step()
            if (step + 1) % 8 == 0 or step == 0:
                losses.append({"update": step + 1, "loss": round(float(loss), 6),
                               "grad_norm": round(float(norm), 6)})
        if all(torch.equal(value, initial[k]) for k, value in adapter.state_dict().items()):
            raise AssertionError("Adapter did not learn: " + arm)
        weights = out / ("adapter-" + arm + ".safetensors")
        save_file({k: v.detach().contiguous() for k, v in adapter.state_dict().items()}, str(weights))
        results[arm] = {
            "train_losses": losses,
            "validation": evaluation(model, adapter, ids, class_ids, validation, arm, threshold, seed + 101),
            "test": evaluation(model, adapter, ids, class_ids, test, arm, threshold, seed + 201),
            "adapter_sha256": hash_file(weights),
            "adapter_parameters": sum(p.numel() for p in adapter.parameters()),
        }
    if parameter_hash(model) != actual_hash or actual_hash != parent_bundle["metadata"]["parameter_sha256"]:
        raise AssertionError("Approved parent weights were modified")
    with torch.no_grad():
        if not torch.equal(model(ids)["logits"], base_logits):
            raise AssertionError("Frozen parent's unconditioned language logits changed")
    report = {
        "schema": "zeref-012a-conditioner-mechanism/v1",
        "mode": "ADAPTER_ONLY_MECHANISM_NOT_GAME_IMPROVEMENT",
        "research_qbeast_id": ZEREF,
        "parent_checkpoint_sha256": PARENT_SHA,
        "parent_parameter_sha256": actual_hash,
        "model_weights_updated": False,
        "parent_optimizer_state_unchanged": True,
        "model_promoted": False,
        "new_provider_jobs": 0,
        "private_user_conversations_included": False,
        "corpus_manifest_sha256": manifest_sha,
        "source_snapshot": manifest["snapshots"],
        "split_counts": manifest["split_counts"],
        "label_definition": "1 if measured even-parity probability feature > training-only median, else 0",
        "label_already_encoded_in_input": True,
        "signal_claim_allowed": False,
        "quantum_advantage_claimed": False,
        "task": TASK,
        "median_train_only": threshold,
        "steps_per_arm": steps,
        "training_rows_sampled": len(train),
        "held_out_test_rows": len(test),
        "seed": seed,
        "baseline_without_adapter_test": base,
        "adapter_initial_zero_impact": True,
        "unconditioned_parent_logits_bit_identical": True,
        "results": results,
        "limitations": [
            "This is an intentionally trivial sensor readout mechanism test, not evidence of improved dialogue or navigation.",
            "The target is computed from one input feature; this checks plumbing, not independent quantum predictive signal.",
            "Controls match training schedule; aligned and shuffled performance is not a hardware advantage test.",
            "Base Zeref parameters and memory remain unchanged; only separate adapter weights were optimized.",
            "The 12D vector is a classical transform of recorded counts, not 12 independent quantum measurements.",
        ],
    }
    (out / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print("ZEREF_012A_REPORT=" + json.dumps({
        "parent_unchanged": True, "baseline": base,
        "arms": {arm: r["test"] for arm, r in results.items()},
        "report_sha256": hash_file(out / "report.json")}, sort_keys=True), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("build/rawrphos-quantum-conditioning"))
    parser.add_argument("--out", type=Path, default=Path("build/zeref-012a-mechanism"))
    parser.add_argument("--steps", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    experiment(args.parent, args.corpus, args.out, steps=args.steps, seed=args.seed, threads=args.threads)


if __name__ == "__main__":
    main()
