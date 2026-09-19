import pytest

from scripts.final_reality_bridge_model_swap import (
    EXPECTED_REFERENCE_SNAPSHOT_MANIFEST_SHA256,
    canonical_zeref_ledger_bytes,
    compare_zeref_ledgers,
    reference_bpc_reproduced,
)


def _row(record_id: str, nll: float):
    return {
        "record_id": record_id,
        "position": 0 if record_id == "a" else 1,
        "view_sha256": "0" * 64,
        "text_characters": 10,
        "supported_characters": 10,
        "dropped_characters": 0,
        "tokenizer_coverage": 1.0,
        "predicted_characters": 9,
        "nll_nats": nll,
        "nll_bits": nll / 0.6931471805599453,
        "bits_per_predicted_character": (nll / 0.6931471805599453) / 9,
    }


def test_zeref_round_trip_requires_byte_identical_canonical_ledgers():
    before = [_row("a", 1.25), _row("b", 2.5)]
    after = [_row("a", 1.25), _row("b", 2.5)]
    result = compare_zeref_ledgers(before, after)
    assert result["byte_identical"] is True
    assert result["before_sha256"] == result["after_sha256"]
    assert canonical_zeref_ledger_bytes(before) == canonical_zeref_ledger_bytes(after)


def test_zeref_round_trip_rejects_one_bit_of_score_drift():
    before = [_row("a", 1.25)]
    after = [_row("a", 1.2500000000001)]
    result = compare_zeref_ledgers(before, after)
    assert result["byte_identical"] is False
    assert result["before_sha256"] != result["after_sha256"]


def test_reference_reproduction_tolerance_is_frozen_at_one_e_minus_nine():
    assert reference_bpc_reproduced(1.2938617454825692, 1.2938617464825692) is True
    assert reference_bpc_reproduced(1.2938617454825692, 1.2938617474825692) is False


def test_reference_snapshot_manifest_identity_is_frozen():
    assert EXPECTED_REFERENCE_SNAPSHOT_MANIFEST_SHA256 == "f75e3350cdeda2c553f2cae22d493eb5f6fa303d84c28c7cf085ca25e4112bfc"
