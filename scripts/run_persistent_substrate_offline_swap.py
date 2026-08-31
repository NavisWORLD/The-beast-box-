#!/usr/bin/env python3
"""Run or verify the frozen offline persistent-substrate model-swap experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from beastbox.persistent_substrate.offline import (
    run_offline_experiment,
    verify_offline_evidence,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute or independently verify persistent-substrate-model-swap-001."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="execute the frozen no-network A -> B -> A closure")
    run.add_argument("--repo-root", default=".", help="repository root")
    run.add_argument("--workspace", required=True, help="isolated disposable runtime directory")
    run.add_argument("--out", required=True, help="new evidence output directory")

    verify = subparsers.add_parser("verify", help="verify an existing sealed evidence package")
    verify.add_argument("--repo-root", default=".", help="repository root")
    verify.add_argument("--out", required=True, help="sealed evidence directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root)
    evidence_root = Path(args.out)

    if args.command == "run":
        receipt = run_offline_experiment(
            repo_root=repo_root,
            workspace=Path(args.workspace),
            out_dir=evidence_root,
        )
    else:
        receipt = verify_offline_evidence(evidence_root, repo_root=repo_root)

    print(json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
