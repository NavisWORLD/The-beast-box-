"""Do not upgrade source-bound negative evidence into unearned correction claims."""
import pytest
from scripts.verify_self_critique_receipts_005 import ROOT,EXPECTED,verify

@pytest.mark.parametrize("label",("native18k","qwen0.5b"))
def test_archived_original_full_sanitized_result(label):
    v=verify(label)
    assert v["original_ci_receipt_sha256"]==EXPECTED[label]
    assert v["intrinsic_corrected_wrong_cases"]==0
    assert v["quality_claim_proven"] is False

def test_gold_answer_copy_control_is_separate_from_self_correction():
    native=verify("native18k")
    qwen=verify("qwen0.5b")
    assert native["baseline_semantic"]==0
    assert native["gold_disclosure_semantic"]==0
    assert qwen["baseline_semantic"]==3
    assert qwen["gold_disclosure_semantic"]==5
    assert qwen["intrinsic_corrected_wrong_cases"]==0

def test_tampering_with_original_model_data_is_rejected(tmp_path):
    src=ROOT/"cosmos-self-correction-005-qwen0.5b-receipt.json"
    dst=tmp_path/src.name
    dst.write_bytes(src.read_bytes().replace(b'"model":"qwen0.5b"',b'"model":"fake_model"',1))
    with pytest.raises(ValueError,match="altered"):
        verify("qwen0.5b",tmp_path)
