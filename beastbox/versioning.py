"""Fail-closed source-lineage verification for the separately versioned Finisher V2.

This commit-pinned metadata is *not* a signature or an independent trust root.
An attacker allowed to rewrite the verifier, manifest, and commit history is
outside this verifier's trust boundary.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

SCHEMA = "beastbox-source-versioning-v1"
HISTORICAL_ANCHOR = "b43f2883425e56446d3db8c009ea301b0adc21bc"
PINNED_MANIFEST_SHA256 = "1b46caafabfd7ce120281f4fbc0ffa77340f8c8f8d420479a7e27e77d7510026"
FROZEN_SHA256 = {
    "beastbox/persistent_substrate/ledger.py": "a32996e3e1093ee58222c50364d9c1800811419a37a55a524c945047fac899c5",
    "beastbox/dad_son.py": "0500094e0eabadc13bc4e1b819ae42f320b4af32e16ceb405a9e2cf2e8bcc6a5",
    "beastbox/persistent_substrate/substrate.py": "e579038e3c9cdf0e2f7a4a7a39e1b30d8b39b8ca854c7bc021a070a926a9260a",
}
V2_PATHS = {
    "beastbox/persistent_substrate/ledger.py": "beastbox/persistent_substrate/ledger_v2.py",
    "beastbox/dad_son.py": "beastbox/dad_son_v2.py",
    "beastbox/persistent_substrate/substrate.py": "beastbox/persistent_substrate/substrate_v2.py",
}


class VersionIntegrityError(RuntimeError):
    """A frozen or secure V2 source, manifest, or historical anchor changed."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def verify_versioned_sources(root: str | Path, *, verify_git_anchor: bool = False) -> dict[str, Any]:
    """Validate source bytes against reviewed SHA-256 pins, optionally Git's historical tree.

    The optional Git check requires the original historical commit to be present
    in this checkout. This is deliberately separate from external authenticity.
    """
    root = Path(root).resolve()
    manifest_file = root / "docs/VERSION_MANIFEST.json"
    raw = manifest_file.read_bytes()
    if _sha(raw) != PINNED_MANIFEST_SHA256:
        raise VersionIntegrityError("version manifest digest mismatch")
    try:
        manifest = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise VersionIntegrityError("invalid version manifest JSON") from exc
    if _canonical(manifest) != raw:
        raise VersionIntegrityError("version manifest is not canonical JSON")
    sidecar = (root / "docs/VERSION_MANIFEST.sha256").read_text(encoding="ascii")
    if sidecar != PINNED_MANIFEST_SHA256 + "  docs/VERSION_MANIFEST.json\n":
        raise VersionIntegrityError("version manifest digest sidecar mismatch")
    if manifest.get("schema") != SCHEMA or manifest.get("historical_anchor") != HISTORICAL_ANCHOR:
        raise VersionIntegrityError("incorrect version manifest schema or historical anchor")
    rows = manifest.get("mappings")
    if not isinstance(rows, list) or len(rows) != len(FROZEN_SHA256):
        raise VersionIntegrityError("missing or duplicate historical-to-V2 mapping")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise VersionIntegrityError("invalid version mapping")
        old = row.get("historical_path")
        if old not in FROZEN_SHA256 or old in seen:
            raise VersionIntegrityError("unrecognized or duplicate frozen source")
        seen.add(old)
        if row.get("historical_sha256") != FROZEN_SHA256[old]:
            raise VersionIntegrityError("historical SHA-256 pin disagrees with reviewed original")
        if row.get("v2_path") != V2_PATHS[old]:
            raise VersionIntegrityError("unapproved V2 destination")
        for path, expected in ((old, FROZEN_SHA256[old]), (V2_PATHS[old], row.get("v2_sha256"))):
            if not isinstance(expected, str) or len(expected) != 64:
                raise VersionIntegrityError("invalid source SHA-256")
            if _sha((root / path).read_bytes()) != expected:
                raise VersionIntegrityError("source SHA-256 mismatch: " + path)
        if verify_git_anchor:
            result = subprocess.run(
                ["git", "-C", str(root), "show", HISTORICAL_ANCHOR + ":" + old],
                check=False, capture_output=True,
            )
            if result.returncode or _sha(result.stdout) != FROZEN_SHA256[old]:
                raise VersionIntegrityError("Git historical anchor mismatch: " + old)
    return {
        "verified": True,
        "manifest_sha256": PINNED_MANIFEST_SHA256,
        "historical_anchor": HISTORICAL_ANCHOR,
        "mapping_count": len(seen),
        "verified_git_anchor": verify_git_anchor,
    }
