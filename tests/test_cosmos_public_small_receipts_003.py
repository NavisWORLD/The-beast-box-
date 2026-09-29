"""Archived real-public-model receipts: hash integrity and all literal outputs."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.verify_public_small_receipts_003 import BASE, RECEIPT_HASHES, verify


@pytest.mark.parametrize("label", ["smollm2-135m", "qwen2.5-0.5b"])
def test_real_public_original_full_receipt_is_pinned_and_regraded(label):
    observed = verify(label)
    assert observed["model"] == label
    assert observed["source_receipt_sha256"] == RECEIPT_HASHES[label]
    assert observed["conditions"] == 40
    assert set(observed["aggregate"]) == {"raw_native_compatible", "official_chat_template"}
    assert all(len(armlist) == 5 for armlist in observed["aggregate"].values())


def test_tampered_archive_does_not_inherit_original_model_attestation(tmp_path: Path):
    label = "smollm2-135m"
    source = BASE / f"cosmos-small-model-controls-003-{label}-receipt.json"
    dest = tmp_path / source.name
    dest.write_bytes(source.read_bytes().replace(b'"model":"smollm2-135m"', b'"model":"other-model"', 1))
    with pytest.raises(ValueError, match="modified"):
        verify(label, base=tmp_path)


def test_record_original_nulls_and_nonnulls_without_favorable_success_gate():
    smol = verify("smollm2-135m")["aggregate"]
    qwen = verify("qwen2.5-0.5b")["aggregate"]
    # Frozen historical observation: no strictly formatted Smol output scored.
    assert all(arm["exact"] == 0.0 for arms in smol.values() for arm in arms.values())
    # Observed public original: the same Qwen source and raw correct example
    # produced four strictly formatted hits. Pin as evidence, not a future gate.
    assert qwen["raw_native_compatible"]["correct_example"]["exact"] == 1.0
    # No answer was shown to the model in the neutral-example condition,
    # which *itself* never yielded a strict success on these particular runs.
    assert all(qwen[fmt]["neutral_example"]["exact"] == 0.0 for fmt in qwen)
