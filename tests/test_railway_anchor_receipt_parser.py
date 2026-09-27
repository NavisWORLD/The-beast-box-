"""Test the Railway receipt parser without a Railway connection."""
from __future__ import annotations

import pytest

from scripts.railway_anchor_one_shot import verified_junit_counts


def test_receipt_accepts_pytest_generated_testsuites_format(tmp_path):
    receipt = tmp_path / "junit.xml"
    receipt.write_text(
        '<testsuites><testsuite name="railway" tests="41" errors="0" '
        'failures="0" skipped="0"></testsuite></testsuites>', encoding="utf-8"
    )
    assert verified_junit_counts(receipt) == {
        "tests": 41, "errors": 0, "failures": 0, "skipped": 0, "passed": 41
    }


def test_receipt_accurately_counts_failures_and_skips(tmp_path):
    receipt = tmp_path / "junit.xml"
    receipt.write_text(
        '<testsuite name="railway" tests="4" errors="1" failures="1" '
        'skipped="1"></testsuite>', encoding="utf-8"
    )
    assert verified_junit_counts(receipt)["passed"] == 1


def test_receipt_rejects_empty_suites(tmp_path):
    receipt = tmp_path / "junit.xml"
    receipt.write_text("<testsuites/>", encoding="utf-8")
    with pytest.raises(ValueError, match="no test suites"):
        verified_junit_counts(receipt)
