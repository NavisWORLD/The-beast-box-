#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = KIT_ROOT.parents[1]
for path in (str(KIT_ROOT), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from soul_qbt_final_kit import (  # noqa: E402
    execute_run,
    load_recovered,
    recover_to_jsonl,
    sample_qbt_to_json,
    verify_checksums,
)


def _prompt(args: argparse.Namespace) -> str:
    if getattr(args, "prompt_file", None):
        return Path(args.prompt_file).read_text(encoding="utf-8")
    value = getattr(args, "prompt", None)
    if value:
        return str(value)
    raise SystemExit("provide --prompt or --prompt-file")


def _add_run_options(parser: argparse.ArgumentParser) -> None:
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file")
    parser.add_argument("--output-root", default=str(KIT_ROOT / "runs"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--provider-mode", choices=("reference", "ollama"), default="reference")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--model-url", default="http://127.0.0.1:11434")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recover QBT evidence and run blinded ORIGINAL/SHUFFLED/CLASSICAL_MATCHED/NEUTRAL Beast-loop controls."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    recover = sub.add_parser("recover", help="Normalize immutable JSON/JSONL/CSV evidence into canonical JSONL.")
    recover.add_argument("--input", required=True)
    recover.add_argument("--output", required=True)

    run = sub.add_parser("run", help="Run an already-recovered source JSONL through the exact SOUL loop.")
    run.add_argument("--sources", required=True)
    _add_run_options(run)

    all_cmd = sub.add_parser("all", help="Recover input and execute the full blinded control matrix in one command.")
    all_cmd.add_argument("--input", required=True)
    all_cmd.add_argument("--recovered-output")
    _add_run_options(all_cmd)

    verify = sub.add_parser("verify", help="Verify every file recorded in a run SHA256SUMS manifest.")
    verify.add_argument("run_dir")

    sample = sub.add_parser("sample", help="Capture one normalized state from the existing loopback-only QBT sidecar.")
    sample.add_argument("--output", required=True)
    sample.add_argument("--base-url", default="http://127.0.0.1:8766")
    sample.add_argument("--provider", default="simulator", choices=("simulator", "ibm", "azure"))
    sample.add_argument("--shots", type=int, default=1024)
    sample.add_argument("--seed", type=int, default=42)
    sample.add_argument(
        "--allow-live",
        action="store_true",
        help="Required for IBM/Azure. QBT must independently have live providers enabled.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "recover":
        records = recover_to_jsonl(args.input, args.output)
        print(json.dumps({"records": len(records), "output": str(Path(args.output))}, sort_keys=True))
        return 0
    if args.command == "run":
        sources = load_recovered(args.sources)
        run_dir = execute_run(
            sources,
            prompt=_prompt(args),
            output_root=args.output_root,
            seed=args.seed,
            provider_mode=args.provider_mode,
            model=args.model,
            model_url=args.model_url,
        )
        print(run_dir)
        return 0
    if args.command == "all":
        recovered_path = Path(args.recovered_output) if args.recovered_output else Path(args.output_root) / "recovered-sources.jsonl"
        sources = recover_to_jsonl(args.input, recovered_path)
        run_dir = execute_run(
            sources,
            prompt=_prompt(args),
            output_root=args.output_root,
            seed=args.seed,
            provider_mode=args.provider_mode,
            model=args.model,
            model_url=args.model_url,
        )
        print(run_dir)
        return 0
    if args.command == "verify":
        result = verify_checksums(args.run_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    if args.command == "sample":
        sample_qbt_to_json(
            args.output,
            base_url=args.base_url,
            provider=args.provider,
            shots=args.shots,
            seed=args.seed,
            allow_live=args.allow_live,
        )
        print(args.output)
        return 0
    raise SystemExit(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
