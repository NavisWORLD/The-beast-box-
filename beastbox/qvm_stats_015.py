"""Stage 015 predeclared paired scenario-level uncertainty, NEVER an effect claim.

Positive paired difference means conditioned CNS12's error is larger (worse)
than that comparator. Report percentile bootstrap intervals descriptively,
not as proof of causal improvement or quantum hardware advantage.
"""
from __future__ import annotations

import random
from typing import Any, Sequence

BOOTSTRAP_REPS = 2000
BOOTSTRAP_SEED = 150068
COMPARATORS = ("raw_history", "classical_summary", "shuffled_cns12", "matched_cns12")
MEASURES = ("abs_error_invalid_is_one", "future_empirical_Brier_invalid_is_one")


def paired_12d_effects(individual_rows: Sequence[dict]) -> dict[str, Any]:
    cohorts = {
        "real_azure_cloud_qvm_simulator": 8,
        "local_classical_synthetic": 24,
    }
    index: dict[tuple[str, int, str], dict] = {}
    for row in individual_rows:
        key = (row["cohort"], row["scenario"], row["arm"])
        if key in index:
            raise ValueError("duplicate scenario-arm observation")
        index[key] = row
    results = {}
    for cohort, size in cohorts.items():
        for metric in MEASURES:
            for control in COMPARATORS:
                diffs = []
                for scenario in range(1, size + 1):
                    expected = index.get((cohort, scenario, "cns12"))
                    comparator = index.get((cohort, scenario, control))
                    if expected is None or comparator is None:
                        raise ValueError("missing paired same-scenario control")
                    diffs.append(expected[metric] - comparator[metric])
                assert len(diffs) == size
                rng = random.Random(BOOTSTRAP_SEED + sum(ord(c) for c in cohort+metric+control))
                draws = sorted(sum(diffs[rng.randrange(size)] for _ in range(size)) / size
                               for _ in range(BOOTSTRAP_REPS))
                results[f"{cohort}__{metric}__vs_{control}"] = {
                    "paired_scenarios": size,
                    "mean_conditioned_minus_control": round(sum(diffs) / size, 8),
                    "descriptive_bootstrap_p2_5": round(draws[int(.025 * BOOTSTRAP_REPS)], 8),
                    "descriptive_bootstrap_p97_5": round(draws[min(
                        BOOTSTRAP_REPS-1, int(.975 * BOOTSTRAP_REPS)
                    )], 8),
                    "bootstrap_reps": BOOTSTRAP_REPS,
                    "sign": "negative=fewer errors for CNS12; positive=more errors for CNS12",
                }
    return {
        "schema": "stage015-fixed-descriptive-paired-bootstrap-v1",
        "registered_before_model_inference": True,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "interpretation": "EXPLORATORY_DESCRIPTIVE_NOT_INFERENTIAL_PROOF",
        "paired_by_cohort": results,
    }
