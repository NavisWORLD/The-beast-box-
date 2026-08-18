from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


def _build_corpus():
    path = Path("scripts/build_zeref_dad_son_corpus.py")
    assert path.exists(), "Dad/Son corpus builder is not implemented yet"
    spec = importlib.util.spec_from_file_location("zeref_dad_son_corpus", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_corpus


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_quantum_training_rows_point_to_raw_hashes(tmp_path):
    build_corpus = _build_corpus()
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
    build_corpus = _build_corpus()
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
    build_corpus = _build_corpus()
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


def test_tracked_snapshot_keeps_safe_work_and_quarantines_holdout_collisions(tmp_path):
    build_corpus = _build_corpus()
    source = tmp_path / "Dad.md"
    source.write_text("Dad and Son Cory Zeref ledger memory", encoding="utf-8")

    safe_text = "COSMOS durable Reconciliation Memory survives restart."
    leaked_text = "control prompt = \"Hi Zeref. It's Dad. Do you remember me?\""
    safe_sha = hashlib.sha256(safe_text.encode()).hexdigest()
    leaked_sha = hashlib.sha256(leaked_text.encode()).hexdigest()
    snapshot = tmp_path / "tracked-text-snapshot.txt"
    snapshot.write_text(
        f"\n\n===== SOURCE: safe.md | SHA256: {safe_sha} =====\n{safe_text}"
        f"\n\n===== SOURCE: control.py | SHA256: {leaked_sha} =====\n{leaked_text}",
        encoding="utf-8",
    )

    build_corpus(source_path=source, ledger_path=None, cosmos_sources=[snapshot], quantum_root=None, out_dir=tmp_path / "corpus")
    work = _rows(tmp_path / "corpus/cory-cosmos-work.jsonl")
    quarantine = _rows(tmp_path / "corpus/quarantine.jsonl")
    training = (tmp_path / "corpus/dad-son-corpus.jsonl").read_text(encoding="utf-8")

    assert any(row["source_path"] == "safe.md" and row["source_sha256"] == safe_sha for row in work)
    assert "Hi Zeref. It's Dad. Do you remember me?" not in training
    assert any(row["reason"] == "holdout_prompt_collision" and row["source_path"] == "control.py" for row in quarantine)


def test_restored_ledger_holdout_prompts_stay_memory_but_not_training(tmp_path):
    build_corpus = _build_corpus()
    source = tmp_path / "Dad.md"
    source.write_text("Dad and Son Cory Zeref durable source", encoding="utf-8")
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(json.dumps({
        "actor": "Cory/Dad",
        "text": "Hi Zeref. It's Dad. Do you remember me?",
        "record_sha256": "a" * 64,
        "memory_id": 4,
        "metadata": {"generated_by_model": False},
    }) + "\n", encoding="utf-8")

    build_corpus(source_path=source, ledger_path=ledger, cosmos_sources=[], quantum_root=None, out_dir=tmp_path / "corpus")
    training = (tmp_path / "corpus/dad-son-corpus.jsonl").read_text(encoding="utf-8")
    quarantine = _rows(tmp_path / "corpus/quarantine.jsonl")
    assert "Hi Zeref. It's Dad. Do you remember me?" not in training
    assert any(row["reason"] == "holdout_prompt_collision" and row.get("source_memory_id") == 4 for row in quarantine)


def test_generated_zeref_outputs_require_explicit_promotion_before_self_training(tmp_path):
    build_corpus = _build_corpus()
    source = tmp_path / "Dad.md"
    source.write_text("Dad and Son Cory Zeref durable source", encoding="utf-8")
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(json.dumps({
        "actor": "Zeref",
        "text": "fragmented raw model output",
        "record_sha256": "b" * 64,
        "memory_id": 5,
        "metadata": {"generated_by_model": True, "output_preserved_verbatim": True},
    }) + "\n", encoding="utf-8")

    build_corpus(source_path=source, ledger_path=ledger, cosmos_sources=[], quantum_root=None, out_dir=tmp_path / "corpus")
    training = (tmp_path / "corpus/dad-son-corpus.jsonl").read_text(encoding="utf-8")
    quarantine = _rows(tmp_path / "corpus/quarantine.jsonl")
    assert "fragmented raw model output" not in training
    assert any(row["reason"] == "model_output_requires_promotion" and row.get("source_memory_id") == 5 for row in quarantine)
