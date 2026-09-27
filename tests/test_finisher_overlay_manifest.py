"""Security-overlay manifest receipts; these tests are safe on both pristine and derived trees."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "apply-security-patches.py"


def test_security_patch_manifest_verification_succeeds_with_original_patch_bytes() -> None:
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--verify-only"], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["verified"] is True
    assert receipt["patch_count"] == 7
    assert len(receipt["manifest_sha256"]) == 64


def test_security_patch_manifest_refuses_mutated_patch_bytes(tmp_path: Path) -> None:
    # The same pinned builder must reject a compromised patch without
    # modifying original frozen sources or producing a derived tree.
    fixture = tmp_path / "tampered"
    shutil.copytree(ROOT / "patches", fixture / "patches")
    patch = sorted((fixture / "patches").glob("*.patch"))[0]
    patch.write_bytes(patch.read_bytes() + b"\n# altered after review\n")
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--source", str(fixture), "--verify-only"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert "patch bytes mismatch" in result.stderr.lower()
