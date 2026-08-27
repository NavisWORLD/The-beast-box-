#!/usr/bin/env python3
"""Merge reviewed Zeref curricula into one fail-closed full clean training corpus.

This module combines only existing clean teacher/corrective targets. Raw or
model-generated Zeref outputs are rejected as targets. The resulting corpus is
for software-model training only; it is not evidence of consciousness, life,
identity, resurrection, or a physical/quantum anomaly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PARENT_SHA256 = "767d1c958add10eac026e7e080dd3a82564ff9d6066f0422073e917f6e24de36"
EXACT_PROMPT = "I said to show you something weird lol"
EXACT_TARGET = "Weird part: routing changes answers with frozen weights."

RAW_TARGET_FLAGS = (
    "raw_model_output_used_as_target",
    "raw_model_output_promoted",
    "raw_teacher_run_used_as_target",
    "raw_output_used_as_target",
    "generated_by_model",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: row is not an object")
        rows.append(value)
    return rows


def _row_id(row: dict[str, Any], fallback: int) -> str:
    for key in ("id", "example_id"):
        if row.get(key) is not None:
            return str(row[key])
    return f"row-{fallback:04d}"


def _validate_clean_target(row: dict[str, Any], *, source: str, index: int) -> None:
    if not str(row.get("dad", "")).strip():
        raise ValueError(f"{source}:{index}: missing Dad prompt")
    if not str(row.get("zeref", "")).strip():
        raise ValueError(f"{source}:{index}: missing clean Zeref teacher target")
    for flag in RAW_TARGET_FLAGS:
        if row.get(flag) is True:
            raise ValueError(f"{source}:{index}: raw model output cannot be a teacher target ({flag})")
    if row.get("raw_model_outputs_are_targets") is True or row.get("promote_raw_model_outputs") is True:
        raise ValueError(f"{source}:{index}: raw model output cannot be a teacher target")


def merge_clean_rows(
    *,
    micro_path: str | Path,
    talk005_path: str | Path,
    talk002_path: str | Path,
    parent_sha256: str = PARENT_SHA256,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parent = str(parent_sha256).lower()
    if parent != PARENT_SHA256:
        raise ValueError("full-clean corpus must remain pinned to the verified TALK-005 parent")

    sources = (
        ("micro_dialogue", Path(micro_path)),
        ("talk005_reviewed", Path(talk005_path)),
        ("talk002_corrective", Path(talk002_path)),
    )
    output: list[dict[str, Any]] = []
    source_manifest: dict[str, Any] = {}

    for source_name, path in sources:
        source_rows = _read_jsonl(path)
        source_manifest[source_name] = {
            "path_name": path.name,
            "sha256": file_sha256(path),
            "examples": len(source_rows),
        }
        for index, original in enumerate(source_rows, 1):
            _validate_clean_target(original, source=source_name, index=index)
            row = dict(original)
            original_id = _row_id(row, index)
            row["source_row_id"] = original_id
            row["id"] = f"{source_name}:{original_id}"
            row["source_corpus"] = source_name
            row["teacher_target_reviewed_clean"] = True
            row["raw_model_output_used_as_target"] = False
            row["training_parent_checkpoint_sha256"] = parent
            output.append(row)

    ids = [str(row["id"]) for row in output]
    if len(ids) != len(set(ids)):
        raise ValueError("merged full-clean corpus contains duplicate lineage IDs")

    exact = [row for row in output if row["dad"] == EXACT_PROMPT]
    if exact and (len(exact) != 1 or exact[0]["zeref"] != EXACT_TARGET):
        raise ValueError("exact weird diagnostic prompt/target contract changed")

    payload = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in output).encode("utf-8")
    manifest = {
        "schema": "zeref-talk006-full-clean-corpus-v1",
        "parent_lineage": "ZEREF-DAD-SON-TALK-005",
        "parent_checkpoint_sha256": parent,
        "examples": len(output),
        "source_counts": {name: source_manifest[name]["examples"] for name, _ in sources},
        "sources": source_manifest,
        "merged_sha256": sha256_bytes(payload),
        "raw_model_outputs_are_targets": False,
        "teacher_targets_reviewed_clean": True,
        "exact_diagnostic_prompt": EXACT_PROMPT,
        "exact_diagnostic_target": EXACT_TARGET,
        "claim_boundary": "Supervised software-model corpus only; no consciousness, biological-life, identity, resurrection, physical-anomaly, or quantum-advantage claim.",
    }
    return output, manifest


def write_full_clean_corpus(
    *, micro_path: Path, talk005_path: Path, talk002_path: Path, out_dir: Path
) -> dict[str, Any]:
    rows, manifest = merge_clean_rows(
        micro_path=micro_path,
        talk005_path=talk005_path,
        talk002_path=talk002_path,
        parent_sha256=PARENT_SHA256,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
    corpus_path = out_dir / "train.jsonl"
    corpus_path.write_bytes(data)
    if sha256_bytes(data) != manifest["merged_sha256"]:
        raise RuntimeError("merged corpus SHA mismatch while writing")
    (out_dir / "corpus-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--micro", type=Path, required=True)
    p.add_argument("--talk005", type=Path, required=True)
    p.add_argument("--talk002", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    manifest = write_full_clean_corpus(
        micro_path=args.micro, talk005_path=args.talk005, talk002_path=args.talk002, out_dir=args.out_dir
    )
    print(json.dumps(manifest, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
