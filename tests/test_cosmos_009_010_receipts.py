"""Negative scientific outcomes cannot be converted to victories via archive edits."""
from __future__ import annotations
import json
import pytest
from scripts import verify_cosmos_009_010_receipts as a

def test_entire_original_both_pilot_archive():
    x=a.verify()
    assert x["original_native_seeds"]==[19,43,71]
    assert not x["real_retrieval_generation_advantage_established"]
    assert not x["longer_context_12d_advantage_established"]

def test_original_retriever_vs_generator_confounds_remain_visible():
    g=json.loads((a.ROOT/"cosmos-end-to-end-009-summary.json").read_text())
    for r in g["results"]:
        assert r["scores"]["oracle"]["correct"]==0
        assert r["scores"]["lexical"]["retrieval_correct"]==r["scores"]["lexical"]["count"]
    n=json.loads((a.ROOT/"cosmos-native-length-010-summary.json").read_text())
    assert n["summary"]["dyn12"]["shift_four"]["mean_accuracy"]>n["summary"]["standard"]["shift_four"]["mean_accuracy"]
    assert n["summary"]["dyn12"]["shift_five"]["mean_accuracy"]<n["summary"]["standard"]["shift_five"]["mean_accuracy"]

def test_mutating_original_010_null_is_detected(tmp_path,monkeypatch):
    for f in ("cosmos-end-to-end-009-summary.json","cosmos-native-length-010-summary.json"):
        (tmp_path/f).write_bytes((a.ROOT/f).read_bytes())
    path=tmp_path/"cosmos-native-length-010-summary.json"
    raw=path.read_bytes()
    assert b'"novel_native_12d_long_sequence_advantage_proven":false' in raw
    path.write_bytes(raw.replace(b'"novel_native_12d_long_sequence_advantage_proven":false',
                                b'"novel_native_12d_long_sequence_advantage_proven":true',1))
    monkeypatch.setattr(a,"ROOT",tmp_path)
    with pytest.raises(ValueError,match="original full source"):
        a.verify()
