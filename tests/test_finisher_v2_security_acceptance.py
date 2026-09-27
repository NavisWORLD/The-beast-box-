"""Additional secure-V2 crash boundaries and externally supplied restart receipt tests.

A caller-owned off-ledger receipt is only independent if the caller protects it
outside the ledger writer's trust domain. A local same-actor JSON sidecar is not
an authenticated anchor and must never be advertised as such.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from beastbox.dad_son_v2 import DadSonLedger
from beastbox.persistent_substrate.ledger_v2 import (
    MemoryChainVerificationError,
    verify_memory_chain,
)

PARENT = "a" * 64


def _new(tmp_path: Path) -> DadSonLedger:
    return DadSonLedger(tmp_path / "data.sqlite3", tmp_path / "events.jsonl", parent_sha256=PARENT)


def test_precommit_failure_leaves_neither_sqlite_memory_nor_jsonl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = _new(tmp_path)

    def fail_before_commit(*_args: object, **_kwargs: object) -> None:
        raise OSError("failure inside transaction before commit")

    monkeypatch.setattr(ledger.memory, "store", fail_before_commit)
    with pytest.raises(OSError, match="before commit"):
        ledger.append_experience(actor="Dad", text="must not commit", kind="test", session_id="a4")
    assert ledger.memory.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0
    assert ledger.memory.db.execute("SELECT COUNT(*) FROM dad_son_outbox").fetchone()[0] == 0
    assert not ledger.evidence_jsonl.exists()
    ledger.close()
    again = _new(tmp_path)
    try:
        assert again.recover_pending() == 0
    finally:
        again.close()


def test_failure_during_jsonl_append_preserves_suspect_and_committed_outbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = _new(tmp_path)
    def crash_mid_write(_row: object) -> None:
        with ledger.evidence_jsonl.open("ab") as handle:
            handle.write(b'{"unfinished":')
            handle.flush()
            os.fsync(handle.fileno())
        raise OSError("injected partial JSONL append")

    monkeypatch.setattr(ledger, "_write_outbox_row", crash_mid_write)
    with pytest.raises(OSError, match="partial JSONL"):
        ledger.append_experience(actor="Dad", text="pending after partial", kind="test", session_id="a4")
    suspect = ledger.evidence_jsonl.read_bytes()
    assert suspect == b'{"unfinished":'
    assert ledger.memory.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 1
    assert ledger.memory.db.execute("SELECT COUNT(*) FROM dad_son_outbox").fetchone()[0] == 1
    ledger.close()

    restarted = _new(tmp_path)
    try:
        with pytest.raises((RuntimeError, MemoryChainVerificationError), match="invalid JSON|partial"):
            restarted.recover_pending()
        assert restarted.evidence_jsonl.read_bytes() == suspect
        assert restarted.memory.db.execute("SELECT COUNT(*) FROM dad_son_outbox").fetchone()[0] == 1
    finally:
        restarted.close()


def test_outbox_divergent_replay_fails_without_new_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = _new(tmp_path)
    original_ack = ledger._ack_outbox_id
    def fail_ack(_memory_id: int) -> None:
        raise OSError("crash before acknowledgement")
    monkeypatch.setattr(ledger, "_ack_outbox_id", fail_ack)
    with pytest.raises(OSError, match="before acknowledgement"):
        ledger.append_experience(actor="Dad", text="correct event", kind="test", session_id="a4")
    signed_bytes = ledger.evidence_jsonl.read_bytes()
    pending = json.loads(ledger.memory.db.execute(
        "SELECT record_json FROM dad_son_outbox WHERE memory_id=1"
    ).fetchone()[0])
    pending["text"] = "maliciously divergent pending row"
    ledger.memory.db.execute(
        "UPDATE dad_son_outbox SET record_json=? WHERE memory_id=1",
        (json.dumps(pending, sort_keys=True, separators=(",", ":")),),
    )
    ledger.memory.db.commit()
    monkeypatch.setattr(ledger, "_ack_outbox_id", original_ack)
    ledger.close()

    restarted = _new(tmp_path)
    try:
        with pytest.raises(RuntimeError, match="conflicts"):
            restarted.recover_pending()
        assert restarted.evidence_jsonl.read_bytes() == signed_bytes
        assert restarted.memory.db.execute("SELECT COUNT(*) FROM dad_son_outbox").fetchone()[0] == 1
    finally:
        restarted.close()


def test_cross_restart_checks_caller_protected_expected_tip_and_count(tmp_path: Path) -> None:
    """Pass trusted receipt independently through process argv, not a sibling JSON file."""
    ledger = _new(tmp_path)
    try:
        first = ledger.append_experience(actor="Dad", text="remember A", kind="test", session_id="a1")
        ledger.append_experience(actor="Dad", text="remember B", kind="test", session_id="a1")
        receipt = verify_memory_chain(ledger.evidence_jsonl, parent_sha256=PARENT)
        assert receipt.record_count == 2
        assert receipt.tip_sha256 != first["record_sha256"]
        ledger_file = ledger.evidence_jsonl
    finally:
        ledger.close()

    worker = """
import sys
from beastbox.persistent_substrate.ledger_v2 import verify_memory_chain
path, parent, count, tip = sys.argv[1:]
result = verify_memory_chain(path, parent_sha256=parent, expected_record_count=int(count), expected_tip_sha256=tip)
print(result.tip_sha256)
"""
    def restarted_read() -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1]) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-c", worker, str(ledger_file), PARENT, str(receipt.record_count), receipt.tip_sha256],
            capture_output=True, text=True, env=env, check=False, timeout=25,
        )

    good = restarted_read()
    assert good.returncode == 0, good.stderr
    assert good.stdout.strip() == receipt.tip_sha256
    ledger_file.write_bytes(b"".join(ledger_file.read_bytes().splitlines(keepends=True)[:-1]))
    bad = restarted_read()
    assert bad.returncode != 0
    assert "record count" in bad.stderr
