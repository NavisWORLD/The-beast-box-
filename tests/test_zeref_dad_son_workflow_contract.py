from pathlib import Path
import hashlib
import json


def test_zeref_dad_son_workflow_pins_lineage_and_runs_full_pipeline():
    text = Path(".github/workflows/zeref-dad-son-001.yml").read_text(encoding="utf-8")
    required = (
        "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6",
        "b414724c627300c41b099dcc6853766d08fd27a4",
        "31910785892",
        "dddb1325b90c9abbe8da77974874e5770623035e",
        "workloads (4)",
        "build_zeref_dad_son_corpus.py",
        "run_d001_stage.py",
        "run_zeref_dad_son_chat.py",
        "zeref-dad-son-001-${{ github.run_id }}",
        "sha256sum",
        "resume_probe",
    )
    for value in required:
        assert value in text


def test_workflow_is_additive_and_does_not_push_or_mutate_parent():
    text = Path(".github/workflows/zeref-dad-son-001.yml").read_text(encoding="utf-8")
    assert "persist-credentials: false" in text
    assert "contents: read" in text
    assert "git push" not in text
    assert "--force" not in text
    assert "rm -f _dadson/parent/weights/cosmos-cst.gguf" not in text


def test_artifact_checksum_manifests_exclude_transient_huggingface_caches():
    text = Path(".github/workflows/zeref-dad-son-001.yml").read_text(encoding="utf-8")
    assert text.count("! -path '*/.cache/*'") >= 2


def test_artifact_checksums_are_written_relative_to_uploaded_root():
    text = Path(".github/workflows/zeref-dad-son-001.yml").read_text(encoding="utf-8")
    assert text.count("cd _dadson &&") >= 3
    assert "find . -type f" in text
    assert "find quantum -type f" in text


def test_future_runs_restore_latest_durable_ledger_before_appending():
    text = Path(".github/workflows/zeref-dad-son-001.yml").read_text(encoding="utf-8")
    assert "memory/ledger-manifest.json" in text
    assert "ledger-snapshots" in text
    assert "restore_snapshot()" in text
    assert "dad-son-resume" in text


def test_memory_stage_uses_promoted_ledger_corpus_not_raw_unreviewed_ledger():
    text = Path(".github/workflows/zeref-dad-son-001.yml").read_text(encoding="utf-8")
    assert "ledger-experiences.jsonl" in text
    assert "dad-son-memory-training.txt" in text


def test_forever_memory_snapshot_chain_is_complete_and_hashes_to_manifest():
    manifest = json.loads(Path("experiments/zeref-dad-son-001/memory/ledger-manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"].startswith("zeref-dad-son-ledger-manifest-v")
    chain = manifest["snapshot_chain"]
    assert isinstance(chain, list) and chain
    combined = b""
    records = 0
    expected_first_id = 1
    previous_last_hash = None
    for segment in chain:
        source = Path(segment["path"])
        data = source.read_bytes()
        assert hashlib.sha256(data).hexdigest() == segment["sha256"]
        rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
        assert len(rows) == segment["record_count"]
        assert rows[0]["memory_id"] == segment["first_memory_id"] == expected_first_id
        assert rows[-1]["memory_id"] == segment["last_memory_id"]
        assert rows[-1]["record_sha256"] == segment["last_record_sha256"]
        if previous_last_hash is not None:
            assert rows[0]["previous_record_sha256"] == previous_last_hash
        previous_last_hash = rows[-1]["record_sha256"]
        expected_first_id = rows[-1]["memory_id"] + 1
        combined += data
        records += len(rows)
    assert records == manifest["record_count"]
    assert previous_last_hash == manifest["last_record_sha256"]
    assert hashlib.sha256(combined).hexdigest() == manifest["combined_ledger_sha256"]
