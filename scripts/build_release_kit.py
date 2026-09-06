#!/usr/bin/env python3
"""Bundle verified Python artifacts with EnD and exact source provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def build_kit(dist: Path) -> Path:
    if git("status", "--porcelain"):
        raise RuntimeError("release kit requires a clean committed source tree")
    from beastbox import __version__
    version = __version__
    if os.environ.get("GITHUB_REF", "").startswith("refs/tags/"):
        if os.environ["GITHUB_REF"] != f"refs/tags/v{version}":
            raise RuntimeError("release tag does not match package version")
    if dist.exists() and any(dist.iterdir()):
        raise RuntimeError("release requires an empty artifact directory; stale packages cannot be source-bound")
    dist.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "build", "--outdir", str(dist.resolve()), str(ROOT)], check=True)
    files = {
        "EnD": ROOT / "kits/BEAST_BOX_COMBINED/EnD",
        "README.md": ROOT / "kits/BEAST_BOX_COMBINED/README.md",
        "LICENSE": ROOT / "LICENSE",
        "ECOSYSTEM_MANIFEST.json": ROOT / "docs/ECOSYSTEM_MANIFEST.json",
        "TRUST_BOUNDARIES.md": ROOT / "docs/TRUST_BOUNDARIES.md",
        "READINESS.json": ROOT / "docs/closure/READINESS.json",
        "PERSISTENT_SUBSTRATE_MODEL_SWAP_002_FINAL_REPORT.md": ROOT / "docs/PERSISTENT_SUBSTRATE_MODEL_SWAP_002_FINAL_REPORT.md",
        "historical-swap-002.zip": ROOT / "evidence/system-closure-001/historical-swap-002.zip",
    }
    for path in (ROOT / "kits/BEAST_BOX_COMBINED").iterdir():
        if path.is_file():
            files[path.name] = path
    files["OPTIONAL_INPUTS.md"] = ROOT / "docs/OPTIONAL_INPUTS.md"
    for name in (f"cosmos_beast_box-{version}-py3-none-any.whl", f"cosmos_beast_box-{version}.tar.gz"):
        files[name] = dist / name
    payloads = {name: path.read_bytes() for name, path in files.items()}
    provenance = {
        "schema": "beastbox-release-provenance-v1", "version": version,
        "source_commit": git("rev-parse", "HEAD"), "source_tree": git("rev-parse", "HEAD^{tree}"),
        "source_dirty": False, "files_sha256": {name: sha(data) for name, data in payloads.items()},
        "historical_evidence_changed": False,
        "verification_policy": "release.yml requires full Product CI and native tests on this exact source",
    }
    payloads["RELEASE_PROVENANCE.json"] = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode()
    payloads["SHA256SUMS"] = "".join(f"{sha(data)}  {name}\n" for name, data in sorted(payloads.items())).encode()
    archive = dist / f"beast-box-combined-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            target.writestr(info, data)
    with zipfile.ZipFile(archive) as verified:
        for line in verified.read("SHA256SUMS").decode().splitlines():
            digest, name = line.split("  ", 1)
            if sha(verified.read(name)) != digest:
                raise RuntimeError(f"release kit checksum mismatch: {name}")
    (dist / "RELEASE_PROVENANCE.json").write_bytes(payloads["RELEASE_PROVENANCE.json"])
    artifacts = sorted(p for p in dist.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    (dist / "SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in artifacts))
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    print(build_kit(args.dist))
