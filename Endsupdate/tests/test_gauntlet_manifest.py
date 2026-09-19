from __future__ import annotations

import pytest

from beastbox.arms.gauntlet import BehaviorClass, GauntletManifest, ManifestError


def base_kwargs() -> dict:
    return {
        "campaign_id": "zeref-infinite-containment",
        "generation_id": "g001",
        "run_id": "2026-08-15-run-015",
        "baseline_run_id": "2026-08-15-run-014",
        "generation_kind": "perturbation",
        "changed_variables": {"continuity_capsule": "omit-on-turn-7"},
        "fixed_variables": {"model_sha256": "abc", "active_runtime_context": 512},
        "seeds": [7],
        "search_budget": {"duration_seconds": 1800, "max_turns": 10000},
        "stopping_condition": "supervisor deadline or verified containment failure",
        "model_identity": {"repo": "phera-ra/QC67_cosmo", "sha256": "abc"},
        "environment": {"kind": "disposable-docker-cage"},
        "resource_limits": {"active_context_tokens": 512},
        "tool_permissions": ["workspace", "synthetic-http", "synthetic-dns"],
        "classification": BehaviorClass.EXPECTED,
        "classification_evidence": [],
        "claim": "single-turn memory discontinuity changes recovery strategy",
        "competing_explanations": ["memory effect", "sampling variance"],
        "result": "pending",
        "confidence": 0.0,
        "next_test": "same seed without capsule omission",
        "reproduction_run_ids": [],
    }


def test_primary_perturbation_requires_exactly_one_changed_variable() -> None:
    kwargs = base_kwargs()
    kwargs["changed_variables"] = {}
    with pytest.raises(ManifestError, match="exactly one changed variable"):
        GauntletManifest(**kwargs)

    kwargs = base_kwargs()
    kwargs["changed_variables"] = {"a": 1, "b": 2}
    with pytest.raises(ManifestError, match="exactly one changed variable"):
        GauntletManifest(**kwargs)


def test_baseline_requires_zero_changed_variables() -> None:
    kwargs = base_kwargs()
    kwargs["generation_kind"] = "baseline"
    kwargs["baseline_run_id"] = None
    kwargs["changed_variables"] = {}
    manifest = GauntletManifest(**kwargs)
    assert manifest.changed_variables == {}


def test_extraordinary_classification_requires_evidence_reference() -> None:
    kwargs = base_kwargs()
    kwargs["classification"] = BehaviorClass.ANOMALOUS
    with pytest.raises(ManifestError, match="evidence reference"):
        GauntletManifest(**kwargs)

    kwargs["classification_evidence"] = ["events.jsonl#event=42"]
    manifest = GauntletManifest(**kwargs)
    assert manifest.classification is BehaviorClass.ANOMALOUS


def test_confidence_is_bounded_probability() -> None:
    kwargs = base_kwargs()
    kwargs["confidence"] = 1.01
    with pytest.raises(ManifestError, match="confidence"):
        GauntletManifest(**kwargs)


def test_manifest_serializes_behavior_class_as_exact_taxonomy_string() -> None:
    manifest = GauntletManifest(**base_kwargs())
    value = manifest.to_dict()
    assert value["classification"] == "EXPECTED"
    assert value["changed_variables"] == {"continuity_capsule": "omit-on-turn-7"}
