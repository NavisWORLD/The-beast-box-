from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.training.lineage import build_parent_manifest, verify_parent_manifest, write_canonical_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze and verify an immutable Zeref parent-lineage manifest")
    parser.add_argument("--model-id", default="zeref-genesis-baseline")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--tokenizer")
    parser.add_argument("--memory-ledger")
    parser.add_argument("--expected-checkpoint-sha256")
    parser.add_argument("--expected-architecture-sha256")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.out.exists():
        raise FileExistsError(f"genesis manifest already exists: {args.out}")

    manifest = build_parent_manifest(
        model_id=args.model_id,
        checkpoint_path=args.checkpoint,
        architecture_path=args.architecture,
        tokenizer_path=args.tokenizer,
        memory_ledger_path=args.memory_ledger,
        root=args.root,
        expected_checkpoint_sha256=args.expected_checkpoint_sha256,
        expected_architecture_sha256=args.expected_architecture_sha256,
    )
    manifest_sha256 = write_canonical_json(args.out, manifest)
    verification = verify_parent_manifest(manifest, root=args.root)
    summary = {**verification, "manifest_path": str(args.out), "manifest_sha256": manifest_sha256}
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
