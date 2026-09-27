"""Product ContinuityStore receipt tests across restart and adversarial boundaries.

The test authority is stored outside the runtime path. Production independent
authentication requires a separately protected OS account/host for this store.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider
from beastbox.trusted_anchor import AnchorMismatch, ContinuityTip, SQLiteAnchorAuthority


def setup_anchor(tmp_path: Path) -> SQLiteAnchorAuthority:
    protected = tmp_path / "separate-authority"
    protected.mkdir(exist_ok=True)
    return SQLiteAnchorAuthority(protected / "receipts.sqlite3")


def test_product_anchor_genesis_update_and_restart(tmp_path: Path) -> None:
    authority = setup_anchor(tmp_path)
    root = tmp_path / "user-runtime"
    runtime = DurableRuntime(root, ReferenceTextProvider(), anchor_authority=authority)
    try:
        genesis = runtime.inspect()
        assert genesis["anchor_mode"] == "external_cas"
        assert genesis["sequence"] == 0
        first = runtime.respond("The violet kite belongs to Cory.")
        assert first["checkpoint"]["sequence"] == 1
        latest = authority.latest(genesis["system_id"])
        assert latest is not None and latest.sequence == 1
        assert latest.sha256 == first["checkpoint"]["sha256"]
    finally:
        runtime.close()
        authority.close()

    # A brand-new object, fresh SQLite connections, separate authority path.
    resumed_authority = SQLiteAnchorAuthority(tmp_path / "separate-authority/receipts.sqlite3")
    resumed = DurableRuntime(root, ReferenceTextProvider(), anchor_authority=resumed_authority)
    try:
        assert resumed.inspect()["sequence"] == 1
        newer = resumed.store_external_memory("External context with explicit owner consent.")
        assert newer["checkpoint"]["sequence"] == 2
        assert resumed_authority.latest(resumed.system_id).sequence == 2
    finally:
        resumed.close()
        resumed_authority.close()


def test_existing_unanchored_runtime_cannot_self_enroll_after_tampering(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    unanchored = DurableRuntime(root, ReferenceTextProvider())
    unanchored.respond("Old state the anchor never witnessed.")
    unanchored.close()
    authority = setup_anchor(tmp_path)
    try:
        with pytest.raises(AnchorMismatch, match="missing independently retained anchor"):
            DurableRuntime(root, ReferenceTextProvider(), anchor_authority=authority)
    finally:
        authority.close()


def test_coherent_checkpoint_database_rollback_is_detected_on_restart(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    authority = setup_anchor(tmp_path)
    runtime = DurableRuntime(root, ReferenceTextProvider(), anchor_authority=authority)
    runtime.close()
    # Snapshot the internally valid original genesis (ledger and checkpoint).
    original = tmp_path / "old-but-self-consistent.sqlite3"
    with sqlite3.connect(root / "runtime.sqlite3") as conn, sqlite3.connect(original) as witness:
        conn.backup(witness)

    runtime = DurableRuntime(root, ReferenceTextProvider(), anchor_authority=authority)
    runtime.respond("An added turn should persist in the independent authority.")
    runtime.close()
    shutil.copyfile(original, root / "runtime.sqlite3")
    try:
        # Local continuity still verifies: only the separately protected
        # authority can detect this fully self-consistent old database.
        with pytest.raises(AnchorMismatch, match="external authority disagrees"):
            DurableRuntime(root, ReferenceTextProvider(), anchor_authority=authority)
    finally:
        authority.close()


class PublicationFailure:
    def __init__(self, delegate: SQLiteAnchorAuthority):
        self.delegate = delegate

    def latest(self, system_id: str) -> ContinuityTip | None:
        return self.delegate.latest(system_id)

    def advance(self, expected: ContinuityTip | None, new: ContinuityTip) -> None:
        if expected is not None:
            raise OSError("injected off-ledger service outage after SQLite commit")
        self.delegate.advance(expected, new)


def test_post_commit_authority_outage_blocks_future_operations(tmp_path: Path) -> None:
    authority = setup_anchor(tmp_path)
    root = tmp_path / "runtime"
    runtime = DurableRuntime(root, ReferenceTextProvider(), anchor_authority=PublicationFailure(authority))
    try:
        with pytest.raises(AnchorMismatch, match="checkpoint committed"):
            runtime.respond("This commit was made but was not externally acknowledged.")
        with pytest.raises(AnchorMismatch, match="reconciliation"):
            runtime.inspect()
        with pytest.raises(AnchorMismatch, match="reconciliation"):
            runtime.respond("A second unauthorized continuation must not occur.")
    finally:
        runtime.close()
    try:
        with pytest.raises(AnchorMismatch, match="external authority disagrees"):
            DurableRuntime(root, ReferenceTextProvider(), anchor_authority=authority)
    finally:
        authority.close()


def test_authority_rejects_stale_and_nonmonotonic_updates(tmp_path: Path) -> None:
    authority = setup_anchor(tmp_path)
    try:
        identity = "owner-runtime-test"
        first = ContinuityTip(identity, 0, "a" * 64, "b" * 64)
        second = ContinuityTip(identity, 1, "c" * 64, "d" * 64)
        authority.advance(None, first)
        with pytest.raises(AnchorMismatch, match="authority has moved"):
            authority.advance(None, first)
        with pytest.raises(AnchorMismatch, match="nonmonotonic"):
            authority.advance(first, ContinuityTip(identity, 3, "e" * 64, "f" * 64))
        authority.advance(first, second)
        with pytest.raises(AnchorMismatch, match="stale"):
            authority.advance(first, ContinuityTip(identity, 1, "f" * 64, "e" * 64))
    finally:
        authority.close()


def test_same_runtime_root_authority_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    authority = SQLiteAnchorAuthority(root / "unsafe.sqlite3")
    try:
        with pytest.raises(ValueError, match="outside runtime root"):
            DurableRuntime(root, ReferenceTextProvider(), anchor_authority=authority)
    finally:
        authority.close()


def test_new_process_validates_caller_owned_external_tip(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    authority = setup_anchor(tmp_path)
    runtime = DurableRuntime(root, ReferenceTextProvider(), anchor_authority=authority)
    runtime.respond("Retain independent state across process exit.")
    runtime.close()
    authority.close()
    worker = """
import sys
from beastbox.durable import DurableRuntime
from beastbox.providers import ReferenceTextProvider
from beastbox.trusted_anchor import SQLiteAnchorAuthority
a=SQLiteAnchorAuthority(sys.argv[2])
r=DurableRuntime(sys.argv[1], ReferenceTextProvider(), anchor_authority=a)
print(r.inspect()["sequence"])
r.close()
a.close()
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1]) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", worker, str(root), str(tmp_path / "separate-authority/receipts.sqlite3")],
        check=False, capture_output=True, text=True, timeout=30, env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1"


def test_unanchored_default_remains_explicit(tmp_path: Path) -> None:
    runtime = DurableRuntime(tmp_path / "ordinary", ReferenceTextProvider())
    try:
        assert runtime.inspect()["anchor_mode"] == "unanchored"
    finally:
        runtime.close()
