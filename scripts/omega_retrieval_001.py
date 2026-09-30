#!/usr/bin/env python3
"""OMEGA-001 E1/E2: deployed R12 routing and Hebbian plasticity vs matched controls.

Memory is written through real `DurableRuntime.respond()` turns, so dyn12, CNS,
Hebbian associations and checkpoints evolve exactly as in production. Each query
is ranked against the same frozen store with the dyn12/sequence that the runtime's
next turn would use; a sample is checked against an actual `respond()` on a copy.
Preregistration: docs/experiments/OMEGA_001_PREREGISTRATION.md.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from beastbox.bridge import BridgePacket  # noqa: E402
from beastbox.durable import DurableRuntime, _RoutingMemoryView  # noqa: E402
from beastbox.memory import ReconciliationMemory  # noqa: E402
from beastbox.refractive_memory import WEIGHTS, RefractiveMemoryRouter  # noqa: E402
from beastbox.retrieval_snapshot import capture_snapshot  # noqa: E402
from beastbox.state import MissionState  # noqa: E402
from beastbox.synaptic import SynapticField  # noqa: E402

SCHEMA = "omega-001-retrieval-v1"
ADJ = ("amber brisk cedar dusky elder frosty gilded hollow ivory jagged kindred lunar misty noble "
       "opal pale quiet russet silver tidal umber velvet woven young zephyr ashen bronze coral "
       "distant ember").split()
NOUN = ("harbor lantern meadow orchard quarry river summit tunnel valley willow beacon canyon "
        "delta forge garden island jetty kiln lagoon mill nest outpost pier ridge spire temple "
        "vault wharf yard zenith").split()
ALIAS = ("glint murmur tallow brine quill ferrule nimbus sorrel gantry lintel runnel spindle "
         "thicket wicket yarrow bramble cairn dory eyot flume gorse hummock inlet knoll").split()
VALUE_A = "cobalt saffron indigo scarlet jade umber topaz obsidian pearl crimson teal ochre".split()
PLACES = ("north station, west dock, old mill, east gate, high tower, river ford, south field, "
          "lower market, glass hall, stone bridge, iron yard, salt road").split(", ")


class Noted:
    model = "noted-fixture"

    def generate(self, prompt: str) -> str:
        return "Noted."


def _value(rng: random.Random) -> str:
    return f"{rng.choice(VALUE_A)}-{rng.randint(10, 99)}"


def workload_direct(seed: int, n_facts: int = 24) -> dict[str, Any]:
    rng = random.Random(1000 + seed)
    pairs = rng.sample([(a, n) for a in ADJ for n in NOUN], n_facts)
    facts, queries, distractors = [], [], []
    for adj, noun in pairs:
        value = _value(rng)
        facts.append((f"The {adj} {noun} code is {value}.", value))
        queries.append((f"What is the {adj} {noun} code?", value))
        other = rng.choice([a for a in ADJ if (a, noun) not in pairs])
        distractors.append(f"The {other} {noun} code was retired last season.")
        distractors.append(f"The {adj} {noun} ferry leaves at {rng.randint(1, 12)} o'clock.")
    return {"facts": facts, "aliases": [], "distractors": distractors, "queries": queries}


def workload_alias(seed: int, n_facts: int = 16) -> dict[str, Any]:
    rng = random.Random(2000 + seed)
    nouns = rng.sample(NOUN, n_facts)
    aliases = rng.sample(ALIAS, n_facts)
    facts, alias_lines, queries, distractors = [], [], [], []
    for noun, alias in zip(nouns, aliases):
        value = _value(rng)
        facts.append((f"The {noun} code is {value}.", value))
        alias_lines.append(f"People also call the {noun} the {alias}.")
        queries.append((f"What is the {alias} code?", value))
        distractors.append(f"The {noun} was painted {rng.choice(VALUE_A)} in spring.")
        distractors.append(f"Visitors walked past the {rng.choice(NOUN)} at dawn.")
    return {"facts": facts, "aliases": alias_lines, "distractors": distractors, "queries": queries}


def workload_unseen(seed: int, n_facts: int = 24) -> dict[str, Any]:
    """Held-out template family for E6; the proposer never calls this."""
    rng = random.Random(3000 + seed)
    combos = rng.sample([(n, p) for n in NOUN for p in PLACES], n_facts)
    facts, queries, distractors = [], [], []
    for noun, place in combos:
        value = _value(rng)
        facts.append((f"For the {place}, the {noun} passphrase is {value}.", value))
        queries.append((f"Which passphrase opens the {noun} at the {place}?", value))
        distractors.append(f"The {noun} at the {rng.choice(PLACES)} needs a new passphrase soon.")
        distractors.append(f"Someone left the {place} {rng.choice(NOUN)} unlocked.")
    return {"facts": facts, "aliases": [], "distractors": distractors, "queries": queries}


def build_store(root: Path, work: dict[str, Any], seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    stream = [("fact", t) for t, _ in work["facts"]] + [("distractor", t) for t in work["distractors"]]
    rng.shuffle(stream)
    # Aliases precede facts in time, as an earlier conversation would.
    stream = [("alias", t) for t in work["aliases"]] + stream
    runtime = DurableRuntime(root, Noted())
    try:
        for _, text in stream:
            runtime.respond(text)
        return runtime.inspect()
    finally:
        runtime.close()


def next_turn_route_inputs(runtime: DurableRuntime, query: str) -> tuple[int, list[float]]:
    """Reproduce the dyn12/sequence `respond()` would hand the router, without committing."""
    fam = copy.deepcopy(runtime.synaptic.state_family)
    cns = copy.deepcopy(runtime.cns)
    packet = BridgePacket()
    syn = SynapticField(state_family=fam).step(audio_features=packet.audio_features,
                                              quantum_spark=packet.quantum_spark)
    state = MissionState(mission_id="probe", objective=query, dyn12=list(syn["states"]["dyn12"]))
    cns.tick(state, packet.safe_dict())
    return runtime.turn + 1, list(state.dyn12)


def rank_all(memory: ReconciliationMemory, rows, query: str, sequence: int, dyn12, r12_state) -> list[dict]:
    adapter = SimpleNamespace(memory=_RoutingMemoryView(memory, rows))
    return RefractiveMemoryRouter(adapter).rank(query, sequence=sequence, dyn12=dyn12,
                                                r12_state=r12_state, limit=len(rows))


def rescore(ranked: list[dict], weights: dict[str, float]) -> list[int]:
    scored = sorted(ranked, key=lambda r: (sum(weights[k] * r["components"][k] for k in weights),
                                           r["memory_id"]), reverse=True)
    return [r["memory_id"] for r in scored]


def gold_ids(rows, value: str) -> set[int]:
    return {int(r["id"]) for r in rows if value.lower() in str(r["text"]).lower() and r["kind"] == "user_turn"}


def rank_metrics(order: list[int], gold: set[int]) -> dict[str, float]:
    rank = next((i + 1 for i, mid in enumerate(order) if mid in gold), None)
    return {"hit1": float(rank == 1), "hit5": float(rank is not None and rank <= 5),
            "rr": 0.0 if rank is None else 1.0 / rank}


def evaluate_seed(work: dict[str, Any], seed: int, tmp: Path, *, weights_variants: dict[str, dict] | None = None,
                  fidelity_checks: int = 2, include_hebbian_ablation: bool = False,
                  keep_components: bool = False) -> dict[str, Any]:
    root = tmp / f"seed-{seed}"
    build_store(root, work, seed)
    runtime = DurableRuntime(root, Noted())
    ablated_memory = None
    try:
        runtime.inspect()
        rows = capture_snapshot(runtime.memory)
        if include_hebbian_ablation:
            ablated_path = tmp / f"seed-{seed}-ablated.sqlite3"
            src = sqlite3.connect(root / "runtime.sqlite3")
            dst = sqlite3.connect(ablated_path)
            src.backup(dst)
            src.close()
            dst.execute("DELETE FROM associations")
            dst.commit()
            dst.close()
            ablated_memory = ReconciliationMemory(ablated_path)
        rng = random.Random(7000 + seed)
        per_query = []
        for qi, (query, value) in enumerate(work["queries"]):
            sequence, dyn12 = next_turn_route_inputs(runtime, query)
            gold = gold_ids(rows, value)
            ranked = rank_all(runtime.memory, rows, query, sequence, dyn12, runtime.r12_state)
            deployed = [r["memory_id"] for r in ranked]
            shuffled = list(dyn12)
            random.Random(9000 + seed * 100 + qi).shuffle(shuffled)
            arms = {
                "r12_deployed": deployed,
                "r12_no_spatial": rescore(ranked, {**WEIGHTS, "spatial": 0.0}),
                "r12_shuffled_dyn12": [r["memory_id"] for r in rank_all(
                    runtime.memory, rows, query, sequence, shuffled, runtime.r12_state)],
                "lexical_baseline": [h.id for h in runtime.memory.search(query, limit=len(rows))],
                "random": rng.sample([int(r["id"]) for r in rows], len(rows)),
            }
            if ablated_memory is not None:
                arms["hebbian_ablated"] = [r["memory_id"] for r in rank_all(
                    ablated_memory, rows, query, sequence, dyn12, runtime.r12_state)]
            for name, weights in (weights_variants or {}).items():
                arms[name] = rescore(ranked, weights)
            entry = {"seed": seed, "query": query, "gold": sorted(gold),
                     "arms": {k: rank_metrics(v, gold) for k, v in arms.items()},
                     "deployed_top5": deployed[:5]}
            if keep_components:
                entry["components"] = [(r["memory_id"], r["components"]) for r in ranked]
            per_query.append(entry)
        fidelity = []
        for qi in range(min(fidelity_checks, len(work["queries"]))):
            query = work["queries"][qi][0]
            copy_root = tmp / f"seed-{seed}-fidelity-{qi}"
            shutil.copytree(root, copy_root)
            probe = DurableRuntime(copy_root, Noted())
            try:
                actual = probe.respond(query)["routing"]["memory_ids"]
            finally:
                probe.close()
            fidelity.append(actual == per_query[qi]["deployed_top5"])
        return {"per_query": per_query, "fidelity": fidelity, "memories": len(rows)}
    finally:
        runtime.close()
        if ablated_memory is not None:
            ablated_memory.close()


def paired_bootstrap(a: list[float], b: list[float], *, resamples: int = 10_000, seed: int = 67) -> dict[str, float]:
    rng = random.Random(seed)
    n = len(a)
    diffs = [x - y for x, y in zip(a, b)]
    stats = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples))
    return {"mean_diff": sum(diffs) / n, "ci95_low": stats[int(0.025 * resamples)],
            "ci95_high": stats[int(0.975 * resamples) - 1], "n": n}


def summarize(per_query: list[dict]) -> dict[str, dict[str, float]]:
    arms = per_query[0]["arms"].keys()
    return {arm: {m: sum(q["arms"][arm][m] for q in per_query) / len(per_query) for m in ("hit1", "hit5", "rr")}
            for arm in arms}


def column(per_query, arm, metric="hit5"):
    return [q["arms"][arm][metric] for q in per_query]


def run(seeds: list[int], output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    report: dict[str, Any] = {"schema": SCHEMA, "seeds": seeds, "weights": WEIGHTS}
    with tempfile.TemporaryDirectory(prefix="omega-e1e2-") as tmp_name:
        tmp = Path(tmp_name)
        e1, e2, fidelity = [], [], []
        for seed in seeds:
            r1 = evaluate_seed(workload_direct(seed), seed, tmp / "e1")
            r2 = evaluate_seed(workload_alias(seed), seed, tmp / "e2", include_hebbian_ablation=True)
            e1 += r1["per_query"]
            e2 += r2["per_query"]
            fidelity += r1["fidelity"] + r2["fidelity"]
    e1_sum, e2_sum = summarize(e1), summarize(e2)
    best_control = max(("lexical_baseline", "r12_no_spatial"), key=lambda a: e1_sum[a]["hit5"])
    vs_best = paired_bootstrap(column(e1, "r12_deployed"), column(e1, best_control))
    vs_lex = paired_bootstrap(column(e1, "r12_deployed"), column(e1, "lexical_baseline"))
    if vs_best["mean_diff"] >= 0.05 and vs_best["ci95_low"] > 0:
        e1_verdict = "SUPPORTED"
    elif vs_lex["ci95_high"] < 0:
        e1_verdict = "REFUTED_FOR_THIS_WORKLOAD"
    else:
        e1_verdict = "NULL"
    heb = paired_bootstrap(column(e2, "r12_deployed"), column(e2, "hebbian_ablated"))
    e2_verdict = "SUPPORTED" if heb["mean_diff"] >= 0.05 and heb["ci95_low"] > 0 else "NULL"
    report.update({
        "fidelity_checks": {"passed": sum(fidelity), "total": len(fidelity)},
        "E1": {"summary": e1_sum, "best_control": best_control, "deployed_vs_best_control": vs_best,
               "deployed_vs_lexical": vs_lex,
               "no_spatial_vs_deployed": paired_bootstrap(column(e1, "r12_no_spatial"), column(e1, "r12_deployed")),
               "shuffled_dyn12_vs_deployed": paired_bootstrap(column(e1, "r12_shuffled_dyn12"),
                                                              column(e1, "r12_deployed")),
               "verdict": e1_verdict, "n_queries": len(e1)},
        "E2": {"summary": e2_sum, "deployed_vs_hebbian_ablated": heb,
               "deployed_vs_lexical": paired_bootstrap(column(e2, "r12_deployed"), column(e2, "lexical_baseline")),
               "verdict": e2_verdict, "n_queries": len(e2)},
        "wall_seconds": round(time.perf_counter() - started, 2),
        "per_query": {"E1": e1, "E2": e2},
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="*", default=list(range(10)))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.seeds, args.output)
    for key in ("E1", "E2"):
        print(key, report[key]["verdict"], json.dumps(report[key]["summary"], indent=None))
    print("fidelity", report["fidelity_checks"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
