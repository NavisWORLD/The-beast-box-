#!/usr/bin/env python3
"""OMEGA-001 E6: bounded self-improvement of the five R12 routing weights.

Proposer: coordinate search over the weights, driven only by retrieval failures
recorded on TRAINING seeds 0-9 of the E1 (direct) and E2 (alias) workloads.
Evaluator: a separate function that the proposer never calls, using seeds
100-119, the same two workloads AND an unseen template family.

The production `WEIGHTS` constant is never modified. The candidate is written to
a separate JSON file with its SHA-256; nothing is promoted. Preregistration:
docs/experiments/OMEGA_001_PREREGISTRATION.md (E6).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from beastbox.refractive_memory import WEIGHTS  # noqa: E402
from scripts.omega_retrieval_001 import (  # noqa: E402
    evaluate_seed, paired_bootstrap, rank_metrics, workload_alias, workload_direct, workload_unseen,
)

KEYS = ("spatial", "lexical", "hebbian", "recency", "integrity")
BASELINE = {k: WEIGHTS[k] for k in KEYS}


def _canon(weights):
    total = sum(max(0.0, w) for w in weights.values())
    return {k: round(max(0.0, weights[k]) / total, 4) for k in KEYS}


def _collect(workloads, seeds, tmp: Path, tag: str):
    """Return, per query, all memories' score components and gold ids for offline rescoring."""
    collected = []
    for name, fn in workloads:
        for seed in seeds:
            out = evaluate_seed(fn(seed), seed, tmp / f"{tag}-{name}-{seed}", fidelity_checks=0,
                                keep_components=True)
            for q in out["per_query"]:
                collected.append({"workload": name, "seed": seed, "gold": set(q["gold"]), "rows": q["components"]})
    return collected


def _hit5(collected, weights):
    out = []
    for q in collected:
        order = [mid for mid, _ in sorted(q["rows"], key=lambda r: (sum(weights[k] * r[1][k] for k in KEYS), r[0]),
                                          reverse=True)]
        out.append(rank_metrics(order, q["gold"])["hit5"])
    return out


def propose(train, *, step=0.05, rounds=6):
    """Coordinate search on training failures only."""
    current = dict(BASELINE)
    best = sum(_hit5(train, current)) / len(train)
    history = [{"round": 0, "weights": current, "train_hit5": best}]
    for rnd in range(1, rounds + 1):
        improved = False
        for key in KEYS:
            for delta in (-step, step, -4 * step, 4 * step):
                trial = _canon({**current, key: current[key] + delta})
                score = sum(_hit5(train, trial)) / len(train)
                if score > best + 1e-9:
                    best, current, improved = score, trial, True
        history.append({"round": rnd, "weights": current, "train_hit5": best})
        if not improved:
            break
    return current, history


def evaluate(candidate, heldout):
    """Trusted evaluator: separate seeds and an unseen template the proposer never saw."""
    result = {}
    for name in sorted({q["workload"] for q in heldout}):
        subset = [q for q in heldout if q["workload"] == name]
        base, cand = _hit5(subset, BASELINE), _hit5(subset, candidate)
        result[name] = {"baseline_hit5": sum(base) / len(base), "candidate_hit5": sum(cand) / len(cand),
                        "candidate_minus_baseline": paired_bootstrap(cand, base)}
    unseen = result["unseen_template"]["candidate_minus_baseline"]
    result["verdict"] = ("ACCEPTED_AS_HELDOUT_IMPROVEMENT" if unseen["mean_diff"] >= 0.05 and unseen["ci95_low"] > 0
                         else "NOT_ACCEPTED")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="omega-e6-") as tmp_name:
        tmp = Path(tmp_name)
        train = _collect([("direct", workload_direct), ("alias", workload_alias)], range(10), tmp, "train")
        candidate, history = propose(train)
        body = {"schema": "omega-001-routing-weight-candidate-v1", "weights": candidate,
                "baseline_weights": BASELINE, "promoted": False}
        blob = json.dumps(body, sort_keys=True).encode()
        args.candidate.parent.mkdir(parents=True, exist_ok=True)
        args.candidate.write_text(json.dumps({**body, "sha256": hashlib.sha256(blob).hexdigest()}, indent=2) + "\n")
        heldout = _collect([("direct", workload_direct), ("alias", workload_alias),
                            ("unseen_template", workload_unseen)], range(100, 120), tmp, "heldout")
    evaluation = evaluate(candidate, heldout)
    report = {"schema": "omega-001-self-improvement-v1", "proposer_history": history, "candidate": candidate,
              "candidate_sha256": hashlib.sha256(blob).hexdigest(), "evaluation": evaluation,
              "train_queries": len(train), "heldout_queries": len(heldout),
              "wall_seconds": round(time.perf_counter() - started, 1)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"candidate": candidate, "evaluation": evaluation}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
