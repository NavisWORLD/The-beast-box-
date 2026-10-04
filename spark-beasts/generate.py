#!/usr/bin/env python3
"""Spark one beast from a simulated signal and a recorded IBM run.

  python generate.py --simulate serene --run ibm_kingston:d93jnlq47v0s73823aj0
  python generate.py --focus 40 --calm 35 --spark 20 --run ibm_fez:da55afc3jnrc73agsvv0#pub2 --user-id cory
  python generate.py --list-runs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from beastgen.genome import build_genome  # noqa: E402
from beastgen.runs import get_run, load_runs  # noqa: E402
from beastgen.signal import PROFILES, simulate_stable  # noqa: E402
from qbeast_file import build_qbeast, serialize_qbeast  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Spark a Lost Cosmos beast and write genome.json plus a .qbeast file.")
    parser.add_argument("--focus", type=int)
    parser.add_argument("--calm", type=int)
    parser.add_argument("--spark", type=int)
    parser.add_argument("--simulate", choices=sorted(PROFILES))
    parser.add_argument("--run", default="ibm_marrakesh:d93d8pgoamcc73dc3afg")
    parser.add_argument("--user-id")
    parser.add_argument("--bucket", type=int, default=10)
    parser.add_argument("--out", default="out/single")
    parser.add_argument("--list-runs", action="store_true")
    args = parser.parse_args()
    if args.list_runs:
        for run in load_runs():
            print(f"{run['key']}  {run['num_bits']}bit  {run['shots']} shots")
        return
    if args.simulate:
        traits = simulate_stable(args.simulate, bucket=args.bucket)
    else:
        if None in (args.focus, args.calm, args.spark):
            parser.error("give --focus/--calm/--spark or --simulate")
        traits = {"focus": args.focus, "calm": args.calm, "spark": args.spark}
    run = get_run(args.run)
    genome = build_genome(traits, run, args.user_id, bucket=args.bucket)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "genome.json").write_text(json.dumps(genome, indent=1) + "\n")
    (out / f"{genome['names'][2]}.qbeast").write_text(serialize_qbeast(build_qbeast(genome)))
    print(json.dumps({"seed": genome["seed"], "names": genome["names"], "island": genome["island"], "run": run["key"], "out": str(out)}, indent=1))


if __name__ == "__main__":
    main()
