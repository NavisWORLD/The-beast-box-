"""Tests for scripts/parse_12d_evidence_report.py (PR 2).

Covers: MEASURED vs NULL routing (above/below threshold, missing),
structured JSON winning over regex scans, and the stub-receipt rule
(a "ready" stub routes everything to NULL, never MEASURED).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.parse_12d_evidence_report import parse_logs, render_markdown


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_above_threshold_is_measured_and_below_is_null(tmp_path):
    log = _write(tmp_path, "train.log",
                 "nll_true=2.10 nll_zero=2.20 nll_shuf=2.19\n"
                 "delta_nll_12d=0.10 jsd_12d=0.005 cfjs_loss=0.31\n")
    report = parse_logs([log])
    assert report["measured"]["delta_nll_12d"]["value"] == 0.10
    assert report["null"]["jsd_12d"]["reason"] == "below_threshold"
    assert report["null"]["jsd_12d"]["value"] == 0.005


def test_missing_metrics_are_null_with_reason(tmp_path):
    log = _write(tmp_path, "empty.log", "epoch 1 done, no gate lines\n")
    report = parse_logs([log])
    assert report["measured"] == {}
    assert report["null"]["delta_nll_12d"]["reason"] == "missing_or_unmeasured_in_logs"
    assert report["null"]["jsd_12d"]["reason"] == "missing_or_unmeasured_in_logs"


def test_embedded_json_wins_over_regex(tmp_path):
    # Regex says delta 0.01 (below threshold); embedded JSON says 0.12.
    # Structured JSON must win -> MEASURED.
    log = _write(tmp_path, "gate.log",
                 "delta_nll_12d=0.01 jsd_12d=0.001\n"
                 '{"delta_nll_12d": 0.12, "jsd_12d": 0.03, "nll_true": 2.0}\n')
    report = parse_logs([log])
    assert report["measured"]["delta_nll_12d"]["value"] == 0.12
    assert report["measured"]["jsd_12d"]["value"] == 0.03


def test_receipt_json_wins_over_log_scan(tmp_path):
    log = _write(tmp_path, "train.log", "delta_nll_12d=0.01 jsd_12d=0.001\n")
    receipt = _write(tmp_path, "receipt.json", json.dumps({
        "status": "measured", "delta_nll": 0.09, "jsd": 0.025,
        "nll_true": 2.0, "nll_zero": 2.09, "nll_shuf": 2.08,
    }))
    report = parse_logs([log], receipt)
    assert report["measured"]["delta_nll_12d"]["value"] == 0.09
    assert report["measured"]["jsd_12d"]["value"] == 0.025


def test_stub_receipt_routes_everything_to_null(tmp_path):
    log = _write(tmp_path, "train.log", "delta_nll_12d=0.01 jsd_12d=0.001\n")
    stub = _write(tmp_path, "stub.json", json.dumps({
        "status": "ready", "note": "verifier not run yet",
    }))
    report = parse_logs([log], stub)
    assert report["measured"] == {}
    assert report["observed"]["receipt_is_stub"] is True
    assert report["null"]["delta_nll_12d"]["reason"] == "below_threshold"
    assert report["null"]["jsd_12d"]["reason"] == "below_threshold"
    # A stub alone (no log values at all) must still be all-NULL.
    empty = _write(tmp_path, "empty.log", "nothing here\n")
    report2 = parse_logs([empty], stub)
    assert report2["measured"] == {}
    assert report2["null"]["delta_nll_12d"]["reason"] == "missing_or_unmeasured_in_logs"


def test_report_sha_and_markdown_sections(tmp_path):
    log = _write(tmp_path, "train.log", "delta_nll_12d=0.10 jsd_12d=0.03\n")
    report = parse_logs([log], commit_sha="abc123", run_id="999", pr="1043")
    assert len(report["report_sha256"]) == 64
    assert report["observed"]["logs"][0]["sha256"]
    assert report["observed"]["pr"] == "1043"
    md = render_markdown(report)
    for section in ("IMPLEMENTED", "OBSERVED", "MEASURED", "NULL"):
        assert section in md
    assert "3,7,11,15,19,23,27,31,35,39,43" in md
    assert "4..44" not in md
