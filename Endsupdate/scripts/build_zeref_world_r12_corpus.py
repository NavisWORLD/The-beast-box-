#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from scripts.build_zeref_world_knowledge import first_factual_sentence


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _compact_title(title: str, max_chars: int = 28) -> str:
    clean = " ".join(str(title).split())
    if len(clean) <= max_chars:
        return clean
    prefix = clean[: max_chars + 1]
    cut = prefix.rfind(" ")
    if cut < 8:
        cut = max_chars
    return clean[:cut].rstrip(" ,;:-")


def _world_row(source: dict[str, Any]) -> dict[str, Any] | None:
    fact = first_factual_sentence(str(source.get("text") or ""), max_chars=34)
    title = _compact_title(str(source.get("title") or ""))
    if not fact or not title or len(fact.split()) < 3:
        return None
    dad = f"K:{fact} Q:{title}?"
    zeref = fact
    if len(dad) + len(zeref) + 14 > 128:
        return None
    return {
        "schema": "zeref-world-r12-dialogue-v1",
        "dad": dad,
        "zeref": zeref,
        "namespace": "world",
        "knowledge_id": int(source["knowledge_id"]),
        "source_dataset": str(source["source_dataset"]),
        "source_id": str(source["source_id"]),
        "source_url": str(source.get("source_url") or ""),
        "source_sha256": str(source["source_sha256"]),
        "license_label": str(source["license_label"]),
        "revision_label": str(source["revision_label"]),
        "raw_model_output_used_as_target": False,
        "source_derived_target": True,
        "teacher_target_reviewed_clean": True,
    }


def _uncertainty_row(evidence: dict[str, Any], question: dict[str, Any], index: int) -> dict[str, Any] | None:
    fact = first_factual_sentence(str(evidence.get("text") or ""), max_chars=34)
    title = _compact_title(str(question.get("title") or ""))
    if not fact or not title:
        return None
    dad = f"K:{fact} Q:{title}?"
    zeref = "Not enough evidence."
    if len(dad) + len(zeref) + 14 > 128:
        return None
    return {
        "schema": "zeref-world-r12-dialogue-v1",
        "dad": dad,
        "zeref": zeref,
        "namespace": "none",
        "negative_pair_index": int(index),
        "evidence_source_id": str(evidence["source_id"]),
        "question_source_id": str(question["source_id"]),
        "raw_model_output_used_as_target": False,
        "source_derived_target": False,
        "teacher_target_reviewed_clean": True,
        "uncertainty_target": True,
    }


def _build_negative_pairs(pool: list[dict[str, Any]], count: int, *, offset: int = 0) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if count <= 0:
        return result
    if len(pool) < 2:
        raise ValueError("uncertainty pairs require at least two source records")
    for index in range(count):
        left = pool[(offset + index) % len(pool)]
        right = pool[(offset + index + 1) % len(pool)]
        if left["source_id"] == right["source_id"]:
            right = pool[(offset + index + 2) % len(pool)]
        row = _uncertainty_row(left, right, index + 1)
        if row is not None:
            result.append(row)
    if len(result) != count:
        raise ValueError(f"could not build requested uncertainty rows: {len(result)} != {count}")
    return result


def build_world_curriculum(
    *,
    world_evidence: Path,
    out_dir: Path,
    train_facts: int,
    holdout_facts: int,
    uncertainty_rows: int,
    uncertainty_holdout_rows: int = 0,
    seed: int,
) -> dict[str, Any]:
    evidence = [json.loads(line) for line in world_evidence.read_text(encoding="utf-8").splitlines() if line.strip()]
    source_rows = [row for row in evidence if row.get("schema") == "zeref-world-knowledge-record-v1"]
    usable = [(source, _world_row(source)) for source in source_rows]
    usable = [(source, row) for source, row in usable if row is not None]
    required = int(train_facts) + int(holdout_facts)
    if required <= 0 or len(usable) < required:
        raise ValueError(f"not enough usable world facts: need {required}, found {len(usable)}")
    if int(uncertainty_rows) < 0 or int(uncertainty_holdout_rows) < 0:
        raise ValueError("uncertainty row counts must be non-negative")

    rng = random.Random(int(seed))
    rng.shuffle(usable)
    train_pairs = usable[: int(train_facts)]
    holdout_pairs = usable[int(train_facts) : required]
    train = [dict(row) for _, row in train_pairs]
    holdout = [dict(row) for _, row in holdout_pairs]

    train_pool = [source for source, _ in train_pairs]
    holdout_pool = [source for source, _ in holdout_pairs]
    uncertainty = _build_negative_pairs(train_pool, int(uncertainty_rows))
    uncertainty_holdout = _build_negative_pairs(holdout_pool, int(uncertainty_holdout_rows), offset=3)
    train.extend(uncertainty)

    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "train.jsonl"
    holdout_path = out_dir / "holdout.jsonl"
    uncertainty_holdout_path = out_dir / "uncertainty-holdout.jsonl"
    _write_jsonl(train_path, train)
    _write_jsonl(holdout_path, holdout)
    _write_jsonl(uncertainty_holdout_path, uncertainty_holdout)
    manifest = {
        "schema": "zeref-world-r12-corpus-manifest-v1",
        "seed": int(seed),
        "world_evidence_sha256": _sha(world_evidence),
        "world_source_records": len(source_rows),
        "usable_source_records": len(usable),
        "world_train_facts": int(train_facts),
        "world_holdout_facts": int(holdout_facts),
        "uncertainty_train_rows": int(uncertainty_rows),
        "uncertainty_holdout_rows": int(uncertainty_holdout_rows),
        "train_rows": len(train),
        "holdout_rows": len(holdout),
        "train_sha256": _sha(train_path),
        "holdout_sha256": _sha(holdout_path),
        "uncertainty_holdout_sha256": _sha(uncertainty_holdout_path),
        "raw_model_outputs_are_targets": False,
        "world_targets_source_derived": True,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world-evidence", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--train-facts", type=int, default=384)
    parser.add_argument("--holdout-facts", type=int, default=96)
    parser.add_argument("--uncertainty-rows", type=int, default=64)
    parser.add_argument("--uncertainty-holdout-rows", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260827)
    args = parser.parse_args()
    result = build_world_curriculum(
        world_evidence=args.world_evidence,
        out_dir=args.out_dir,
        train_facts=args.train_facts,
        holdout_facts=args.holdout_facts,
        uncertainty_rows=args.uncertainty_rows,
        uncertainty_holdout_rows=args.uncertainty_holdout_rows,
        seed=args.seed,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
