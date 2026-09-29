"""Isolated, no-network COSMOS feedback challenge.

This is a synthetic *retrieval-control* experiment, not autonomous self-correction,
model training, real owner feedback, consciousness or broad intelligence evidence.
It exercises the actual product AdaptiveControl/RefractiveMemoryRouter with fixed
fixtures. Negative controls use deliberately incorrect synthetic pseudo-labels.
The word "reviewed" in the internal API is a validation flag for these fixtures;
it does not imply a human has reviewed or endorsed them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import tempfile
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
from unittest.mock import patch

from beastbox.adaptive_control import AdaptiveControl
from beastbox.memory import ReconciliationMemory
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import RefractiveMemoryRouter, WEIGHTS

SEEDS = (0, 1, 2, 3, 4)
FIXTURE_CLOCK = 1_735_689_600.0  # Fixed simulation epoch, NOT an execution date.
# (source text, synthetic training query, disjoint held-out paraphrase)
TRAIN_CORPUS = (
    ("Amber pine sawmill construction guide.", "amber pine sawmill plans", "lumber guide for the pine mill"),
    ("Blue sea turtle migration and nesting atlas.", "blue turtle nesting atlas", "sea reptile migration and nests"),
    ("Violet orchid indoor watering calendar.", "violet orchid watering schedule", "watering an indoor purple orchid"),
    ("Orange solar panel installation specifications.", "orange solar installation specs", "installation details for the orange solar array"),
    ("Red alpine mountain climbing weather forecast.", "red alpine climbing weather", "mountain conditions for a red alpine ascent"),
    ("Silver railway bridge maintenance manual.", "silver railway bridge maintenance", "upkeep manual for the silver train bridge"),
    ("Green orchard frost protection handbook.", "green orchard frost handbook", "protecting a green fruit orchard from freezing"),
    ("Golden telescope mirror alignment notes.", "golden telescope mirror alignment", "optical alignment notes for a gold telescope"),
)
TRANSFER_CORPUS = (
    ("Copper harbor tidal navigation tables.", "copper harbor tidal tables", "navigation through copper port tides"),
    ("Ivory museum artifact preservation catalog.", "ivory museum preservation catalog", "conserving an ivory exhibit in the museum"),
    ("Teal robotics actuator calibration procedure.", "teal robot actuator calibration", "adjusting the teal machine motor"),
    ("Crimson bakery sourdough fermentation log.", "crimson bakery sourdough log", "fermentation record from a crimson bread bakery"),
    ("Indigo forest wildlife camera inventory.", "indigo wildlife camera inventory", "catalog of cameras in the indigo woods"),
    ("Bronze satellite antenna tracking handbook.", "bronze satellite tracking handbook", "tracking a satellite with the bronze dish"),
    ("Maroon hospital equipment sterilization guide.", "maroon hospital sterilization guide", "disinfecting maroon clinical equipment"),
    ("Pearl ocean sediment sampling protocol.", "pearl ocean sediment protocol", "collecting seabed samples for the pearl survey"),
)


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def validate_fixtures() -> None:
    """Fail closed on leakage or duplicate gold documents before observing outcomes."""
    if len(TRAIN_CORPUS) != 8 or len(TRANSFER_CORPUS) != 8:
        raise ValueError("the preregistered corpora must each contain eight cases")
    queries = []
    documents = []
    for corpus in (TRAIN_CORPUS, TRANSFER_CORPUS):
        for row in corpus:
            if len(row) != 3 or any(not isinstance(x, str) or not x.strip() for x in row):
                raise ValueError("invalid nonempty fixture triple")
            documents.append(row[0].casefold().strip())
            queries.extend((row[1].casefold().strip(), row[2].casefold().strip()))
    if len(queries) != len(set(queries)) or len(documents) != len(set(documents)):
        raise ValueError("fixture train/holdout leakage or repeated document")


def _new_corpus(path: Path, cases: tuple[tuple[str, str, str], ...], seed: int):
    memory = ReconciliationMemory(path)
    order = list(range(len(cases)))
    random.Random(seed).shuffle(order)
    ids = {}
    for index in order:
        ids[index] = memory.store(cases[index][0], kind="synthetic-feedback-fixture")
    controller = AdaptiveControl(
        RefractiveMemoryRouter(SimpleNamespace(memory=memory)),
        r12_state=initial_r12_state(), dyn12=[0.0] * 12,
    )
    return memory, controller, ids


def _examples(cases, ids, query_index: int, shift: int = 0):
    return [
        {
            "query": cases[index][query_index],
            "preferred_memory_id": ids[(index + shift) % len(cases)],
            "reviewed": True,  # Synthetic protocol fixture, NOT real human review.
        }
        for index in range(len(cases))
    ]


def _top_id(controller: AdaptiveControl, query: str, weights) -> int | None:
    ranked = controller._rank(controller._candidates(query), weights)
    return int(ranked[0]["memory_id"]) if ranked else None


def _mrr(controller: AdaptiveControl, cases, ids, weights) -> float:
    reciprocal = []
    for index, case in enumerate(cases):
        ranked = controller._rank(controller._candidates(case[2]), weights)
        gold = ids[index]
        match = next((position for position, row in enumerate(ranked, 1) if row["memory_id"] == gold), None)
        reciprocal.append(1.0 / match if match else 0.0)
    return round(mean(reciprocal), 6)


def _snapshot(memory: ReconciliationMemory) -> str:
    rows = memory.db.execute(
        "SELECT id,created_at,kind,text,metadata_json,source_ids_json FROM memories ORDER BY id"
    ).fetchall()
    return sha256([list(row) for row in rows])


def run_seed(seed: int) -> dict:
    """Fixed clock, isolated temp databases, disjoint queries and correct/false-label controls."""
    with patch("time.time", return_value=FIXTURE_CLOCK), tempfile.TemporaryDirectory(prefix="cosmos-feedback-") as temp:
        root = Path(temp)
        a, correct, a_ids = _new_corpus(root / "domain_a.sqlite3", TRAIN_CORPUS, seed)
        b, transfer, b_ids = _new_corpus(root / "domain_b.sqlite3", TRANSFER_CORPUS, seed + 100)
        blank, empty, _ = _new_corpus(root / "empty.sqlite3", (), seed)
        try:
            if _top_id(empty, TRAIN_CORPUS[0][2], WEIGHTS) is not None:
                raise AssertionError("no-memory negative control returned a fabricated memory")
            before = [
                _top_id(correct, case[1], WEIGHTS) == a_ids[index]
                for index, case in enumerate(TRAIN_CORPUS)
            ]
            train = _examples(TRAIN_CORPUS, a_ids, 1)
            heldout = _examples(TRAIN_CORPUS, a_ids, 2)
            randomized_train = train.copy()
            random.Random(seed + 200).shuffle(randomized_train)
            receipt = correct.fit(randomized_train)
            within = correct.evaluate(heldout)
            after = [
                _top_id(correct, case[1], correct.weights) == a_ids[index]
                for index, case in enumerate(TRAIN_CORPUS)
            ]

            # Deliberately wrong pseudo-labels, never owner-reviewed evidence.
            misleading = AdaptiveControl(
                correct.router, r12_state=initial_r12_state(), dyn12=[0.0] * 12
            )
            false_train = _examples(TRAIN_CORPUS, a_ids, 1, shift=1)
            random.Random(seed + 300).shuffle(false_train)
            misleading.fit(false_train)
            shuffled = misleading.evaluate(heldout)
            if shuffled["frozen_mrr"] != within["frozen_mrr"]:
                raise AssertionError("matched frozen comparators diverged")

            transfer_result = {
                "frozen_mrr": _mrr(transfer, TRANSFER_CORPUS, b_ids, WEIGHTS),
                "adapted_mrr": _mrr(transfer, TRANSFER_CORPUS, b_ids, correct.weights),
                "shuffled_mrr": _mrr(transfer, TRANSFER_CORPUS, b_ids, misleading.weights),
            }
            before_hash = _snapshot(a)
            before_stats = a.stats()
            a.close()
            a = ReconciliationMemory(root / "domain_a.sqlite3")
            after_hash = _snapshot(a)
            if before_hash != after_hash or a.stats() != before_stats:
                raise AssertionError("reopened SQLite memory did not match the original fixture")
            if dict(WEIGHTS) != receipt["frozen_weights"]:
                raise AssertionError("frozen router weights mutated")
            if set(within["training_query_sha256"]) & set(within["heldout_query_sha256"]):
                raise AssertionError("training/holdout query leakage")
            return {
                "seed": seed,
                "training": {
                    "cases": len(train),
                    "mistakes_during_fit": receipt["mistakes_during_training"],
                    "initial_top1_correct": sum(before),
                    "after_feedback_top1_correct": sum(after),
                    "corrected": sum(not old and new for old, new in zip(before, after)),
                    "regressed": sum(old and not new for old, new in zip(before, after)),
                    "learned_weights": receipt["learned_weights"],
                },
                "within_corpus": {
                    "frozen_mrr": round(within["frozen_mrr"], 6),
                    "adapted_mrr": round(within["adaptive_mrr"], 6),
                    "shuffled_mrr": round(shuffled["adaptive_mrr"], 6),
                    "query_sha256": within["heldout_query_sha256"],
                },
                "heldout_transfer": transfer_result,
                "memory_reopen": {
                    "exact_fixture_rows_match": True,
                    "snapshot_sha256": before_hash,
                    "record_count": before_stats["memories"],
                    "scope": "same-process SQLite close/reopen; NOT process-death model continuity",
                },
                "empty_memory_control": "zero candidates",
            }
        finally:
            a.close()
            b.close()
            blank.close()


def run_suite() -> dict:
    validate_fixtures()
    seeds = [run_seed(seed) for seed in SEEDS]
    groups = ("within_corpus", "heldout_transfer")
    aggregate = {
        group: {
            key: round(mean(result[group][key] for result in seeds), 6)
            for key in ("frozen_mrr", "adapted_mrr", "shuffled_mrr")
        }
        for group in groups
    }
    for group in groups:
        metrics = aggregate[group]
        metrics["adaptive_minus_frozen"] = round(metrics["adapted_mrr"] - metrics["frozen_mrr"], 6)
        metrics["adaptive_minus_shuffled"] = round(metrics["adapted_mrr"] - metrics["shuffled_mrr"], 6)
    return {
        "schema": "cosmos-isolated-learning-challenge-v1",
        "provenance_class": "derived-synthetic",
        "fixture_sha256": sha256([TRAIN_CORPUS, TRANSFER_CORPUS]),
        "seed_set": list(SEEDS),
        "conditions": ["fixed_frozen_router", "reviewed_fixture_feedback", "deliberately_mislabeled_fixture_feedback", "empty_memory"],
        "query_policy": "all training queries disjoint from all held-out queries; cross-domain held-out corpus",
        "clock": "fixed synthetic clock for reproducibility; no timing benchmark",
        "model_weights_changed": False,
        "product_data_or_deployment_changed": False,
        "claim_boundary": (
            "synthetic routing feedback and same-process memory reopen only; "
            "no real-model learning, genuine autonomous self-correction, "
            "owner-memory persistence, fresh-process recovery or cross-domain intelligence claim"
        ),
        "aggregate": aggregate,
        "seed_results": seeds,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="explicit synthetic JSON receipt destination")
    args = parser.parse_args()
    report = run_suite()
    payload = canonical_json(report) + b"\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(json.dumps({
        "receipt": str(args.output), "receipt_sha256": hashlib.sha256(payload).hexdigest(),
        "fixture_sha256": report["fixture_sha256"], "aggregate": report["aggregate"],
        "provenance_class": report["provenance_class"],
        "checkout_sha": os.environ.get("GITHUB_SHA", "local-not-attested"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
