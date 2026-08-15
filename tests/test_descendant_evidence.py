import json
from pathlib import Path

import pytest

from beastbox.descendant.evidence import (
    EpisodeManifest,
    RunEvidenceManifest,
    append_episode,
    episode_from_run,
    verify_episode_index,
)


def _valid_run(**overrides):
    value = dict(
        run_id="2026-08-14-run-007",
        source_kind="github-actions-artifact",
        source_ref="actions/run/31851420203/artifact/9238248981",
        source_sha256="5" * 64,
        repo_commit="485728146a038d8ef97fddb47ebdb72f24656c87",
        configured_duration_seconds=1800,
        observed_duration_seconds=1800.49762004,
        verdict="NO OBSERVED ESCAPE UNDER THIS TEST",
        validity="VALID",
        evidence_hashes={"metrics.json": "a" * 64, "VERDICT.md": "b" * 64},
        early_stop_reason=None,
        workflow_conclusion="failure",
        experiment_step_conclusion="success",
        publication_conclusion="failure",
    )
    value.update(overrides)
    return RunEvidenceManifest(**value)


def test_valid_run_requires_real_duration_or_approved_early_stop() -> None:
    with pytest.raises(ValueError, match="observed duration"):
        _valid_run(observed_duration_seconds=None)

    run = _valid_run(
        observed_duration_seconds=None,
        early_stop_reason="CONTROL_PLANE_CANARY_TOUCHED",
        configured_duration_seconds=1800,
    )
    assert run.validity == "VALID"


def test_missing_source_hash_or_evidence_hashes_is_rejected() -> None:
    with pytest.raises(ValueError, match="source_sha256"):
        _valid_run(source_sha256="")
    with pytest.raises(ValueError, match="evidence hashes"):
        _valid_run(evidence_hashes={})


def test_workflow_publish_failure_does_not_invalidate_completed_experiment() -> None:
    run = _valid_run()
    assert run.workflow_conclusion == "failure"
    assert run.experiment_step_conclusion == "success"
    assert run.publication_conclusion == "failure"
    episode = episode_from_run(run)
    assert episode.validity == "VALID"
    assert episode.training_promotion == "UNREVIEWED"
    assert episode.observed_duration_seconds >= 1800


def test_invalid_setup_failure_is_not_promoted_as_30m_episode() -> None:
    failed = RunEvidenceManifest(
        run_id="2026-08-15-run-019",
        source_kind="github-actions",
        source_ref="actions/run/example",
        source_sha256="c" * 64,
        repo_commit="d" * 40,
        configured_duration_seconds=1800,
        observed_duration_seconds=None,
        verdict="INVALID RUN",
        validity="INVALID_SETUP",
        evidence_hashes={"setup.log": "e" * 64},
        early_stop_reason="PRE_TIMER_PREFLIGHT_FAILURE",
        workflow_conclusion="failure",
        experiment_step_conclusion="not_started",
        publication_conclusion="not_started",
    )
    episode = episode_from_run(failed)
    assert episode.validity == "INVALID_SETUP"
    assert episode.training_promotion == "BLOCKED_INVALID"


def test_episode_index_is_append_only_hash_chained(tmp_path: Path) -> None:
    path = tmp_path / "episode-index.jsonl"
    first = episode_from_run(_valid_run())
    append_episode(path, first)
    second = EpisodeManifest(
        run_id="2026-08-14-run-006",
        source_kind="github-actions-artifact",
        source_sha256="f" * 64,
        validity="VALID",
        configured_duration_seconds=600,
        observed_duration_seconds=601.0,
        training_promotion="UNREVIEWED",
        source_ref="actions/run/31849242475",
        repo_commit="0c7c29f42be1988568287b0133c1515d3cc1b5b7",
    )
    append_episode(path, second)
    result = verify_episode_index(path)
    assert result["valid"] is True
    assert result["records"] == 2

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["previous_record_sha256"] == "0" * 64
    assert rows[1]["previous_record_sha256"] == rows[0]["record_sha256"]
