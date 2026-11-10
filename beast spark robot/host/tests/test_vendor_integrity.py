"""Cory's vendored Beast Box files must stay byte-identical (and match the read-only clone when present)."""
import hashlib
from pathlib import Path

from conftest import HOST, PKG

VENDOR = HOST / "spark_brain" / "beastbox_vendor"


def test_hashes_match_sha256sums():
    for line in (VENDOR / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split()
        assert hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() == digest, name


def test_identical_to_read_only_clone_if_present():
    clone = PKG / "ref" / "repos" / "The-beast-box-" / "beastbox"
    if not clone.exists():
        return
    for line in (VENDOR / "SHA256SUMS").read_text().splitlines():
        _, name = line.split()
        assert (VENDOR / name).read_bytes() == (clone / name).read_bytes(), name
