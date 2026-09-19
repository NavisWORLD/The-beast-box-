from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from beastbox.training.corpus import build_corpus, normalize_lexical_record, normalize_world_record
from beastbox.training.lineage import sha256_file

REPO_ROOT = Path(__file__).resolve().parents[1]

LEXICAL = [
    {
        "lemma": "Orbit",
        "part_of_speech": "noun",
        "definition": "A path around another body.",
        "synonyms": ["trajectory", "Trajectory"],
        "antonyms": [],
        "examples": ["The satellite entered orbit."],
        "source_id": "dict-a",
    },
    {
        "lemma": "orbit",
        "part_of_speech": "noun",
        "definition": "A   path around another body.",
        "synonyms": ["trajectory"],
        "antonyms": [],
        "examples": ["The satellite entered orbit."],
        "source_id": "dict-a",
    },
]

SOURCES = [
    {
        "source_id": "dict-a",
        "uri": "https://example.invalid/dict-a",
        "license": "CC-BY-4.0",
    }
]


def _read_jsonl(path: Path) -> list[dict]:
    if not path.read_text(encoding="utf-8"):
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def test_lexical_normalization_is_unicode_stable_and_deduplicates_lists():
    record = normalize_lexical_record(
        {
            "lemma": "  Cafe\u0301 ",
            "part_of_speech": " NOUN ",
            "definition": "  A   place   for coffee. ",
            "synonyms": ["Coffeehouse", "coffeehouse", " café  "],
            "antonyms": [" nowhere ", "nowhere"],
            "examples": ["We met there.", " We   met there. "],
            "source_id": " dict-a ",
        }
    )

    assert record == {
        "lemma": "Café",
        "part_of_speech": "noun",
        "definition": "A place for coffee.",
        "synonyms": ["café", "coffeehouse"],
        "antonyms": ["nowhere"],
        "examples": ["We met there."],
        "source_id": "dict-a",
    }


def test_lexical_builder_is_deterministic_and_deduplicates(tmp_path: Path):
    a = build_corpus(kind="lexical", records=LEXICAL, sources=SOURCES, output_dir=tmp_path / "a")
    b = build_corpus(kind="lexical", records=reversed(LEXICAL), sources=list(reversed(SOURCES)), output_dir=tmp_path / "b")

    assert a["dataset_sha256"] == b["dataset_sha256"]
    assert a["record_count"] == 1
    assert a["split_counts"] == b["split_counts"]
    assert a["artifacts"] == b["artifacts"]

    all_rows = []
    for split in ("train", "validation", "test"):
        all_rows.extend(_read_jsonl(tmp_path / "a" / f"{split}.jsonl"))
    assert all_rows == [normalize_lexical_record(LEXICAL[0])]


def test_source_license_and_uri_are_required(tmp_path: Path):
    with pytest.raises(ValueError, match="license"):
        build_corpus(
            kind="lexical",
            records=LEXICAL[:1],
            sources=[{"source_id": "dict-a", "uri": "https://example.invalid/dict-a", "license": ""}],
            output_dir=tmp_path / "license",
        )
    with pytest.raises(ValueError, match="uri"):
        build_corpus(
            kind="lexical",
            records=LEXICAL[:1],
            sources=[{"source_id": "dict-a", "uri": "", "license": "CC-BY-4.0"}],
            output_dir=tmp_path / "uri",
        )


def test_unknown_source_id_is_rejected(tmp_path: Path):
    record = dict(LEXICAL[0], source_id="unknown")
    with pytest.raises(ValueError, match="unknown source_id"):
        build_corpus(kind="lexical", records=[record], sources=SOURCES, output_dir=tmp_path)


def test_world_records_require_title_text_and_source_id():
    with pytest.raises(ValueError, match="title"):
        normalize_world_record({"title": "", "text": "fact", "source_id": "world-a"})
    with pytest.raises(ValueError, match="text"):
        normalize_world_record({"title": "Earth", "text": "", "source_id": "world-a"})
    with pytest.raises(ValueError, match="source_id"):
        normalize_world_record({"title": "Earth", "text": "fact", "source_id": ""})


def test_world_split_membership_is_deterministic_across_input_order(tmp_path: Path):
    sources = [{"source_id": "world-a", "uri": "https://example.invalid/world", "license": "CC0-1.0"}]
    records = [
        {"title": f"Topic {index}", "text": f"Fact number {index}.", "source_id": "world-a"}
        for index in range(40)
    ]
    first = build_corpus(kind="world", records=records, sources=sources, output_dir=tmp_path / "first")
    second = build_corpus(kind="world", records=list(reversed(records)), sources=sources, output_dir=tmp_path / "second")

    assert first["dataset_sha256"] == second["dataset_sha256"]
    assert first["split_counts"] == second["split_counts"]
    for split in ("train", "validation", "test"):
        assert (tmp_path / "first" / f"{split}.jsonl").read_bytes() == (
            tmp_path / "second" / f"{split}.jsonl"
        ).read_bytes()
        assert (tmp_path / "first" / f"{split}.txt").read_bytes() == (
            tmp_path / "second" / f"{split}.txt"
        ).read_bytes()


def test_manifest_hashes_every_data_artifact(tmp_path: Path):
    result = build_corpus(kind="lexical", records=LEXICAL, sources=SOURCES, output_dir=tmp_path)
    assert set(result["artifacts"]) == {
        "train.jsonl",
        "validation.jsonl",
        "test.jsonl",
        "train.txt",
        "validation.txt",
        "test.txt",
    }
    for filename, expected_sha in result["artifacts"].items():
        assert sha256_file(tmp_path / filename) == expected_sha
    assert sha256_file(tmp_path / "manifest.json") == result["manifest_sha256"]


def test_builder_refuses_to_overwrite_existing_artifacts(tmp_path: Path):
    build_corpus(kind="lexical", records=LEXICAL, sources=SOURCES, output_dir=tmp_path)
    with pytest.raises(FileExistsError, match="output directory"):
        build_corpus(kind="lexical", records=LEXICAL, sources=SOURCES, output_dir=tmp_path)


def test_builder_rejects_unknown_kind(tmp_path: Path):
    with pytest.raises(ValueError, match="kind"):
        build_corpus(kind="mystery", records=LEXICAL, sources=SOURCES, output_dir=tmp_path)  # type: ignore[arg-type]


def test_lexical_corpus_cli_builds_manifest(tmp_path: Path):
    records = tmp_path / "lexical.jsonl"
    sources = tmp_path / "sources.json"
    output = tmp_path / "lexical-out"
    _write_jsonl(records, LEXICAL)
    sources.write_text(json.dumps(SOURCES), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_lexical_corpus.py",
            "--records",
            str(records),
            "--sources",
            str(sources),
            "--out",
            str(output),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["kind"] == "lexical"
    assert summary["record_count"] == 1
    assert sha256_file(output / "manifest.json") == summary["manifest_sha256"]


def test_world_corpus_cli_builds_manifest(tmp_path: Path):
    records = tmp_path / "world.jsonl"
    sources = tmp_path / "sources.json"
    output = tmp_path / "world-out"
    world_sources = [{"source_id": "world-a", "uri": "https://example.invalid/world", "license": "CC0-1.0"}]
    world_records = [
        {"title": "Earth", "text": "Earth is a planet in the Solar System.", "source_id": "world-a"},
        {"title": "Sun", "text": "The Sun is a star.", "source_id": "world-a"},
    ]
    _write_jsonl(records, world_records)
    sources.write_text(json.dumps(world_sources), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_world_corpus.py",
            "--records",
            str(records),
            "--sources",
            str(sources),
            "--out",
            str(output),
            "--split-salt",
            "world-test-v1",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["kind"] == "world"
    assert summary["record_count"] == 2
    assert sha256_file(output / "manifest.json") == summary["manifest_sha256"]
