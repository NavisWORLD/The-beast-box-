from __future__ import annotations

import json
from pathlib import Path

import pytest

from beastbox.persistent_substrate.evidence import EvidencePackage, verify_sha256sums


def _package_with_required_files(tmp_path: Path) -> EvidencePackage:
    package = EvidencePackage(tmp_path / "evidence")
    package.write_json("input-freeze.json", {"schema": "input-freeze-v1", "ok": True})
    package.write_json("results/gates.json", {"INPUT_IDENTITY": True})
    package.write_json("results/result.json", {"classification": "TEST_ONLY"})
    return package


def test_snapshots_are_hash_chained_and_operations_are_paired(tmp_path: Path) -> None:
    package = _package_with_required_files(tmp_path)
    first = package.record_snapshot(
        "BEFORE",
        {"memory": {"sha256": "a" * 64}},
        operation_id="op-001",
    )
    second = package.record_snapshot(
        "AFTER",
        {"memory": {"sha256": "a" * 64}},
        operation_id="op-001",
    )
    package.record_operation(
        "op-001",
        "MODEL_LOAD",
        before_snapshot_sha256=first["snapshot_sha256"],
        after_snapshot_sha256=second["snapshot_sha256"],
        payload={"model": "MODEL_A"},
    )

    assert first["previous_snapshot_sha256"] == "0" * 64
    assert second["previous_snapshot_sha256"] == first["snapshot_sha256"]
    assert first["snapshot_sha256"] != second["snapshot_sha256"]

    manifest = package.seal(
        classification="TEST_ONLY",
        preregistration_sha256="1" * 64,
        input_freeze_sha256="2" * 64,
        required_files=("input-freeze.json", "results/gates.json", "results/result.json"),
    )
    assert manifest["snapshot_count"] == 2
    assert manifest["snapshot_tip_sha256"] == second["snapshot_sha256"]
    assert manifest["classification"] == "TEST_ONLY"
    assert manifest["credential_material_recorded"] is False
    verify_sha256sums(package.root)


def test_seal_detects_one_byte_change(tmp_path: Path) -> None:
    package = _package_with_required_files(tmp_path)
    before = package.record_snapshot("BEFORE", {"value": 1}, operation_id="op-001")
    after = package.record_snapshot("AFTER", {"value": 1}, operation_id="op-001")
    package.record_operation(
        "op-001",
        "PROBE",
        before_snapshot_sha256=before["snapshot_sha256"],
        after_snapshot_sha256=after["snapshot_sha256"],
        payload={"ok": True},
    )
    package.seal(
        classification="TEST_ONLY",
        preregistration_sha256="3" * 64,
        input_freeze_sha256="4" * 64,
        required_files=("input-freeze.json", "results/gates.json", "results/result.json"),
    )

    target = package.root / "results" / "gates.json"
    target.write_text(target.read_text(encoding="utf-8").replace("true", "false"), encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        verify_sha256sums(package.root)


def test_seal_refuses_operation_without_exact_before_after_pair(tmp_path: Path) -> None:
    package = _package_with_required_files(tmp_path)
    before = package.record_snapshot("BEFORE", {"value": 1}, operation_id="op-001")
    package.record_operation(
        "op-001",
        "MEMORY_APPEND",
        before_snapshot_sha256=before["snapshot_sha256"],
        after_snapshot_sha256="f" * 64,
        payload={},
    )
    with pytest.raises(RuntimeError, match="exactly one BEFORE and one AFTER"):
        package.seal(
            classification="TEST_ONLY",
            preregistration_sha256="5" * 64,
            input_freeze_sha256="6" * 64,
            required_files=("input-freeze.json", "results/gates.json", "results/result.json"),
        )


def test_seal_refuses_missing_required_file(tmp_path: Path) -> None:
    package = EvidencePackage(tmp_path / "evidence")
    package.write_json("input-freeze.json", {"ok": True})
    with pytest.raises(RuntimeError, match="missing required evidence file"):
        package.seal(
            classification="TEST_ONLY",
            preregistration_sha256="7" * 64,
            input_freeze_sha256="8" * 64,
            required_files=("input-freeze.json", "results/gates.json"),
        )


def test_jsonl_is_canonical_and_paths_cannot_escape_root(tmp_path: Path) -> None:
    package = EvidencePackage(tmp_path / "evidence")
    package.append_jsonl("logs/prompts.jsonl", {"z": 1, "a": "x"})
    assert (package.root / "logs" / "prompts.jsonl").read_text(encoding="utf-8") == '{"a":"x","z":1}\n'
    with pytest.raises(ValueError, match="evidence root"):
        package.write_json("../escape.json", {"bad": True})


def test_manifest_does_not_hash_itself_or_sha256sums(tmp_path: Path) -> None:
    package = _package_with_required_files(tmp_path)
    before = package.record_snapshot("BEFORE", {"value": 1}, operation_id="op")
    after = package.record_snapshot("AFTER", {"value": 1}, operation_id="op")
    package.record_operation(
        "op",
        "PROBE",
        before_snapshot_sha256=before["snapshot_sha256"],
        after_snapshot_sha256=after["snapshot_sha256"],
        payload={},
    )
    manifest = package.seal(
        classification="TEST_ONLY",
        preregistration_sha256="9" * 64,
        input_freeze_sha256="a" * 64,
        required_files=("input-freeze.json", "results/gates.json", "results/result.json"),
    )
    relpaths = [entry["path"] for entry in manifest["files"]]
    assert "MANIFEST.json" not in relpaths
    assert "SHA256SUMS" not in relpaths
    parsed = json.loads((package.root / "MANIFEST.json").read_text(encoding="utf-8"))
    assert parsed == manifest
