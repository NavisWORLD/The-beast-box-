"""Package-wheel smoke stays on package releases and skips evidence pins."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.public_release_wheel_scope import scope_decision


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "public_release_wheel_scope.py"

# Asset names read from the live releases on 2026-11-09.
EVIDENCE_V15_ASSETS = [
    "heart-seed-v15.json",
    "ibm-chsh-result-public.json",
    "pair-choice.json",
    "public-evidence-sha256.txt",
    "quota-after.json",
    "quota-before.json",
    "raw-artifact-sha256.txt",
    "README.md",
    "submission.json",
]
PACKAGE_V071_WHEEL = "cosmos_beast_box-0.7.1-py3-none-any.whl"


def test_evidence_heart_seed_v15_is_skipped() -> None:
    decision, reason = scope_decision("evidence-zeref-heart-seed-v15", EVIDENCE_V15_ASSETS)
    assert decision == "skip"
    assert "evidence-" in reason
    assert "evidence-zeref-heart-seed-v15" in reason


def test_evidence_tag_with_a_wheel_attached_is_still_skipped() -> None:
    decision, reason = scope_decision(
        "evidence-zeref-heart-seed-v15",
        [*EVIDENCE_V15_ASSETS, PACKAGE_V071_WHEEL],
    )
    assert decision == "skip"
    assert reason.startswith("tag evidence-zeref-heart-seed-v15 starts with evidence-")


def test_v_star_package_tag_with_a_wheel_runs() -> None:
    decision, reason = scope_decision(
        "v0.7.1",
        [PACKAGE_V071_WHEEL, "SHA256SUMS.txt", "beast-box-combined-0.7.1.zip"],
    )
    assert decision == "run"
    assert "v0.7.1" in reason


def test_v_star_tag_without_a_wheel_still_runs() -> None:
    decision, reason = scope_decision("v0.7.1", ["SHA256SUMS.txt", "RELEASE_PROVENANCE.json"])
    assert decision == "run"
    assert "v0.7.1" in reason
    assert "missing wheel fails there" in reason


def test_cli_prints_the_same_two_outcomes() -> None:
    evidence = subprocess.run(
        [sys.executable, str(SCRIPT), "--tag", "evidence-zeref-heart-seed-v15", *[
            arg for name in EVIDENCE_V15_ASSETS for arg in ("--asset", name)
        ]],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "decision=skip\n" in evidence.stdout
    package = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--tag",
            "v0.7.1",
            "--asset",
            PACKAGE_V071_WHEEL,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "decision=run\n" in package.stdout
    missing = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--tag",
            "v0.7.1",
            "--asset",
            "SHA256SUMS.txt",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "decision=run\n" in missing.stdout
    assert "decision=skip" not in missing.stdout
