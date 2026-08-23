from pathlib import Path

from scripts.build_zeref_r12_public_kit import build_source_kit, add_verified_checkpoint
from scripts.verify_zeref_r12_public_kit import verify_kit


ROOT = Path(__file__).resolve().parents[1]


def test_source_kit_builds_with_pinned_r12_and_memory(tmp_path):
    out = tmp_path / "kit"
    receipt = build_source_kit(ROOT, out)
    assert receipt["schema"] == "zeref-r12-source-kit-receipt-v1"
    assert receipt["active_lineage"] == "ZEREF-DAD-SON-TALK-004"
    assert receipt["durable_memory_record_count"] == 352
    assert receipt["r12_state_sha256"] == "48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20"
    assert receipt["reality_ledger_tip_sha256"] == "78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415"
    assert (out / "KIT_MANIFEST.json").is_file()
    assert (out / "SHA256SUMS").is_file()
    assert (out / "runtime" / "beastbox" / "reality_memory.py").is_file()
    assert (out / "memory" / "ledger-manifest.json").is_file()
    assert (out / "reality-memory" / "ledger" / "reality-events.jsonl").is_file()


def test_source_kit_verifies_without_checkpoint(tmp_path):
    out = tmp_path / "kit"
    build_source_kit(ROOT, out)
    report = verify_kit(out, require_checkpoint=False)
    assert report["ok"] is True
    assert report["checkpoint_present"] is False
    assert report["r12_chain_valid"] is True
    assert report["r12_rebuild_verified"] is True


def test_checkpoint_addition_rejects_wrong_hash(tmp_path):
    out = tmp_path / "kit"
    build_source_kit(ROOT, out)
    fake = tmp_path / "checkpoint.pt"
    fake.write_bytes(b"not-talk4")
    try:
        add_verified_checkpoint(out, fake)
    except ValueError as exc:
        assert "checkpoint sha256" in str(exc).lower()
    else:
        raise AssertionError("wrong checkpoint hash was accepted")


def test_root_readme_and_manual_document_r12_boundary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    manual = (ROOT / "docs" / "ZEREF_R12_REALITY_MEMORY_MANUAL.md").read_text(encoding="utf-8")
    assert "R12 Reality Memory Expansion" in readme
    assert "forever memory" in readme.lower()
    assert "measured" in manual and "derived" in manual and "synthetic" in manual
    boundary = "does not establish biological life, consciousness"
    assert boundary in manual
