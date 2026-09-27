"""No-network preflight for source-bound real-model retrieval evaluation."""
from __future__ import annotations

import io
import json
import zipfile

import pytest

from scripts.semantic_real_eval import (
    QUERY_COUNT, load_scifact_zip, metric_summary, select_documents, select_queries,
)


def test_frozen_metrics_reward_only_judged_results():
    result = metric_summary([(["bad", "good", "also_good"], {"good", "also_good"})])
    assert result == {"mrr_at_10": 0.5, "recall_at_5": 1.0}
    assert metric_summary([(["bad"], {"good"})]) == {"mrr_at_10": 0.0, "recall_at_5": 0.0}


def test_fixed_query_and_positive_enriched_source_policy():
    corpus = {f"d{i:03}": "independent fixture" for i in range(600)}
    queries = {f"q{i:03}": f"fixture query {i}" for i in range(30)}
    qrels = {qid: {f"d{i:03}"} for i, qid in enumerate(sorted(queries))}
    ids = select_queries(queries, qrels, corpus)
    assert ids == sorted(queries)[:QUERY_COUNT]
    docs = select_documents(corpus, qrels, ids, 500)
    assert len(docs) == 500
    assert all(qrels[q].issubset(docs) for q in ids)
    assert docs == select_documents(corpus, qrels, ids, 500)


def test_incomplete_test_judgments_raise_instead_of_creating_answers():
    with pytest.raises(RuntimeError, match="enough judged"):
        select_queries({"q": "fixture"}, {"q": {"absent"}}, {"d": "fixture"})


def test_archive_parser_is_test_only_and_never_extracts_files(tmp_path, monkeypatch):
    files = {
        "scifact/corpus.jsonl": "\n".join(
            json.dumps({"_id": f"d{i}", "title": "synthetic", "text": str(i)})
            for i in range(5001)
        ),
        "scifact/queries.jsonl": "\n".join(
            json.dumps({"_id": f"q{i}", "text": "synthetic"})
            for i in range(25)
        ),
        "scifact/qrels/test.tsv": "query-id\tcorpus-id\tscore\nq0\td0\t1\nq1\td1\t0\n",
    }
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    monkeypatch.chdir(tmp_path)
    corpus, queries, qrels = load_scifact_zip(blob.getvalue())
    assert corpus["d0"] == "synthetic 0"
    assert len(queries) == 25
    assert qrels == {"q0": {"d0"}}
    assert list(tmp_path.iterdir()) == []
