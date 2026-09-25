"""Create a new, hash-bound data phase from original dialogue + audited supplemental data.

No source data is modified. Original validation remains separately addressable;
synthetic holdout is not confused with an independent capability benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from rawrphos.data.conversation import load_dataset, write_dataset
from rawrphos.data.corpus import canonical, sha
from rawrphos.scripts.prepare_broad_curriculum import CATEGORIES, VERSION

ORIGINAL_SHA = "7e9e8f91e751b3304663cb28293b2c90cc0e1623df355eb77dfdc6004cadcec5"
SUPPLEMENT_SHA = "4275abb30706826ab42d6e9e3c54d0c0a9de66fb43590d5b8660f0a2e8eb243d"
PROBE_PATH = Path(__file__).resolve().parents[1] / "evaluation/conversation/probes.json"
QUALITY_PROBES = Path(__file__).resolve().parents[1] / "evaluation/conversation/quality-21k-public-probes.json"


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold().strip())


def question(row):
    messages = row["messages"]
    if not messages or not isinstance(messages[-1], dict):
        raise ValueError("missing final conversation question")
    return normalized(messages[-1]["content"])


def read_supplement(folder: Path) -> tuple[list[dict], list[dict], dict]:
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    digest = manifest.pop("dataset_sha256")
    actual = hashlib.sha256(json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    if digest != actual or digest != SUPPLEMENT_SHA or manifest["schema"] != VERSION:
        raise ValueError("audited supplemental manifest mismatch")
    manifest["dataset_sha256"] = digest
    rows = []
    for split in ("train", "validation"):
        raw = (folder / (split + ".jsonl")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest["files"][split + ".jsonl"]:
            raise ValueError("supplemental file digest mismatch")
        parsed = [json.loads(line) for line in raw.splitlines() if line]
        if len(parsed) != manifest[split + "_examples"]:
            raise ValueError("supplemental row count mismatch")
        if any(r.get("category") not in CATEGORIES or
               r.get("license") != "LicenseRef-Beast-Box-Source-Available" or
               r.get("source") != VERSION for r in parsed):
            raise ValueError("supplemental row provenance mismatch")
        rows.append(parsed)
    return rows[0], rows[1], manifest


def build(original: Path, supplement: Path, output: Path) -> dict:
    old = load_dataset(original)
    if old["manifest"]["dataset_sha256"] != ORIGINAL_SHA:
        raise ValueError("original frozen conversation dataset mismatch")
    broad_train, broad_val, supplemental_manifest = read_supplement(supplement)
    original_train = list(old["train"])
    original_val = list(old["validation"])

    # Frozen public evaluation prompts must not become supplemental training examples.
    public = json.loads(QUALITY_PROBES.read_text())
    frozen = json.loads(PROBE_PATH.read_text())
    reserved = {normalized(row["prompt"]) for row in public["items"]}
    reserved.update(normalized(m["content"]) for p in frozen for m in p["messages"]
                    if m["role"] == "user")

    train_q = {question(r) for r in original_train}
    original_val_q = {question(r) for r in original_val}
    if train_q.intersection(original_val_q):
        raise ValueError("original train/validation question split is contaminated")
    reasons = Counter()
    selected_train = []
    for row in broad_train:
        key = question(row)
        if key in original_val_q or key in reserved:
            reasons["supplemental_train_reserved_or_original_validation"] += 1
            continue
        if key in train_q:
            reasons["supplemental_train_duplicate_original"] += 1
            continue
        train_q.add(key)
        selected_train.append(row)
    val_q = set(original_val_q)
    selected_val = []
    for row in broad_val:
        key = question(row)
        if key in train_q or key in reserved or key in val_q:
            reasons["supplemental_validation_overlap_or_reserved"] += 1
            continue
        selected_val.append(row)
        val_q.add(key)

    # The original validation bytes remain exactly the original split (copied
    # by content), never replaced with synthetic items.
    if len(original_val) != old["manifest"]["counts"]["validation"]:
        raise ValueError("original validation changed")
    train_cats = Counter(r["category"] for r in selected_train)
    val_cats = Counter(r["category"] for r in selected_val)
    if len(selected_train) < 600 or len(selected_val) < 50:
        raise ValueError("insufficient leak-free supplemental curriculum")
    if len(train_cats) < 27 or len(val_cats) < 25:
        raise ValueError("category coverage lost in split protection")

    all_train = original_train + selected_train
    all_validation = original_val + selected_val
    assert not {question(r) for r in all_train}.intersection(
        {question(r) for r in all_validation})
    train_ids = {sha(canonical({"messages": r["messages"], "reply": r["reply"]}))
                 for r in all_train}
    val_ids = {sha(canonical({"messages": r["messages"], "reply": r["reply"]}))
               for r in all_validation}
    if train_ids.intersection(val_ids):
        raise ValueError("identical train and validation conversations")
    provenance = {
        "phase": "rawrphos-broad-blend-v1",
        "base_dataset_sha256": ORIGINAL_SHA,
        "supplement_dataset_sha256": SUPPLEMENT_SHA,
        "base_provenance": old["manifest"]["provenance"],
        "supplement_license": supplemental_manifest["license"],
        "supplement_provenance": supplemental_manifest["provenance"],
        "mix_sampling": {
            "frozen_original_dialogue_mass": 0.80,
            "supplemental_category_uniform_mass": 0.20
        },
        "counts": {
            "base_train": len(original_train),
            "base_validation": len(original_val),
            "supplement_train": len(selected_train),
            "supplement_validation": len(selected_val),
        },
        "supplement_train_categories": dict(sorted(train_cats.items())),
        "supplement_validation_categories": dict(sorted(val_cats.items())),
        "cross_split_rejections": dict(reasons),
        "frozen_public_probes_sha256": sha(QUALITY_PROBES.read_bytes()),
        "quality_limitations": [
            "Synthetic short-form examples, some templated; do not infer broad reasoning ability.",
            "Existing source is synthetically generated public dialogue, not human conversation.",
            "Category-wise validation is tiny and separate from original heldout.",
            "Blended dataset is a NEW training phase, not same-data exact continuation."
        ],
        "personal_user_history_used": False,
        "private_sensor_or_quantum_data_used": False
    }
    manifest = write_dataset(output, all_train, all_validation, provenance)
    if manifest["counts"] != {"train": len(all_train), "validation": len(all_validation)}:
        raise ValueError("unexpected blended dataset count")
    (Path(output) / "blend-receipt.json").write_text(json.dumps({
        "schema": "rawrphos-broad-blend-receipt-v1",
        "dataset_sha256": manifest["dataset_sha256"],
        "original_sha256": ORIGINAL_SHA,
        "supplement_sha256": SUPPLEMENT_SHA,
        "original_validation_sha256": sha(
            b"".join(canonical(r) + b"\n" for r in original_val)),
        "counts": provenance["counts"],
        "cross_split_rejections": dict(reasons),
        "frozen_public_probes_sha256": provenance["frozen_public_probes_sha256"]
    }, indent=2, sort_keys=True) + "\n")
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--supplement", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = build(a.original, a.supplement, a.output)
    print(json.dumps({
        "dataset_sha256": result["dataset_sha256"],
        "counts": result["counts"],
        "supplemental_counts": result["provenance"]["counts"],
        "category_coverage": len(result["provenance"]["supplement_train_categories"]),
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
