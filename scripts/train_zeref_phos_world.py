#!/usr/bin/env python3
"""Train one verified Zeref-PHOS world-model descendant generation offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping, Sequence

from beastbox.hashutil import canonical_json
from beastbox.training.lineage import verify_parent_manifest
from beastbox.training.phos_descendant import parameter_sha256
from beastbox.training.world_runner import train_descendant_generation
from scripts.run_zeref_dad_son_chat import _load_model


def _json_object(path: str | Path, *, label: str) -> dict[str, Any]:
    target = Path(path)
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must contain valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _artifact_entry(manifest: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise ValueError("parent manifest artifacts must be an object")
    entry = artifacts.get(name)
    if not isinstance(entry, Mapping):
        raise ValueError(f"parent manifest requires {name} artifact")
    stored_path = entry.get("path")
    recorded_sha = entry.get("sha256")
    if not isinstance(stored_path, str) or not stored_path.strip():
        raise ValueError(f"parent manifest {name} path must be non-empty")
    if not isinstance(recorded_sha, str) or len(recorded_sha) != 64:
        raise ValueError(f"parent manifest {name} SHA-256 is invalid")
    return entry


def _artifact_path(manifest: Mapping[str, Any], name: str, *, root: str | Path) -> Path:
    entry = _artifact_entry(manifest, name)
    stored_path = str(entry["path"])
    raw = Path(stored_path)
    if raw.is_absolute() or PureWindowsPath(stored_path).is_absolute():
        raise ValueError(f"parent artifact path must be relative to root: {stored_path}")
    base = Path(root).resolve()
    candidate = (base / raw).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"parent artifact path is outside root: {stored_path}") from exc
    return candidate


def _checkpoint_inputs(checkpoint: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    raw_config = checkpoint.get("config")
    raw_tokenizer = checkpoint.get("stoi")
    if not isinstance(raw_config, Mapping):
        raise ValueError("historical parent checkpoint config is missing")
    if not isinstance(raw_tokenizer, Mapping):
        raise ValueError("historical parent checkpoint tokenizer is missing")
    config = {str(key): value for key, value in raw_config.items()}
    tokenizer: dict[str, int] = {}
    for character, index in raw_tokenizer.items():
        if isinstance(index, bool) or not isinstance(index, int):
            raise ValueError("historical parent tokenizer ids must be integers")
        tokenizer[str(character)] = index
    return config, tokenizer


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a frozen historical Zeref parent, load it through the existing "
            "SparkCST loader, and train one sealed PHOS descendant generation offline."
        )
    )
    parser.add_argument("--parent-manifest", required=True)
    parser.add_argument("--parent-root", required=True)
    parser.add_argument("--lexical-manifest", required=True)
    parser.add_argument("--lexical-root", required=True)
    parser.add_argument("--world-manifest", required=True)
    parser.add_argument("--world-root", required=True)
    parser.add_argument("--quantum-receipt", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--generation-id", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    parent_manifest = _json_object(args.parent_manifest, label="parent manifest")
    verify_parent_manifest(parent_manifest, root=args.parent_root)
    checkpoint_entry = _artifact_entry(parent_manifest, "checkpoint")
    architecture_entry = _artifact_entry(parent_manifest, "architecture")
    checkpoint_path = _artifact_path(parent_manifest, "checkpoint", root=args.parent_root)
    architecture_path = _artifact_path(parent_manifest, "architecture", root=args.parent_root)

    checkpoint, parent_model = _load_model(checkpoint_path, architecture_path)
    if not isinstance(checkpoint, Mapping):
        raise ValueError("historical parent checkpoint must be an object")
    parent_config, tokenizer = _checkpoint_inputs(checkpoint)
    parent_parameter_sha = parameter_sha256(parent_model)

    lexical_manifest = _json_object(args.lexical_manifest, label="lexical manifest")
    world_manifest = _json_object(args.world_manifest, label="world manifest")
    quantum_receipt = _json_object(args.quantum_receipt, label="quantum control receipt")
    config = _json_object(args.config, label="training config")

    run_manifest = train_descendant_generation(
        parent_model=parent_model,
        parent_config=parent_config,
        tokenizer=tokenizer,
        parent_checkpoint_sha256=str(checkpoint_entry["sha256"]),
        parent_architecture_sha256=str(architecture_entry["sha256"]),
        expected_parent_parameter_sha256=parent_parameter_sha,
        lexical_manifest=lexical_manifest,
        lexical_root=args.lexical_root,
        world_manifest=world_manifest,
        world_root=args.world_root,
        quantum_receipt=quantum_receipt,
        config=config,
        output_dir=args.out,
        generation_id=args.generation_id,
    )
    print(canonical_json(run_manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
