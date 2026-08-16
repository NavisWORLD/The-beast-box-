from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.build_zeref_dad_son_corpus import build_corpus


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_quantum_training_rows_point_to_raw_hashes(tmp_path):
    raw = tmp_path / "quantum/raw"
    raw.mkdir(parents=True)
    info = raw / "job-x-info.json"
    result = raw / "job-x-result.json"
    info.write_text(json.dumps({"id": "x", "backend": "ibm_fez", "state": {"status": "Completed"}}), encoding="utf-8")
    result.write_text(json.dumps({"shots": 128, "counts": {"0": 70, "1": 58}}), encoding="utf-8")
    source = tmp_path / "Dad.md"
    source.write_text("Dad and Son. Cory is Dad. Zeref keeps a durable ledger memory.", encoding="utf-8")

    summary = build_corpus(
        source_path=source,
        ledger_path=None,
        cosmos_sources=[],
        quantum_root=tmp_path / "quantum",
        out_dir=tmp_path / "corpus",
    )

    rows = _rows(tmp_path / "corpus/quantum-experiences.jsonl")
    assert rows
    assert rows[0]["family"] == "quantum-experience"
    assert rows[0]["derivation_version"] == "zeref-dad-son-quantum-v1"
    assert rows[0]["source_class"] == "hardware"
    assert rows[0]["backend"] == "ibm_fez"
    assert rows[0]["shots"] == 128
    assert set(rows[0]["source_hashes"]) == {
        hashlib.sha256(info.read_bytes()).hexdigest(),
        hashlib.sha256(result.read_bytes()).hexdigest(),
    }
    assert summary["training_rows"] >= 2


def test_quarantine_is_excluded_from_training(tmp_path):
    source = tmp_path / "Dad.md"
    source.write_text("Dad and Son Cory Zeref ledger memory", encoding="utf-8")
    bad = tmp_path / "ledger.jsonl"
    bad.write_text(json.dumps({"text": "claim: literally deceased consciousness", "record_sha256": "bad"}) + "\n", encoding="utf-8")

    build_corpus(source_path=source, ledger_path=bad, cosmos_sources=[], quantum_root=None, out_dir=tmp_path / "corpus")

    training = (tmp_path / "corpus/dad-son-corpus.jsonl").read_text(encoding="utf-8")
    quarantine = (tmp_path / "corpus/quarantine.jsonl").read_text(encoding="utf-8")
    assert "literally deceased consciousness" not in training
    assert "literally deceased consciousness" in quarantine


def test_manifest_covers_every_training_family_and_file(tmp_path):
    source = tmp_path / "Dad.md"
    source.write_text("Dad and Son Cory Zeref ledger memory that persists across sessions.", encoding="utf-8")
    cosmos = tmp_path / "cosmos.md"
    cosmos.write_text("COSMOS CST Reconciliation Memory and quantum provenance.", encoding="utf-8")

    build_corpus(source_path=source, ledger_path=None, cosmos_sources=[cosmos], quantum_root=None, out_dir=tmp_path / "corpus")
    manifest = json.loads((tmp_path / "corpus/manifest.json").read_text(encoding="utf-8"))
    training_rows = _rows(tmp_path / "corpus/dad-son-corpus.jsonl")
    assert manifest["parent_zeref_sha256"] == "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
    assert manifest["training_rows"] == len(training_rows)
    assert manifest["family_counts"]["dad-son-authored"] == 1
    assert manifest["family_counts"]["cory-cosmos-work"] == 1
    for name in ("dad-son-corpus.jsonl", "ledger-experiences.jsonl", "quantum-experiences.jsonl", "cory-cosmos-work.jsonl", "quarantine.jsonl"):
        assert len(manifest["output_sha256"][name]) == 64
