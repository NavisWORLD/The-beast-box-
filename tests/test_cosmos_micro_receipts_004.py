"""Immutable actual PHOS/Spark public artifact audit with privacy regression."""
from __future__ import annotations
from pathlib import Path
import pytest
from scripts.verify_cosmos_micro_receipts_004 import RECEIPTS, ROOT, verify
@pytest.mark.parametrize("name",("phos","cosmos_born"))
def test_original_full_real_checkpoint_evidence_is_pinned(name):
    r=verify(name)
    assert r["original_ci_receipt_sha256"]==RECEIPTS[name]
    assert r["observations"]==40
    assert r["strict_compact_baseline"]==0 and r["strict_compact_feedback"]==0
def test_spark_has_explicit_unrepresentable_original_character_target():
    assert verify("cosmos_born")["target_encodable_compact"]==3
    assert verify("phos")["target_encodable_compact"]==4
def test_tampered_public_evidence_fails_before_interpretation(tmp_path:Path):
    src=ROOT/"cosmos-micro-originals-004-phos-measurements.json"
    dest=tmp_path/src.name
    dest.write_bytes(src.read_bytes().replace(b'"model":"phos"',b'"model":"fabricated"',1))
    with pytest.raises(ValueError,match="receipt bytes changed"):
        verify("phos",tmp_path)
