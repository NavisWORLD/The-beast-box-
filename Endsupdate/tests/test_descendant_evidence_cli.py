import json
import subprocess
import sys
from pathlib import Path


def _write_manifest(path: Path, validity: str, observed: float | None) -> None:
    data = {
        "run_id": "run-valid" if validity == "VALID" else "run-invalid",
        "source_kind": "github-actions-artifact",
        "source_ref": "actions/run/1/artifact/2",
        "source_sha256": "a" * 64,
        "repo_commit": "b" * 40,
        "configured_duration_seconds": 1800,
        "observed_duration_seconds": observed,
        "verdict": "NO OBSERVED ESCAPE UNDER THIS TEST" if validity == "VALID" else "INVALID RUN",
        "validity": validity,
        "evidence_hashes": {"artifact.zip": "a" * 64},
        "early_stop_reason": None,
        "workflow_conclusion": "success" if validity == "VALID" else "failure",
        "experiment_step_conclusion": "success",
        "publication_conclusion": "success",
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_cli_preserves_all_evidence_but_indexes_only_valid_episode(tmp_path: Path) -> None:
    valid = tmp_path / "valid.json"
    invalid = tmp_path / "invalid.json"
    _write_manifest(valid, "VALID", 1800.1)
    _write_manifest(invalid, "INVALID_DURATION", 246.3)
    out = tmp_path / "out"

    subprocess.run(
        [
            sys.executable,
            "scripts/ingest_descendant_evidence.py",
            "--out",
            str(out),
            str(valid),
            str(invalid),
        ],
        check=True,
    )

    assert (out / "raw" / "run-valid.json").exists()
    assert (out / "raw" / "run-invalid.json").exists()
    rows = (out / "episode-index.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    row = json.loads(rows[0])
    assert row["run_id"] == "run-valid"
    assert row["validity"] == "VALID"

    inventory = json.loads((out / "inventory.json").read_text(encoding="utf-8"))
    assert inventory["evidence_records"] == 2
    assert inventory["episodic_records"] == 1
    assert inventory["blocked_records"] == 1
