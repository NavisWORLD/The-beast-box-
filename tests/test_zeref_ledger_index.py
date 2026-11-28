"""Tests for scripts/zeref_ledger_index.py (TRACK 2).

All fixtures are synthetic JSONL written to tmp_path. Nothing here
touches the real ledger, the real rows file, run(), or narrate().
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from zeref_ledger_index import LedgerIndex, build_index, normalize_license


def _write(path, records):
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    return path


def _rows_file(tmp_path):
    return _write(tmp_path / "rows.jsonl", [
        {"mode": "chat", "source": "zeref-self-study-taught", "label": "TAUGHT",
         "user": "What is the fort?", "assistant": "The fort is a military construction designed.",
         "origin": "https://en.wikipedia.org/wiki/Fortification", "license": "CC-BY-SA-4.0"},
        {"mode": "chat", "source": "zeref-self-study-taught", "label": "TAUGHT",
         "user": "What is the river?", "assistant": "The river is a long flow of water.",
         "origin": "https://en.wikipedia.org/wiki/River", "license": "CC0-1.0"},
        {"mode": "chat", "source": "zeref-self-study-taught", "label": "TAUGHT",
         "user": "What is the moon?", "assistant": "The moon is a bright circle in the night sky.",
         "origin": "https://en.wikipedia.org/wiki/Moon", "license": "PUBLIC-DOMAIN"},
        {"mode": "chat", "source": "zeref-self-study-taught", "label": "TAUGHT",
         "user": "What is the fort wall?", "assistant": "The fort wall is a strong stone barrier.",
         "origin": "https://en.wikipedia.org/wiki/Fortification", "license": "CC-BY-SA-4.0"},
    ])


def _ledger_file(tmp_path):
    return _write(tmp_path / "ledger.jsonl", [
        {"schema": "zeref-self-study-ledger/v1", "question": "What is the fort?",
         "topic": "fort", "status": "studied", "license": "CC-BY-SA-4.0",
         "source_url": "https://en.wikipedia.org/wiki/Fortification",
         "taught_row": {"mode": "chat", "source": "zeref-self-study-taught", "label": "TAUGHT",
                        "user": "What is the fort?",
                        "assistant": "The fort is a military construction designed.",
                        "origin": "https://en.wikipedia.org/wiki/Fortification",
                        "license": "CC-BY-SA-4.0"}},
        {"schema": "zeref-self-study-ledger/v1", "question": "What is the river?",
         "topic": "river", "status": "search_failed:no_open_abstract",
         "license": "none", "source_url": None, "taught_row": None},
    ])


def test_indexing_synthetic_ledger_and_rows(tmp_path):
    index = build_index([_rows_file(tmp_path), _ledger_file(tmp_path)])
    assert index.stats["indexed"] == 5
    assert index.stats["lines_read"] == 6
    assert index.stats["excluded_no_taught_row"] == 1
    kinds = [row.kind for row in index.entries]
    assert kinds == ["taught"] * 5
    assert index.entries[0].user == "What is the fort?"
    assert index.entries[4].source_file.endswith("ledger.jsonl")
    assert index.entries[4].line_no == 1


def test_topic_query_returns_right_rows_in_deterministic_order(tmp_path):
    index = build_index([_rows_file(tmp_path), _ledger_file(tmp_path)])
    first = index.query("fort", max_tokens=1000)
    second = index.query("fort", max_tokens=1000)
    assert first == second
    users = [row["user"] for row in first["rows"]]
    assert users == ["What is the fort?", "What is the fort wall?", "What is the fort?"]
    assert first["matched"] == 3
    assert first["leftover"] == 0
    other = build_index([_rows_file(tmp_path), _ledger_file(tmp_path)])
    assert [r["user"] for r in other.query("fort", max_tokens=1000)["rows"]] == users
    river = index.query("river", max_tokens=1000)
    assert [row["user"] for row in river["rows"]] == ["What is the river?"]
    assert river["matched"] == 1
    assert index.query("volcano", max_tokens=1000)["matched"] == 0


def test_token_budget_respected_and_leftover_reported(tmp_path):
    index = build_index([_rows_file(tmp_path)])
    wide = index.query("fort", max_tokens=1000)
    assert wide["returned"] == 2
    assert wide["leftover"] == 0
    one_row_cost = wide["rows"][0]["tokens"]
    tight = index.query("fort", max_tokens=one_row_cost)
    assert tight["returned"] == 1
    assert tight["leftover"] == 1
    assert tight["tokens_used"] <= one_row_cost
    assert tight["tokens_used"] == one_row_cost
    assert tight["rows"][0]["user"] == "What is the fort?"
    empty = index.query("fort", max_tokens=1)
    assert empty["returned"] == 0
    assert empty["leftover"] == 2
    assert empty["tokens_used"] == 0


def test_appending_rows_grows_index_without_touching_existing(tmp_path):
    rows_path = _rows_file(tmp_path)
    index = build_index([rows_path])
    before = [(row.seq, row.user, row.assistant, row.license) for row in index.entries]
    before_hash = hashlib.sha256(rows_path.read_bytes()).hexdigest()
    with rows_path.open("a") as handle:
        handle.write(json.dumps(
            {"mode": "chat", "source": "zeref-self-study-taught", "label": "TAUGHT",
             "user": "What is the island?",
             "assistant": "The island is a small land in the water.",
             "origin": "https://en.wikipedia.org/wiki/Island",
             "license": "CC-BY-SA-4.0"}) + "\n")
    assert hashlib.sha256(rows_path.read_bytes()).hexdigest() != before_hash
    index.refresh()
    after = [(row.seq, row.user, row.assistant, row.license) for row in index.entries]
    assert after[:4] == before
    assert len(after) == 5
    assert after[4][1] == "What is the island?"
    assert index.stats["indexed"] == 5
    assert index.query("island", max_tokens=1000)["matched"] == 1
    index.refresh()
    assert len(index.entries) == 5


def test_missing_or_unrecognized_license_excluded(tmp_path):
    path = _write(tmp_path / "mixed.jsonl", [
        {"user": "What is the fort?", "assistant": "The fort is a military construction designed.",
         "license": "CC-BY-SA-4.0"},
        {"user": "What is the river?", "assistant": "The river is a long flow of water.",
         "license": "CC0-1.0"},
        {"user": "What is the moon?", "assistant": "The moon is a bright circle in the night sky.",
         "license": "PUBLIC-DOMAIN"},
        {"user": "What is the sun?", "assistant": "The sun is a bright star."},
        {"user": "What is the star?", "assistant": "The star is a bright light.",
         "license": "unknown"},
        {"user": "What is the cloud?", "assistant": "The cloud is a white shape.",
         "license": "Example"},
        {"user": "What is the rain?", "assistant": "The rain is falling water.",
         "license": "Beast Box world record (owner's own, same as repository)"},
        {"user": "What is the snow?", "assistant": "The snow is cold and white.",
         "license": "cc by-sa 4.0"},
    ])
    index = build_index([path])
    assert index.stats["indexed"] == 4
    assert index.stats["excluded_unlicensed"] == 4
    users = [row.user for row in index.entries]
    assert users == ["What is the fort?", "What is the river?",
                     "What is the moon?", "What is the snow?"]
    assert index.query("sun", max_tokens=1000)["matched"] == 0
    assert index.query("rain", max_tokens=1000)["matched"] == 0
    assert normalize_license("CC-BY-SA-4.0") == "CC-BY-SA-4.0"
    assert normalize_license("cc0") == "CC0-1.0"
    assert normalize_license("Public Domain") == "PUBLIC-DOMAIN"
    assert normalize_license(None) is None
    assert normalize_license("") is None
    assert normalize_license("unknown") is None


def test_indexing_is_read_only_and_failed_entries_yield_nothing(tmp_path):
    rows_path = _rows_file(tmp_path)
    ledger_path = _ledger_file(tmp_path)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (rows_path, ledger_path)}
    index = build_index([rows_path, ledger_path])
    index.query("fort", max_tokens=10)
    index.refresh()
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (rows_path, ledger_path)}
    assert before == after
    assert all(row.kind == "taught" for row in index.entries)
    assert "search_failed" not in [row.user for row in index.entries]


def test_malformed_lines_skipped_and_shrunk_file_refused(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text(
        '{"user": "What is the fort?", "assistant": "The fort is strong.", "license": "CC-BY-SA-4.0"}\n'
        'not json at all\n'
        '{"user": "What is the river?", "assistant": "The river flows.", "license": "CC0-1.0"}\n'
        '\n')
    index = build_index([path])
    assert index.stats["indexed"] == 2
    assert index.stats["excluded_malformed"] == 1
    assert index.stats["excluded_empty"] == 1
    path.write_text(
        '{"user": "What is the fort?", "assistant": "The fort is strong.", "license": "CC-BY-SA-4.0"}\n')
    try:
        index.refresh()
    except ValueError as exc:
        assert "shrank" in str(exc)
    else:
        raise AssertionError("refresh after history rewrite did not raise")
    assert len(index.entries) == 2


def test_no_em_dashes_in_module_text(tmp_path):
    module = Path(__file__).resolve().parents[1] / "scripts" / "zeref_ledger_index.py"
    assert "\u2014" not in module.read_text()
    assert "\u2014" not in Path(__file__).read_text()
