#!/usr/bin/env python3
"""OMEGA-001 live demonstration driver (real models, real substrate, real trace).

`start` queues a problem stream on a fresh substrate and runs the operator with
adaptive model selection over the pinned local checkpoints. Tasks are paced by
`--pace` seconds so a person can follow the live viewer; pacing is disclosed in
the journal and does not change any computation. `stop` writes the emergency
stop file from a separate process. `resume` clears it (owner action), recovers
and continues. The viewer is served by `scripts/omega_viewer.py serve`.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from beastbox.omega.operator import STOP_FILE, Budget, CognitiveOperator  # noqa: E402
from scripts.omega_model_independence_001 import build_pool  # noqa: E402

MOVE = 'Reply with exactly this JSON and nothing else: {"tool_request": {"capability": "SIMULATED_MOVE", "value": 0.3}}'
STREAM = [
    ("observe", {"text": "Remember this: the vault code is cobalt-41.", "required_model": "C"}),
    ("observe", {"text": "Remember this: the orbit seal is prism-birch.", "required_model": "B",
                 "features": [0.8, -0.4, 0.2]}),
    ("probe", {"question": "What is the vault code?", "expected": "cobalt-41"}),
    ("probe", {"question": "What is the orbit seal?", "expected": "prism-birch"}),
    ("observe", {"text": MOVE, "required_model": "C"}, ("SIMULATED_MOVE",)),
    ("observe", {"text": MOVE, "required_model": "C"}),
    ("probe", {"question": "What is the vault code?", "expected": "cobalt-41"}),
    ("probe", {"question": "What is the orbit seal?", "expected": "prism-birch"}),
    ("observe", {"text": "Remember this: the lantern word is saffron-17.", "required_model": "A"}),
    ("probe", {"question": "What is the lantern word?", "expected": "saffron-17"}),
    ("probe", {"question": "What is the vault code?", "expected": "cobalt-41"}),
    ("probe", {"question": "What is the lantern word?", "expected": "saffron-17"}),
]


class Paced(CognitiveOperator):
    pace = 0.0

    def _execute(self, task):
        super()._execute(task)
        if self.pace:
            time.sleep(self.pace)


def operator(args) -> Paced:
    op = Paced(args.work / "substrate", args.work / "control", build_pool(args.models),
               budget=Budget(max_tasks=60, max_wall_seconds=1800, max_provider_calls=40, maintenance_every=4),
               selector="adaptive", min_trials=1)
    op.pace = args.pace
    return op


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cmd", choices=("start", "stop", "resume", "report"))
    parser.add_argument("--models", type=Path, default=PROJECT_ROOT / "build" / "omega-models")
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--pace", type=float, default=0.0)
    args = parser.parse_args()
    if args.cmd == "stop":
        (args.work / "control" / STOP_FILE).write_text("owner emergency stop from a separate process\n")
        print("emergency stop file written")
        return 0
    op = operator(args)
    try:
        if args.cmd == "start":
            if (args.work / "substrate").exists():
                raise SystemExit("start requires a fresh work directory")
            op.store.log("demo_pacing", seconds_between_tasks=args.pace)
            for item in STREAM:
                kind, payload, *grants = item
                op.submit(kind, payload, grants=grants[0] if grants else ())
        elif args.cmd == "resume":
            op.clear_stop(reviewer="owner-demo")
        if args.cmd in ("start", "resume"):
            print(json.dumps(op.run(), indent=2))
        print(json.dumps({"inspect": op.open(), "model_stats": op.report()["model_stats"]}, indent=2, default=str))
    finally:
        op.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
