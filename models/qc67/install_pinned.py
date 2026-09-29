"""Build-time installer only: immutable original public QC67 weights and source.

No runtime downloading, secret handling, model substitution, or training.
All six content hashes were independently confirmed by a real GitHub Actions
strict-load/forward test. Upstream HF model-card license is 'other'; distributing
its published weights separately requires review of that upstream license.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request

PINS = json.loads((Path(__file__).parent / "pins.json").read_text())


def sha256(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def verify(root: Path) -> dict:
    """Verify every pinned file without network or mutating installed weights."""
    files = PINS["files"]
    for name, expected in files.items():
        target = root / name
        if target.is_symlink() or not target.is_file() or sha256(target) != expected:
            raise RuntimeError("Original QC67 artifact not installed or digest mismatch: " + name)
    manifest = root / "pins.json"
    if manifest.is_symlink() or not manifest.is_file() or json.loads(manifest.read_text()) != PINS:
        raise RuntimeError("Original QC67 manifest mismatch")
    return {"phos": files["weights/phos.pt"],
            "samgo": files["weights/samgo_weights.pt"],
            "revision": PINS["hf_revision"]}


def install(destination: Path) -> dict:
    from huggingface_hub import hf_hub_download
    destination = destination.resolve()
    if destination.exists():
        return verify(destination)  # Preserve an existing installation verbatim.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".qc67-stage-", dir=destination.parent) as td:
        stage = Path(td)
        for name in ("weights/phos.pt", "weights/samgo_weights.pt",
                     "architecture/cosmos_state_ladder.py",
                     "architecture/cosmos_spark_cst.py"):
            upstream = Path(hf_hub_download(repo_id=PINS["hf_repository"],
                                            filename=name, revision=PINS["hf_revision"],
                                            token=False))
            dest = stage / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(upstream, dest)
            if sha256(dest) != PINS["files"][name]:
                raise RuntimeError("QC67 upstream hash mismatch: " + name)
        for name in ("cosmos_config.py", "cosmos_model.py"):
            rel = "cosmos/web/cosmosynapse/model/" + name
            local = "original_54d/" + rel
            url = ("https://raw.githubusercontent.com/" + PINS["original_54d_repo"] +
                   "/" + PINS["original_54d_revision"] + "/" + rel)
            req = urllib.request.Request(url, headers={"User-Agent": "BeastBox-QC67-pinned-build"})
            with urllib.request.urlopen(req, timeout=40) as response:
                if response.status != 200 or response.geturl() != url:
                    raise RuntimeError("Unexpected original 54D download response")
                body = response.read(110_001)
            if len(body) > 110_000:
                raise RuntimeError("Original 54D source too large")
            dest = stage / local
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            if sha256(dest) != PINS["files"][local]:
                raise RuntimeError("Original 54D source hash mismatch: " + local)
        (stage / "pins.json").write_text(json.dumps(PINS, indent=2, sort_keys=True) + "\n")
        verify(stage)
        stage.rename(destination)
    return verify(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.destination), sort_keys=True))
