from __future__ import annotations

import json

import pytest

from beastbox.durable import DurableRuntime
from beastbox.product_services import (
    CAPABILITY_STATUSES,
    AuthoritySession,
    ProductService,
    WorkspaceGrant,
    capability_inventory,
)


def test_capability_inventory_uses_frozen_status_vocabulary():
    inventory = capability_inventory()
    assert set(CAPABILITY_STATUSES) == {
        "EXISTS_AND_WORKS",
        "EXISTS_BUT_NOT_EXPOSED",
        "HISTORICAL_REUSABLE",
        "PROTOTYPE_ONLY",
        "MISSING",
        "NOT_ESTABLISHED",
    }
    assert inventory["persistent_substrate"]["status"] == "EXISTS_AND_WORKS"
    assert inventory["camera_capture"]["status"] in CAPABILITY_STATUSES
    assert inventory["custom_voice"]["status"] in CAPABILITY_STATUSES
    assert all(entry["status"] in CAPABILITY_STATUSES for entry in inventory.values())


def test_authority_session_is_default_deny_and_master_stop_revokes_live_paths():
    authority = AuthoritySession()
    sensitive = {"camera", "microphone", "sensors", "cloud", "repo_write", "quantum_live"}
    assert not any(authority.allowed(name) for name in sensitive)
    for name in sensitive:
        authority.grant(name)
        assert authority.allowed(name)
    stopped = authority.master_privacy_stop()
    assert stopped == sorted(sensitive)
    assert not any(authority.allowed(name) for name in sensitive)


def test_authority_rejects_unknown_grants():
    authority = AuthoritySession()
    with pytest.raises(ValueError, match="unknown authority"):
        authority.grant("shell")


def test_file_inspection_is_bounded_hashed_and_does_not_persist_by_default(tmp_path):
    root = tmp_path / "state"
    service = ProductService(root)
    source = tmp_path / "notes.txt"
    source.write_text("sunflower continuity\n", encoding="utf-8")

    result = service.inspect_file(source)

    assert result.name == "notes.txt"
    assert result.byte_count == len(source.read_bytes())
    assert len(result.sha256) == 64
    assert result.persistent is False
    assert result.preview == "sunflower continuity\n"
    assert not root.exists() or not (root / "files").exists()


def test_file_inspection_rejects_executable_and_oversize_inputs(tmp_path):
    service = ProductService(tmp_path / "state", max_file_bytes=64)
    binary = tmp_path / "run.exe"
    binary.write_bytes(b"MZ" + b"x" * 10)
    with pytest.raises(ValueError, match="unsupported file type"):
        service.inspect_file(binary)

    huge = tmp_path / "huge.txt"
    huge.write_bytes(b"a" * 65)
    with pytest.raises(ValueError, match="file exceeds"):
        service.inspect_file(huge)


def test_workspace_is_read_only_and_cannot_escape_allowlisted_root(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('orbit')\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    grant = WorkspaceGrant(root)
    listing = grant.list_files()
    assert listing == ["src/app.py"]
    assert grant.read_text("src/app.py") == "print('orbit')\n"
    with pytest.raises(ValueError, match="workspace root"):
        grant.read_text("../outside.txt")


def test_workspace_rejects_symlink_escape(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = root / "linked.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    grant = WorkspaceGrant(root)
    with pytest.raises(ValueError, match="symlink"):
        grant.read_text("linked.txt")


def test_resource_status_contains_configuration_state_not_values(tmp_path, monkeypatch):
    monkeypatch.setenv("IBM_QUANTUM_TOKEN", "TOP-SECRET-TOKEN-VALUE")
    service = ProductService(tmp_path / "state")
    status = service.resource_status()
    encoded = json.dumps(status, sort_keys=True)
    assert "TOP-SECRET-TOKEN-VALUE" not in encoded
    assert status["ibm"]["IBM_QUANTUM_TOKEN"] == "configured"


def test_portable_export_keeps_credentials_and_authority_outside_substrate(tmp_path, monkeypatch):
    root = tmp_path / "state"
    monkeypatch.setenv("OPENAI_API_KEY", "sk-example-secret-that-must-not-travel")
    runtime = DurableRuntime(root)
    try:
        runtime.respond("remember marigold")
    finally:
        runtime.close()

    authority = AuthoritySession()
    authority.grant("repo_write")
    service = ProductService(root, authority=authority)
    bundle = tmp_path / "portable"
    receipt = service.export_portable(bundle)
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))

    assert receipt["authority"] == "NOT_TRANSFERRED"
    assert manifest["authority"] == "NOT_TRANSFERRED"
    assert manifest["credentials"] == "HOST_CONFIGURATION_EXCLUDED"
    assert "sk-example-secret-that-must-not-travel" not in (bundle / "runtime.sqlite3").read_bytes().decode("utf-8", errors="ignore")
