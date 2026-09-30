#!/usr/bin/env python3
"""OMEGA-001 E6 transfer: do candidate routing weights change real model answers?

Loads the hash-pinned candidate file (verifying its SHA-256 after a fresh process
start), builds the held-out unseen-template store (seed 100), and for each of 24
queries runs a real `DurableRuntime.respond()` on a private copy of the store with
models B and C, under baseline and candidate weights. Exact-recall is scored by
substring match on the gold value. Weight patching is confined to this process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from beastbox import refractive_memory  # noqa: E402
from beastbox.durable import DurableRuntime  # noqa: E402
from scripts.omega_model_independence_001 import build_pool  # noqa: E402
from scripts.omega_retrieval_001 import build_store, workload_unseen  # noqa: E402


def load_candidate(path: Path) -> dict:
    data = json.loads(path.read_text())
    body = {k: data[k] for k in ("schema", "weights", "baseline_weights", "promoted")}
    if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != data["sha256"]:
        raise RuntimeError("candidate file hash mismatch")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidate = load_candidate(args.candidate)
    baseline = dict(refractive_memory.WEIGHTS)
    if baseline != candidate["baseline_weights"]:
        raise RuntimeError("production baseline weights differ from the recorded baseline")
    work = workload_unseen(100)
    pool = build_pool(args.models)
    rows = []
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="omega-transfer-") as tmp_name:
        tmp = Path(tmp_name)
        store = tmp / "store"
        build_store(store, work, 100)
        for key in ("B", "C"):
            provider = pool.get(key)
            for arm, weights in (("baseline", baseline), ("candidate", candidate["weights"])):
                refractive_memory.WEIGHTS.clear()
                refractive_memory.WEIGHTS.update(weights)
                for qi, (query, gold) in enumerate(work["queries"]):
                    copy_root = tmp / f"{key}-{arm}-{qi}"
                    shutil.copytree(store, copy_root)
                    rt = DurableRuntime(copy_root, provider)
                    try:
                        out = rt.respond(query)
                    finally:
                        rt.close()
                    delivered = provider.calls[-1]["delivered_prompt"].lower()
                    rows.append({"model": key, "arm": arm, "query": query, "gold": gold,
                                 "gold_delivered": gold in delivered,
                                 "model_emitted_gold": gold in out["response"].lower(),
                                 "output": out["response"][:200]})
                    shutil.rmtree(copy_root)
        refractive_memory.WEIGHTS.clear()
        refractive_memory.WEIGHTS.update(baseline)
        pool.release()
    summary = {}
    for key in ("B", "C"):
        for arm in ("baseline", "candidate"):
            sel = [r for r in rows if r["model"] == key and r["arm"] == arm]
            summary[f"{key}:{arm}"] = {"delivered": sum(r["gold_delivered"] for r in sel),
                                       "emitted": sum(r["model_emitted_gold"] for r in sel), "n": len(sel)}
    report = {"schema": "omega-001-transfer-v1", "candidate_sha256": candidate["sha256"],
              "baseline_weights": baseline, "candidate_weights": candidate["weights"], "summary": summary,
              "rows": rows, "wall_s": round(time.perf_counter() - started, 1)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
