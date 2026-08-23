from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "kits" / "ZEREF_R12_REALITY_MEMORY_KIT"

EXPECTED = {
    "active_lineage": "ZEREF-DAD-SON-TALK-004",
    "active_checkpoint_sha256": "9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f",
    "durable_memory_record_count": 352,
    "durable_memory_sha256": "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef",
    "durable_memory_tip_sha256": "b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26",
    "r12_state_sha256": "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20",
    "reality_ledger_tip_sha256": "78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415",
}


def test_public_kit_contains_launchers_and_manifest():
    required = ["README.md", "kit-manifest.json", "verify_kit.py", "INSTALL.bat", "RUN_ZEREF.bat", "install.sh", "run_zeref.sh"]
    for name in required:
        assert (KIT / name).is_file(), name
    data = json.loads((KIT / "kit-manifest.json").read_text())
    for key, value in EXPECTED.items():
        assert data[key] == value
    assert data["claim_boundary"].startswith("Persistent computational memory")


def test_kit_verifier_accepts_repo_state_and_rejects_tamper(tmp_path):
    spec = importlib.util.spec_from_file_location("zeref_r12_kit_verify", KIT / "verify_kit.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    ok = module.verify(repo_root=ROOT, manifest_path=KIT / "kit-manifest.json")
    assert ok["ok"] is True
    tampered = json.loads((KIT / "kit-manifest.json").read_text())
    tampered["active_checkpoint_sha256"] = "0" * 64
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(tampered))
    bad = module.verify(repo_root=ROOT, manifest_path=p)
    assert bad["ok"] is False
    assert "active_checkpoint_sha256" in bad["errors"]
