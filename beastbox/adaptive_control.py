"""Isolated, owner-reviewed adaptive retrieval-control experiment.

This module NEVER trains/edits a model or sealed R12 source, alters durable
memory/state, or selects unauthorized providers. Its learned state is an
in-memory, transparent convex combination of the existing frozen router's
five software score components. Any claim of advantage requires held-out
results, repeated seeds and cross-corpus validation not included here.
"""
from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .refractive_memory import RefractiveMemoryRouter, WEIGHTS

_KEYS = ("spatial", "lexical", "hebbian", "recency", "integrity")


class AdaptiveControl:
    """Pairwise feedback routing controlled by explicit reviewed examples."""

    def __init__(
        self, router: RefractiveMemoryRouter, *, r12_state: Mapping[str, Any],
        dyn12: Sequence[float], sequence: int = 0,
    ) -> None:
        self.router = router
        self.r12_state = r12_state
        self.dyn12 = list(dyn12)
        self.sequence = int(sequence)
        self.weights: dict[str, float] = dict(WEIGHTS)
        self._training_queries: set[str] = set()
        self._trained = False

    @staticmethod
    def _validated(sample: Mapping[str, Any]) -> tuple[str, int, str]:
        if not isinstance(sample, Mapping) or set(sample) != {"query", "preferred_memory_id", "reviewed"}:
            raise ValueError("reviewed feedback requires exact query, id and reviewed fields")
        q, key = sample["query"], sample["preferred_memory_id"]
        if not isinstance(q, str) or not 1 <= len(q.strip()) <= 512:
            raise ValueError("bounded nonempty feedback query required")
        if type(key) is not int or key <= 0 or sample["reviewed"] is not True:
            raise ValueError("reviewed positive integer relevant memory id required")
        return q.strip(), key, hashlib.sha256(q.strip().encode("utf-8")).hexdigest()

    def _candidates(self, query: str) -> list[dict[str, Any]]:
        count = int(self.router.ledger.memory.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
        return self.router.rank(
            query, sequence=self.sequence, dyn12=self.dyn12,
            r12_state=self.r12_state, limit=count,
        )

    @staticmethod
    def _rank(candidates: list[dict[str, Any]], weights: Mapping[str, float]) -> list[dict[str, Any]]:
        return sorted(candidates, key=lambda c: (
            sum(float(weights[k]) * float(c["components"][k]) for k in _KEYS),
            int(c["memory_id"]),
        ), reverse=True)

    def fit(self, examples: Sequence[Mapping[str, Any]], *, learning_rate: float = 0.12) -> dict[str, Any]:
        if self._trained:
            raise RuntimeError("adaptive control already fitted; hold out later observations")
        if not isinstance(examples, (tuple, list)) or not 2 <= len(examples) <= 256:
            raise ValueError("training requires between 2 and 256 reviewed examples")
        if not isinstance(learning_rate, (float, int)) or not 0 < learning_rate <= 0.25:
            raise ValueError("bounded adaptation learning rate required")
        scratch = dict(self.weights)
        seen: set[str] = set()
        mistakes = 0
        # Stage the entire fit: invalid labels must not partially mutate weights.
        for sample in examples:
            query, gold, query_hash = self._validated(sample)
            if query_hash in seen:
                raise ValueError("repeated training query would overcount feedback")
            seen.add(query_hash)
            candidates = self._candidates(query)
            target = next((row for row in candidates if int(row["memory_id"]) == gold), None)
            if target is None:
                raise ValueError("reviewed relevant id not found in frozen router candidates")
            ranked = self._rank(candidates, scratch)
            if ranked[0]["memory_id"] == gold:
                continue
            mistakes += 1
            rival = next(row for row in ranked if row["memory_id"] != gold)
            for component in _KEYS:
                scratch[component] = max(
                    0.01,
                    scratch[component] + float(learning_rate)
                    * (target["components"][component] - rival["components"][component]),
                )
            total = sum(scratch.values())
            scratch = {k: v / total for k, v in scratch.items()}
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in scratch.values()):
            raise RuntimeError("adaptive feedback produced invalid normalized weights")
        self.weights = scratch
        self._training_queries = seen
        self._trained = True
        return {
            "schema": "finisher-adaptive-feedback-control-v1",
            "algorithm": "bounded-reviewed-pairwise-reweighting",
            "examples": len(examples), "mistakes_during_training": mistakes,
            "frozen_weights": dict(WEIGHTS), "learned_weights": dict(scratch),
            "trained_model_weights": False,
        }

    def evaluate(self, heldout: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not self._trained:
            raise RuntimeError("fit on reviewed training cases before held-out evaluation")
        if not isinstance(heldout, (tuple, list)) or not 1 <= len(heldout) <= 256:
            raise ValueError("1..256 held-out reviewed cases required")
        seen: set[str] = set()
        fixed_rr, adapted_rr = [], []
        for sample in heldout:
            query, gold, query_hash = self._validated(sample)
            if query_hash in self._training_queries or query_hash in seen:
                raise ValueError("held-out query leakage or duplicate evaluation case")
            seen.add(query_hash)
            candidates = self._candidates(query)
            if not any(int(c["memory_id"]) == gold for c in candidates):
                raise ValueError("held-out relevant id absent from candidate corpus")
            for ranker, values in ((WEIGHTS, fixed_rr), (self.weights, adapted_rr)):
                sorted_rows = self._rank(candidates, ranker)
                rank = next(index for index, item in enumerate(sorted_rows, 1) if item["memory_id"] == gold)
                values.append(1.0 / rank)
        return {
            "schema": "finisher-heldout-routing-ablation-v1",
            "provenance_class": "derived-synthetic",
            "fixture_kind": "owner-reviewed-software-ranking-fixture",
            "training_query_sha256": sorted(self._training_queries),
            "heldout_query_sha256": sorted(seen),
            "samples": len(heldout),
            "frozen_mrr": sum(fixed_rr) / len(fixed_rr),
            "adaptive_mrr": sum(adapted_rr) / len(adapted_rr),
            "delta_mrr": sum(adapted_rr) / len(adapted_rr) - sum(fixed_rr) / len(fixed_rr),
            "model_weights_changed": False,
            "claim_boundary": "software fixture comparison only; no demonstrated real-model or broad retrieval improvement",
        }
