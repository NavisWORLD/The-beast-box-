"""Attest original-vs-Endsupdate Git blob integrity without reading private assets.

Run from the repository checkout; does not modify history or protected files.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

BASELINE = "8f90e440f0f4ceba502b1a3f8637507491fb23b0"
BASELINE_BLOBS = 1325
# Immutable main commit at which the licensing-only PR forked. The research
# snapshot remains frozen at BASELINE; root checks compare with this newer
# approved main tree so unrelated preexisting evolution is not misclassified.
ROOT_APPROVED_PRELICENSE = "d2ae2c9f140a9ccdbf0eaa4268eeace67a50212a"
# Only reviewed open-source licensing files may differ from the frozen baseline.
# All other baseline blobs are still checked byte-for-byte and modes are checked.
APPROVED_OPEN_SOURCE_OVERLAYS = frozenset({
    "LICENSE", "LICENSE_HISTORY.md", "NOTICE", "README.md",
    "COMMERCIAL_RIGHTS.md", "IP_NOTICE.md", "pyproject.toml",
    "docs/LICENSE_CLARIFICATION.md", "docs/REPOSITORY_SECURITY.md",
    "scripts/security_audit.py",
})
EXPLICIT_CANDIDATE_OVERLAYS = frozenset({
    ".gitignore", "scripts/productization_receipt.py",
}) | APPROVED_OPEN_SOURCE_OVERLAYS
CANDIDATE_PREFIX = "Endsupdate/"
ROOT = Path(__file__).resolve().parent.parent


def parse_ls_tree(raw: bytes) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    for entry in raw.split(b"\x00"):
        if not entry:
            continue
        metadata, filename = entry.split(b"\t", 1)
        mode, kind, sha = metadata.decode("ascii").split()
        if kind != "blob":
            raise ValueError("unexpected non-blob tree entry")
        path = filename.decode("utf-8")
        if path in found:
            raise ValueError("duplicate path")
        found[path] = (mode, sha)
    return found


def tree_at(revision: str, *, root: Path = ROOT) -> dict[str, tuple[str, str]]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "-z", revision],
        cwd=root, check=True, capture_output=True,
    )
    return parse_ls_tree(result.stdout)


def verify(*, baseline: dict[str, tuple[str, str]], current: dict[str, tuple[str, str]], root_reference: dict[str, tuple[str, str]] | None = None) -> dict:
    """Attest frozen copy and root against prelicense main, allowing declared legal edits."""
    missing, modified_root, modified_copy, illegal_overlays = [], [], [], []
    root_ref = root_reference if root_reference is not None else baseline
    for path, original in root_ref.items():
        if path.startswith(CANDIDATE_PREFIX):
            continue
        if current.get(path) != original:
            if path not in APPROVED_OPEN_SOURCE_OVERLAYS or current.get(path, (None,))[0] != original[0]:
                modified_root.append(path)
    # New files outside Endsupdate/ also require explicit licensing approval.
    modified_root.extend(p for p in current if p not in root_ref and not p.startswith(CANDIDATE_PREFIX) and p not in APPROVED_OPEN_SOURCE_OVERLAYS)
    for path, original in baseline.items():
        copied = current.get(CANDIDATE_PREFIX + path)
        if copied is None:
            missing.append(path)
        elif copied != original and path not in EXPLICIT_CANDIDATE_OVERLAYS:
            modified_copy.append(path)
        elif copied != original and copied[0] != original[0]:
            illegal_overlays.append(path)
    candidate_paths = [p for p in current if p.startswith(CANDIDATE_PREFIX)]
    overlay_paths = sorted(p for p in EXPLICIT_CANDIDATE_OVERLAYS if current.get(CANDIDATE_PREFIX + p) != baseline.get(p))
    checks = {
        "expected_baseline_blob_count": len(baseline) == BASELINE_BLOBS,
        "baseline_paths_present": not missing,
        "root_baseline_unchanged": not modified_root,
        "copied_baseline_unchanged_outside_declared_overlays": not modified_copy,
        "overlay_modes_unchanged": not illegal_overlays,
        "candidate_contains_baseline_and_research": len(candidate_paths) > len(baseline),
    }
    return {
        "schema": "endsupdate-git-blob-attestation-001",
        "classification": "SOURCE_INTEGRITY_ONLY",
        "baseline_commit": BASELINE,
        "root_reference_commit": ROOT_APPROVED_PRELICENSE if root_reference is not None else BASELINE,
        "baseline_blob_count": len(baseline),
        "candidate_blob_count": len(candidate_paths),
        "explicit_modified_source_overlays": overlay_paths,
        "checks": checks,
        "unexpected_root_changes": modified_root,
        "missing_copied_paths": missing,
        "unapproved_copied_changes": modified_copy,
        "invalid_overlay_modes": illegal_overlays,
    }


def main() -> None:
    report = verify(baseline=tree_at(BASELINE), current=tree_at("HEAD"), root_reference=tree_at(ROOT_APPROVED_PRELICENSE))
    target = ROOT / "Endsupdate" / "evidence" / "endsupdate_blob_attestation_004.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "checks": report["checks"],
        "baseline_blob_count": report["baseline_blob_count"],
        "candidate_blob_count": report["candidate_blob_count"],
        "explicit_modified_source_overlays": report["explicit_modified_source_overlays"],
        "evidence": str(target),
    }, sort_keys=True))
    if not all(report["checks"].values()):
        raise SystemExit("FAIL: source integrity gate; see unexpected paths in JSON evidence")


if __name__ == "__main__":
    main()
