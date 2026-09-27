"""Finisher V2 lineage, isolation, negative-integrity and historical-routing tests."""
from __future__ import annotations

import ast
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from beastbox import dad_son as historical_dad_son
from beastbox import dad_son_v2
from beastbox.persistent_substrate import ledger as historical_ledger
from beastbox.persistent_substrate import ledger_v2, substrate as historical_substrate, substrate_v2
from beastbox.versioning import (
    FROZEN_SHA256,
    HISTORICAL_ANCHOR,
    PINNED_MANIFEST_SHA256,
    V2_PATHS,
    VersionIntegrityError,
    verify_versioned_sources,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture_tree(tmp_path: Path) -> Path:
    for path in (
        *FROZEN_SHA256,
        *V2_PATHS.values(),
        "docs/VERSION_MANIFEST.json",
        "docs/VERSION_MANIFEST.sha256",
    ):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    return tmp_path


def test_versioned_sources_are_exact_and_manifest_is_pinned() -> None:
    receipt = verify_versioned_sources(ROOT)
    assert receipt["mapping_count"] == 3
    assert receipt["manifest_sha256"] == PINNED_MANIFEST_SHA256
    assert receipt["historical_anchor"] == HISTORICAL_ANCHOR
    assert receipt["verified_git_anchor"] is False
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == expected
               for p, expected in FROZEN_SHA256.items())


@pytest.mark.parametrize("path", [
    "beastbox/dad_son.py",
    "beastbox/persistent_substrate/ledger.py",
    "beastbox/persistent_substrate/substrate.py",
    "beastbox/dad_son_v2.py",
    "beastbox/persistent_substrate/ledger_v2.py",
    "beastbox/persistent_substrate/substrate_v2.py",
])
def test_version_integrity_rejects_single_byte_source_change(tmp_path: Path, path: str) -> None:
    _fixture_tree(tmp_path)
    (tmp_path / path).write_bytes((tmp_path / path).read_bytes() + b"tampered")
    with pytest.raises(VersionIntegrityError, match="source SHA-256 mismatch"):
        verify_versioned_sources(tmp_path)


def test_version_integrity_rejects_forged_or_noncanonical_manifest(tmp_path: Path) -> None:
    _fixture_tree(tmp_path)
    manifest_path = tmp_path / "docs/VERSION_MANIFEST.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["mappings"][0]["v2_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(VersionIntegrityError, match="manifest digest mismatch"):
        verify_versioned_sources(tmp_path)


def test_version_integrity_rejects_manifest_sidecar_mutation(tmp_path: Path) -> None:
    _fixture_tree(tmp_path)
    (tmp_path / "docs/VERSION_MANIFEST.sha256").write_text("0" * 64, encoding="ascii")
    with pytest.raises(VersionIntegrityError, match="sidecar mismatch"):
        verify_versioned_sources(tmp_path)


def test_versioned_lineage_headers_match_independently_verified_originals() -> None:
    for old, newer in V2_PATHS.items():
        docstring = ast.get_docstring(ast.parse((ROOT / newer).read_text(encoding="utf-8")))
        assert docstring is not None
        assert old in docstring
        assert FROZEN_SHA256[old] in docstring
        assert HISTORICAL_ANCHOR in docstring


def test_historical_imports_remain_v1_while_v2_is_explicit() -> None:
    assert historical_substrate.PersistentSubstrate.__module__.endswith(".substrate")
    assert substrate_v2.PersistentSubstrate.__module__.endswith(".substrate_v2")
    assert historical_ledger.StateEventLedger.__module__.endswith(".ledger")
    assert ledger_v2.StateEventLedger.__module__.endswith(".ledger_v2")
    assert historical_dad_son.DadSonLedger.__module__.endswith(".dad_son")
    assert dad_son_v2.DadSonLedger.__module__.endswith(".dad_son_v2")
    historical_runner = (ROOT / "beastbox/persistent_substrate/runner.py").read_text(encoding="utf-8")
    historical_script = (ROOT / "scripts/run_persistent_substrate_model_swap_002.py").read_text(encoding="utf-8")
    assert "from beastbox.persistent_substrate.substrate import (" in historical_runner
    assert "from beastbox.persistent_substrate.substrate import PersistentSubstrate" in historical_script
    assert "substrate_v2" not in historical_runner + historical_script
    active = (ROOT / "beastbox/persistent_substrate/substrate_v2.py").read_text(encoding="utf-8")
    assert "from beastbox.dad_son_v2 import DadSonLedger" in active
    assert "from .ledger_v2 import (" in active
    assert "from beastbox.dad_son import DadSonLedger" not in active
    assert "from .ledger import (" not in active


def test_secure_v2_does_not_delegate_writes_or_verification_to_v1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("security-critical V1 path was called")

    monkeypatch.setattr(historical_dad_son.DadSonLedger, "append_experience", forbidden)
    monkeypatch.setattr(historical_ledger, "verify_memory_chain", forbidden)
    monkeypatch.setattr(historical_ledger.StateEventLedger, "append", forbidden)

    ledger = dad_son_v2.DadSonLedger(
        tmp_path / "m.sqlite3", tmp_path / "m.jsonl", parent_sha256="a" * 64
    )
    try:
        row = ledger.append_experience(
            actor="Cory", text="versioned source proof", kind="integration", session_id="v2"
        )
        assert ledger.recover_pending() == 0
        assert ledger_v2.get_verified_memory_record(
            tmp_path / "m.jsonl", 1, parent_sha256="a" * 64
        )["record_sha256"] == row["record_sha256"]
        state = ledger_v2.StateEventLedger(tmp_path / "state.jsonl")
        event = state.append("TEST", {}, "2026-09-27T00:00:00+00:00")
        assert state.verify().tip_sha256 == event["event_sha256"]
    finally:
        ledger.close()
