"""Original measured 12D negative result is versioned, reproducible and not cherry-picked."""
import json
from pathlib import Path
import pytest
from scripts.verify_dyn12_summary_006 import P, verify
def test_original_three_seed_full_result_can_be_rederived():
    v=verify()
    assert v["registered_seeds"]==[11,29,47]
    assert v["candidate_pattern"] is False
def test_archived_negative_results_and_ood_signal_are_both_preserved():
    r=json.loads(P.read_text())
    a=r["summary"]["dyn12"];b=r["summary"]["standard"]
    assert a["test"]["mean_accuracy"] < b["test"]["mean_accuracy"]
    assert a["ood_four_bindings"]["mean_accuracy"] > b["ood_four_bindings"]["mean_accuracy"]
def test_tampered_original_numeric_summary_never_passes(monkeypatch,tmp_path):
    from scripts import verify_dyn12_summary_006 as audit
    altered=tmp_path/"wrong.json"
    altered.write_bytes(P.read_bytes().replace(b'"novel_intelligence_advantage_proven":false',
                                               b'"novel_intelligence_advantage_proven":true',1))
    monkeypatch.setattr(audit,"P",altered)
    with pytest.raises(ValueError,match="modified"):
        audit.verify()
