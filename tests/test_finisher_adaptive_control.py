"""Pre-registered disjoint synthetic feedback controls; no model weight training."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from beastbox.adaptive_control import AdaptiveControl
from beastbox.memory import ReconciliationMemory
from beastbox.reality_memory import initial_r12_state
from beastbox.refractive_memory import RefractiveMemoryRouter, WEIGHTS


def _corpus(tmp_path):
    memory = ReconciliationMemory(tmp_path / "feedback.sqlite3")
    ids = [
        memory.store("Amber pine sawmill construction guide.", kind="fixture"),
        memory.store("Blue sea turtle migration and nesting atlas.", kind="fixture"),
        memory.store("Violet orchid indoor watering calendar.", kind="fixture"),
        memory.store("Orange solar panel installation specifications.", kind="fixture"),
        memory.store("Red alpine mountain climbing weather forecast.", kind="fixture"),
    ]
    adapter = SimpleNamespace(memory=memory)
    controller = AdaptiveControl(
        RefractiveMemoryRouter(adapter), r12_state=initial_r12_state(), dyn12=[0.0] * 12,
    )
    return memory, controller, ids


def _review(query, memory_id):
    return {"query": query, "preferred_memory_id": memory_id, "reviewed": True}


def test_reviewed_fit_uses_disjoint_holdout_without_claiming_real_gain(tmp_path):
    memory, model, ids = _corpus(tmp_path)
    try:
        before = memory.stats().copy()
        trained = model.fit([
            _review("amber sawmill", ids[0]),
            _review("blue nesting sea turtle", ids[1]),
            _review("orchid watering violet", ids[2]),
        ])
        report = model.evaluate([
            _review("pine construction instructions", ids[0]),
            _review("sea turtle migration atlas", ids[1]),
            _review("calendar for indoor orchids", ids[2]),
            _review("solar installation orange", ids[3]),
            _review("alpine weather mountain climbing", ids[4]),
        ])
        assert trained["trained_model_weights"] is False
        assert trained["examples"] == 3
        assert trained["frozen_weights"] == WEIGHTS
        assert set(trained["learned_weights"]) == set(WEIGHTS)
        assert sum(trained["learned_weights"].values()) == pytest.approx(1)
        assert report["model_weights_changed"] is False
        assert report["samples"] == 5
        assert set(report["training_query_sha256"]).isdisjoint(report["heldout_query_sha256"])
        assert 0 <= report["frozen_mrr"] <= 1
        assert 0 <= report["adaptive_mrr"] <= 1
        assert report["delta_mrr"] == pytest.approx(report["adaptive_mrr"] - report["frozen_mrr"])
        assert memory.stats() == before
        assert WEIGHTS == trained["frozen_weights"]
    finally:
        memory.close()


def test_invalid_training_evidence_fails_without_partial_learning(tmp_path):
    memory, model, ids = _corpus(tmp_path)
    try:
        with pytest.raises(ValueError, match="reviewed"):
            model.fit([_review("valid first", ids[0]),
                       {"query": "invalid second", "preferred_memory_id": ids[1], "reviewed": False}])
        assert model.weights == WEIGHTS
        assert model._trained is False
        with pytest.raises(ValueError, match="repeated"):
            model.fit([_review("same query", ids[0]), _review("same query", ids[1])])
        assert model.weights == WEIGHTS
    finally:
        memory.close()


def test_holdout_query_leakage_fails_closed(tmp_path):
    memory, model, ids = _corpus(tmp_path)
    try:
        model.fit([_review("amber sawmill", ids[0]), _review("violet orchid", ids[2])])
        with pytest.raises(ValueError, match="leakage"):
            model.evaluate([_review("amber sawmill", ids[0])])
        with pytest.raises(RuntimeError, match="already fitted"):
            model.fit([_review("new query", ids[0]), _review("fresh topic", ids[2])])
    finally:
        memory.close()


def test_unfitted_control_has_no_claimed_heldout_result(tmp_path):
    memory, model, ids = _corpus(tmp_path)
    try:
        with pytest.raises(RuntimeError, match="fit"):
            model.evaluate([_review("solar orange", ids[3])])
        with pytest.raises(ValueError, match="relevant id"):
            model.fit([_review("violet orchid", 99999), _review("solar orange", ids[3])])
        assert model.weights == WEIGHTS
        assert model._trained is False
    finally:
        memory.close()
