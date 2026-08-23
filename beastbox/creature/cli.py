from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .bridges import classical_receipt
from .doctor import doctor_project
from .gguf import export_gguf
from .project import create_creature_project
from .weights import build_weight_manifest, inspect_weight


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cosmos-creature",
        description="Create, inspect, and verify COSMOS Creature projects without exposing cloud credentials.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="create a new creature project")
    create.add_argument("name")
    create.add_argument("--root", default=".")

    doctor = sub.add_parser("doctor", help="validate a creature project")
    doctor.add_argument("path")

    weights = sub.add_parser("weights", help="inspect and package model weights")
    weight_sub = weights.add_subparsers(dest="weight_command", required=True)
    inspect = weight_sub.add_parser("inspect")
    inspect.add_argument("file")
    manifest = weight_sub.add_parser("manifest")
    manifest.add_argument("file")
    manifest.add_argument("--architecture")
    manifest.add_argument("--quantization")
    manifest.add_argument("--tokenizer")
    manifest.add_argument("--source-checkpoint")
    manifest.add_argument("--license", dest="license_name")
    manifest.add_argument("--provenance")
    manifest.add_argument("--converter")
    manifest.add_argument("--output")
    convert = weight_sub.add_parser("export-gguf")
    convert.add_argument("source")
    convert.add_argument("output")
    convert.add_argument("--converter", nargs="+")

    bridge = sub.add_parser("bridge", help="emit sanitized bridge receipts")
    bridge_sub = bridge.add_subparsers(dest="bridge_command", required=True)
    classical = bridge_sub.add_parser("classical")
    classical.add_argument("--seed", type=int, required=True)
    classical.add_argument("--ttl", type=int, default=3600)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "create":
        root = create_creature_project(args.name, args.root)
        _print({"root": str(root), "manifest": str(root / "creature.json")})
        return 0
    if args.command == "doctor":
        result = doctor_project(args.path)
        _print(result)
        return 0 if result["ok"] else 1
    if args.command == "weights":
        if args.weight_command == "inspect":
            _print(inspect_weight(args.file))
            return 0
        if args.weight_command == "manifest":
            value = build_weight_manifest(
                args.file,
                architecture=args.architecture,
                quantization=args.quantization,
                tokenizer=args.tokenizer,
                source_checkpoint=args.source_checkpoint,
                license_name=args.license_name,
                provenance=args.provenance,
                converter=args.converter,
            )
            if args.output:
                path = Path(args.output)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            _print(value)
            return 0
        if args.weight_command == "export-gguf":
            path = export_gguf(args.source, args.output, converter=args.converter)
            _print(inspect_weight(path))
            return 0
    if args.command == "bridge" and args.bridge_command == "classical":
        _print(classical_receipt(args.seed, ttl_seconds=args.ttl).to_dict())
        return 0
    raise RuntimeError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
