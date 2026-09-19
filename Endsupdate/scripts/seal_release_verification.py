#!/usr/bin/env python3
"""Validate and retain exact-source CI receipts before release publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def validate_quality(directory: Path, source_sha: str) -> dict:
    acceptance = json.loads((directory / "architecture-acceptance.json").read_text())
    if acceptance.get("source_sha") != source_sha or acceptance.get("source_dirty") is not False:
        raise ValueError("acceptance receipt does not bind clean release source")
    checks = acceptance.get("checks", {})
    if acceptance.get("passed") is not True or not checks or not all(v is True for v in checks.values()):
        raise ValueError("architecture acceptance did not pass")
    root = ET.parse(directory / "junit.xml").getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    total = sum(int(s.attrib["tests"]) for s in suites)
    if total <= 0 or total != len(list(root.iter("testcase"))):
        raise ValueError("missing or inconsistent test results")
    if any(int(s.attrib.get(k, 0)) for s in suites for k in ("errors", "failures", "skipped")):
        raise ValueError("test matrix contains failures, errors or skips")
    if any(list(root.iter(k)) for k in ("failure", "error", "skipped")):
        raise ValueError("test cases contradict passing summary")
    return {"tests": total, "architecture_checks": len(checks), "passed": True}


def seal(assets: Path, output: Path, source_sha: str, run_url: str) -> None:
    matrix = {version: validate_quality(assets / f"quality-{version}", source_sha)
              for version in ("3.10", "3.11", "3.12")}
    package = json.loads((assets / "package-smoke/package-smoke.json").read_text())
    if package.get("passed") is not True:
        raise ValueError("clean package installation did not pass")
    provenance = json.loads((output / "RELEASE_PROVENANCE.json").read_text())
    if provenance["source_commit"] != source_sha or provenance["source_dirty"] is not False:
        raise ValueError("package provenance does not bind clean release source")
    files = sorted(p for d in [*(assets / f"quality-{v}" for v in matrix), assets / "package-smoke"]
                   for p in d.rglob("*") if p.is_file())
    receipt = {
        "schema": "beastbox-release-verification-v1", "source_commit": source_sha,
        "source_tree": provenance["source_tree"], "workflow_run": run_url,
        "classification": "release-hardened experimental software", "production_ready": False,
        "python_matrix": matrix, "clean_wheel_and_sdist_install": "PASS",
        "native_tests_and_builds": "PASS: Linux, macOS, Windows; required predecessor jobs",
        "files_sha256": {p.relative_to(assets).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in files},
        "publication": "authorized only after required workflow jobs succeed; not a publication receipt",
    }
    (output / "RELEASE_VERIFICATION.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    with zipfile.ZipFile(output / "CI_EVIDENCE.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for p in files:
            archive.write(p, p.relative_to(assets).as_posix())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    seal(args.assets, args.output, args.source_sha, args.run_url)
