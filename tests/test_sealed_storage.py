from __future__ import annotations

import json
from pathlib import Path

import pytest

from beastbox.durable import DurableRuntime
from beastbox.portable_state import export_snapshot
from beastbox.sealed_storage import (
    AuthenticationFailed,
    CryptoUnavailable,
    SealedStorageError,
    crypto_available,
    encryption_status,
    export_sealed_snapshot,
    import_sealed_snapshot,
    maybe_seal_root,
    maybe_unseal_root,
    seal_bytes,
    seal_runtime_root,
    unseal_bytes,
    unseal_runtime_root,
    verify_sealed_snapshot,
)


pytestmark = pytest.mark.skipif(not crypto_available(), reason="cosmos-beast-box[secure] not installed")

PASSPHRASE = "owner-seal-passphrase"


def _runtime(root: Path, text: str = "remember sunflower code marigold") -> None:
    runtime = DurableRuntime(root)
    try:
        runtime.respond(text)
    finally:
        runtime.close()


def test_seal_roundtrip_and_wrong_passphrase() -> None:
    blob = seal_bytes(b"durable-bytes", PASSPHRASE)
    assert blob.startswith(b"BBSEAL1\n")
    assert unseal_bytes(blob, PASSPHRASE) == b"durable-bytes"
    with pytest.raises(AuthenticationFailed):
        unseal_bytes(blob, "wrong-passphrase")


def test_runtime_seal_removes_plaintext_and_unseal_restores(tmp_path: Path) -> None:
    root = tmp_path / "state"
    _runtime(root)
    receipt = seal_runtime_root(root, PASSPHRASE)
    assert receipt["authority"] == "NOT_TRANSFERRED"
    assert receipt["credentials"] == "HOST_CONFIGURATION_EXCLUDED"
    assert not (root / "runtime.sqlite3").exists()
    assert (root / "runtime.sqlite3.sealed").is_file()
    restored = unseal_runtime_root(root, PASSPHRASE)
    assert restored["unsealed"] is True
    runtime = DurableRuntime(root)
    try:
        prompt = runtime.respond("recall sunflower")["model"]["prompt"]
    finally:
        runtime.close()
    assert "marigold" in prompt


def test_idle_helpers_use_env_and_leave_working_copy_when_unset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "state"
    _runtime(root)
    monkeypatch.delenv("BEASTBOX_SEAL_PASSPHRASE", raising=False)
    assert maybe_seal_root(root)["sealed"] is False
    assert (root / "runtime.sqlite3").is_file()
    monkeypatch.setenv("BEASTBOX_SEAL_PASSPHRASE", PASSPHRASE)
    assert maybe_seal_root(root)["sealed"] is True
    assert not (root / "runtime.sqlite3").exists()
    monkeypatch.delenv("BEASTBOX_SEAL_PASSPHRASE")
    with pytest.raises(SealedStorageError):
        maybe_unseal_root(root)
    monkeypatch.setenv("BEASTBOX_SEAL_PASSPHRASE", PASSPHRASE)
    DurableRuntime(root).close()
    assert (root / "runtime.sqlite3.sealed").is_file()


def test_sealed_portable_keeps_authority_out_and_refuses_tamper(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    _runtime(origin)
    bundle = tmp_path / "sealed-portable"
    receipt = export_sealed_snapshot(origin, bundle, PASSPHRASE)
    assert receipt["authority"] == "NOT_TRANSFERRED"
    assert receipt["encryption"] == "ACTIVE"
    names = {path.name for path in bundle.iterdir()}
    assert names == {"manifest.json", "runtime.sqlite3.sealed"}
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["authority"] == "NOT_TRANSFERRED"
    assert "runtime.sqlite3" not in names
    verified = verify_sealed_snapshot(bundle, receipt["manifest_sha256"], PASSPHRASE)
    assert verified["verified"] is True
    destination = tmp_path / "restored"
    imported = import_sealed_snapshot(bundle, destination, receipt["manifest_sha256"], PASSPHRASE)
    assert imported["restored"] is True
    runtime = DurableRuntime(destination)
    try:
        assert runtime.inspect()["valid"] is True
        assert not runtime.policy.allowed
    finally:
        runtime.close()
    raw = bytearray((bundle / "runtime.sqlite3.sealed").read_bytes())
    raw[-1] ^= 1
    (bundle / "runtime.sqlite3.sealed").write_bytes(bytes(raw))
    with pytest.raises((AuthenticationFailed, SealedStorageError)):
        verify_sealed_snapshot(bundle, receipt["manifest_sha256"], PASSPHRASE)


def test_v1_plaintext_export_still_works_without_passphrase(tmp_path: Path) -> None:
    origin = tmp_path / "origin"
    _runtime(origin)
    bundle = tmp_path / "v1"
    receipt = export_snapshot(origin, bundle)
    assert receipt["authority"] == "NOT_TRANSFERRED"
    assert {path.name for path in bundle.iterdir()} == {"manifest.json", "runtime.sqlite3"}


def test_encryption_status_vocabulary() -> None:
    status = encryption_status(sealed=False)
    assert status["status"] in {"AVAILABLE", "MISSING_SECURE_EXTRA"}
    if crypto_available():
        assert encryption_status(sealed=True)["status"] == "ACTIVE"


def test_crypto_unavailable_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("beastbox.sealed_storage.crypto_available", lambda: False)
    with pytest.raises(CryptoUnavailable):
        from beastbox.sealed_storage import require_crypto

        require_crypto()
