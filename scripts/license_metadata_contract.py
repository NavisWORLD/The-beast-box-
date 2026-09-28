"""Current Beast Box licensing contract and comprehensive tracked-text keyword audit.

Historical snapshots and independent third-party notices are reported, never
retroactively relicensed or silently rewritten.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {".git", "node_modules", "vendor", "vendored", ".venv", "venv", "__pycache__"}
PRESERVED_PREFIXES = (
    "Endsupdate/", "experimental/", "evidence/", "apps/licenses/",
    "docs/performance/", "docs/closure/PREVIOUS_PRODUCT_STATUS.json",
    "docs/closure/RELEASE_NOTES_", "docs/superpowers/", "docs/evidence/",
)
AUDIT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".jsonl", ".toml", ".yml", ".yaml",
    ".js", ".mjs", ".ts", ".tsx", ".jsx", ".rs", ".html", ".xml", ".sh",
    ".css", ".c", ".cpp", ".h", ".hpp", ".ini", ".cfg", ".lock",
}
AUDIT_TERMS = re.compile(
    r"\b(?:proprietary|source[\s-]*available|permission[\s-]*required|open_source|licen[cs]e|MIT|Apache)\b",
    re.IGNORECASE,
)
STALE_TERMS = re.compile(
    r"\b(?:proprietary|source[\s-]*available|permission[\s-]*required)\b",
    re.IGNORECASE,
)

def status_errors(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["PROJECT_STATUS.json must contain a JSON object"]
    errors: list[str] = []
    if data.get("license") != "Apache-2.0":
        errors.append("PROJECT_STATUS.json license must be Apache-2.0")
    if data.get("open_source") is not True:
        errors.append("PROJECT_STATUS.json open_source must be boolean true")
    return errors

def tracked_text_paths(root: Path):
    try:
        found = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
        )
        paths = [Path(p.decode("utf-8", errors="replace"))
                 for p in found.stdout.split(b"\x00") if p]
    except (OSError, subprocess.SubprocessError):
        paths = [p.relative_to(root) for p in root.rglob("*") if p.is_file()]
    for rel in sorted(paths):
        if any(part in IGNORED_PARTS for part in rel.parts):
            continue
        absolute = root / rel
        if not absolute.is_file():
            continue
        if absolute.suffix.lower() not in AUDIT_SUFFIXES and absolute.name not in ("LICENSE", "NOTICE"):
            continue
        try:
            if absolute.stat().st_size > 2_000_000:
                continue
        except OSError:
            continue
        yield rel, absolute

def category(path: str) -> str:
    if path == "LICENSE_HISTORY.md" or path.startswith(PRESERVED_PREFIXES):
        return "PRESERVED_HISTORY_OR_THIRD_PARTY"
    if path in ("scripts/license_metadata_contract.py", "tests/test_license_metadata_contract.py"):
        return "AUDIT_IMPLEMENTATION"
    return "CURRENT_OR_UNCLASSIFIED"

def audit_lines(root: Path):
    for rel, absolute in tracked_text_paths(root):
        path = rel.as_posix()
        try:
            content = absolute.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        classification = category(path)
        for number, line in enumerate(content.splitlines(), 1):
            if AUDIT_TERMS.search(line):
                yield path, number, classification, line

def verify(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    def read(path: str) -> str:
        try:
            return (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            errors.append("Required file missing or unreadable: " + path)
            return ""
    license_text = read("LICENSE")
    if not (
        re.search(r"(?m)^\s*Apache License\s*$", license_text)
        and re.search(r"(?m)^\s*Version 2\.0, January 2004\s*$", license_text)
    ):
        errors.append("Root LICENSE must contain Apache License 2.0")
    try:
        errors.extend(status_errors(json.loads(read("PROJECT_STATUS.json"))))
    except ValueError:
        errors.append("PROJECT_STATUS.json is invalid JSON")
    pyproject = read("pyproject.toml")
    if 'license = {file = "LICENSE"}' not in pyproject:
        errors.append("pyproject.toml must refer to root LICENSE")
    if '"License :: OSI Approved :: Apache Software License"' not in pyproject:
        errors.append("pyproject.toml is missing the Apache Software License classifier")
    if 'License :: Other/' in pyproject:
        errors.append("pyproject.toml contains an incompatible additional classifier")
    for must_exist in ("apps/beastbox-cloud/package.json", "html/package.json"):
        if not (root / must_exist).is_file():
            errors.append("Required package manifest missing: " + must_exist)
    for group in ("apps", "html", "models"):
        directory = root / group
        if not directory.is_dir():
            continue
        for manifest in sorted(directory.rglob("package.json")):
            rel = manifest.relative_to(root)
            if any(part in IGNORED_PARTS for part in rel.parts):
                continue
            try:
                metadata = json.loads(manifest.read_text(encoding="utf-8"))
                if metadata.get("license") != "Apache-2.0":
                    errors.append(f"{rel}: package license metadata must be Apache-2.0")
            except (OSError, UnicodeError, ValueError):
                errors.append(f"{rel}: package manifest cannot be decoded")
    history = read("LICENSE_HISTORY.md")
    if "4c4e4d38e645ee521534643d42843e181be4900a" not in history or "Apache-2.0 open-source revision" not in history:
        errors.append("LICENSE_HISTORY.md must retain the existing adoption record")
    if "Apache-2.0" not in read("NOTICE"):
        errors.append("NOTICE must retain Apache-2.0 scope")
    for path in (
        "README.md", "IP_NOTICE.md", "IP_PROVENANCE.md",
        "COMMERCIAL_RIGHTS.md", "CONTRIBUTING.md",
        "CORY_DAVIS_IP_AND_ACCESS_NOTICE.md", "docs/LICENSE_CLARIFICATION.md",
    ):
        if "Apache-2.0" not in read(path):
            errors.append(f"{path}: current covered-source license is not stated")
    for path, line, classification, content in audit_lines(root):
        if classification == "CURRENT_OR_UNCLASSIFIED" and STALE_TERMS.search(content):
            errors.append(f"{path}:{line}: stale restrictive-language term outside preserved history")
    return errors

def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--audit", action="store_true",
                     help="print every tracked-text keyword hit with file, 1-based line, classification, full line")
    args = cli.parse_args()
    if args.audit:
        print("file\tline\tclassification\tcontent")
        for path, line, classification, content in audit_lines(ROOT):
            print(f"{path}\t{line}\t{classification}\t{content.replace(chr(9), ' ')}")
        return 0
    errors = verify(ROOT)
    for message in errors:
        print("LICENSE_METADATA_CONTRACT_ERROR: " + message)
    if errors:
        print(f"license metadata contract FAIL: {len(errors)} issue(s)")
        return 1
    print("license metadata contract PASS; preserved history and third-party texts separately audited")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
