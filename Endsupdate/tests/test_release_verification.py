"""Release publication must reject incomplete or mismatched CI evidence."""

import json

import pytest

from scripts.seal_release_verification import validate_quality


@pytest.fixture
def receipts(tmp_path):
    (tmp_path / "architecture-acceptance.json").write_text(json.dumps({
        "source_sha": "test-source", "source_dirty": False, "passed": True,
        "checks": {"restart": True, "corruption": True},
    }))
    (tmp_path / "junit.xml").write_text(
        '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0">'
        '<testcase name="test_fixture"/></testsuite></testsuites>'
    )
    return tmp_path


def test_release_accepts_matching_clean_receipts(receipts):
    assert validate_quality(receipts, "test-source") == {
        "tests": 1, "architecture_checks": 2, "passed": True,
    }


def test_release_rejects_different_source(receipts):
    with pytest.raises(ValueError, match="clean release source"):
        validate_quality(receipts, "wrong-source")


def test_release_rejects_failed_case_with_false_green_summary(receipts):
    p = receipts / "junit.xml"
    p.write_text(p.read_text().replace('<testcase name="test_fixture"/>',
                                     '<testcase name="test_fixture"><failure/></testcase>'))
    with pytest.raises(ValueError, match="contradict"):
        validate_quality(receipts, "test-source")


def test_release_rejects_failed_architecture_check(receipts):
    p = receipts / "architecture-acceptance.json"
    data = json.loads(p.read_text())
    data["checks"]["corruption"] = False
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="acceptance did not pass"):
        validate_quality(receipts, "test-source")
