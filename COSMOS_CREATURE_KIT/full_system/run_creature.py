#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.creature.bridges import azure_receipt_from_payload, classical_receipt, ibm_receipt_from_resident
from beastbox.creature.project import create_creature_project
from beastbox.creature.runtime import CreatureRuntime


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the provider-neutral COSMOS Creature state/memory/heartbeat loop")
    parser.add_argument("name")
    parser.add_argument("--root", default="./creatures")
    parser.add_argument("--provider", choices=["classical", "ibm", "azure"], default="classical")
    parser.add_argument("--receipt", help="sanitized IBM resident receipt or Azure payload JSON")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--remember", default="creature initialized")
    args = parser.parse_args()

    project = Path(args.root) / args.name
    if not (project / "creature.json").exists():
        project = create_creature_project(args.name, args.root)

    if args.provider == "classical":
        receipt = classical_receipt(args.seed)
    else:
        if not args.receipt:
            raise SystemExit("--receipt is required for IBM or Azure; provide only a sanitized receipt/payload")
        raw = _load(args.receipt)
        receipt = ibm_receipt_from_resident(raw) if args.provider == "ibm" else azure_receipt_from_payload(raw)

    runtime = CreatureRuntime(project)
    try:
        runtime.activate_receipt(receipt)
        runtime.remember("system", args.remember)
        runtime.tick()
        print(json.dumps(runtime.snapshot(), indent=2, sort_keys=True, default=str))
    finally:
        runtime.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
