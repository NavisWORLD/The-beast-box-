"""Parity tests for the two-tier runtime (Track 4).

The browser ONNX lane (scripts/zeref_onnx_export.py, schema
zeref-browser-brain-v1, opset 17) and the local high-capacity lane
(scripts/zeref_local_runtime.py + profiles/zeref-local-high-capacity.json)
must recompute the same SHA-256 chain identically. Pure Python, no torch,
no hardware needed: the chain math is stdlib only.
"""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import zeref_local_runtime as lr  # noqa: E402

PIN_STEP = 47664
PIN_SHA = "b2678b9a19eb982772b916bab0be3097a95c4a240dca59ac1060baa631abc34b"

PAYLOADS = [
    {"seq": 0, "kind": "genesis", "text": "Zeref begins: a heartbeat folded into a chain."},
    {"seq": 1, "kind": "taught", "text": "The fort is a military construction designed."},
    {"seq": 2, "kind": "lived", "text": "The river held all three hold turns."},
    {"seq": 3, "kind": "taught", "text": "A leaf falls; gravity pulls it down."},
    {"seq": 4, "kind": "lived", "text": "Mom and dad together in one hold turn."},
]

PIN = {"training_steps": PIN_STEP, "checkpoint_sha256": PIN_SHA}


def test_canonical_json_matches_repo_form():
    assert lr.canonical_json({"b": 1, "a": [2, 3]}) == '{"a":[2,3],"b":1}'
    assert lr.sha256_obj({"a": 1}) == hashlib.sha256(b'{"a":1}').hexdigest()


def test_parity_across_profiles():
    entries = lr.build_chain(PAYLOADS)
    browser = lr.verify_chain_for_profile(lr.BROWSER_PROFILE, entries)
    local_profile = lr.load_local_profile(REPO / "profiles/zeref-local-high-capacity.json")
    local = lr.verify_chain_for_profile(local_profile, entries)
    assert browser["verified"] is True
    assert local["verified"] is True
    assert browser["chain_head"] == local["chain_head"]
    assert browser["entry_count"] == local["entry_count"] == len(PAYLOADS)
    assert browser["chain_head"] == entries[-1]["hash"]
    per_entry = [e["hash"] for e in entries]
    assert per_entry == [e["hash"] for e in lr.build_chain(PAYLOADS)]


def test_tamper_detected_by_both_profiles():
    entries = lr.build_chain(PAYLOADS)
    tampered = copy.deepcopy(entries)
    tampered[2]["text"] = "The river never held anything."
    browser = lr.verify_chain_for_profile(lr.BROWSER_PROFILE, tampered)
    local_profile = lr.load_local_profile(REPO / "profiles/zeref-local-high-capacity.json")
    local = lr.verify_chain_for_profile(local_profile, tampered)
    assert browser["verified"] is False
    assert local["verified"] is False
    assert browser["entry_count"] == local["entry_count"] == 2


def test_prev_link_tamper_detected():
    entries = lr.build_chain(PAYLOADS)
    tampered = copy.deepcopy(entries)
    tampered[3]["prev"] = "0" * 64
    ok, count, _head = lr.verify_chain(tampered)
    assert ok is False
    assert count == 3


def test_empty_chain_verifies_as_genesis():
    ok, count, head = lr.verify_chain([])
    assert (ok, count, head) == (True, 0, "genesis")


def test_local_profile_loads_and_receipt_reports_pin(tmp_path):
    profile = lr.load_local_profile(REPO / "profiles/zeref-local-high-capacity.json")
    assert profile["name"] == "local-high-capacity"
    assert profile["tier"] == "local"
    assert profile["device_class"] == "jetson-or-local-gpu"
    assert profile["max_parameters"] == 120000000000
    assert profile["threads"] == 8
    assert profile["batch_size"] == 8
    assert profile["memory_budget_gb"] == 32
    entries = lr.build_chain(PAYLOADS)
    receipt = lr.build_receipt(profile, PIN, entries)
    assert receipt["schema"] == "zeref-runtime-receipt-v1"
    assert receipt["pin_step"] == PIN_STEP
    assert receipt["checkpoint_sha256"] == PIN_SHA
    assert receipt["profile_name"] == "local-high-capacity"
    assert receipt["chain_head"] == entries[-1]["hash"]
    assert receipt["entry_count"] == len(PAYLOADS)
    assert receipt["verified"] is True
    out = tmp_path / "receipt.json"
    rc = lr.main(["--profile", str(REPO / "profiles/zeref-local-high-capacity.json"),
                  "--pin-file", str(_write_pin(tmp_path)), "--out", str(out)])
    assert rc == 0
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["pin_step"] == PIN_STEP
    assert saved["verified"] is True
    assert saved["entry_count"] == 0
    assert saved["chain_head"] == "genesis"


def _write_pin(tmp_path):
    pin_path = tmp_path / "pin.json"
    pin_path.write_text(json.dumps(PIN), encoding="utf-8")
    return pin_path


def test_local_profile_declares_more_capacity_than_browser():
    profile = lr.load_local_profile(REPO / "profiles/zeref-local-high-capacity.json")
    assert profile["max_parameters"] is not None
    assert profile["max_parameters"] > 0
    assert profile["threads"] > lr.BROWSER_PROFILE["threads"]
    assert profile["device_class"] != lr.BROWSER_PROFILE["device_class"]


def test_browser_lane_untouched():
    src = (REPO / "scripts/zeref_onnx_export.py").read_text(encoding="utf-8")
    assert "zeref-browser-brain-v1" in src
    assert "opset_version=17" in src
    assert "class Step" in src
    assert "def forward(self, ids, pk, pv, ps, fast)" in src
    local_src = (REPO / "scripts/zeref_local_runtime.py").read_text(encoding="utf-8")
    assert "import zeref_onnx_export" not in local_src
    assert "from zeref_onnx_export" not in local_src
    assert "import torch" not in local_src
    assert "zeref_onnx_export" not in sys.modules


def test_no_em_dash_in_new_files():
    for path in (
        REPO / "scripts/zeref_local_runtime.py",
        REPO / "profiles/zeref-local-high-capacity.json",
        REPO / "tests/test_zeref_runtime_parity.py",
    ):
        assert "\u2014" not in path.read_text(encoding="utf-8"), path
