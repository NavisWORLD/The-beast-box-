from __future__ import annotations

from pathlib import Path

import pytest

from beastbox import quantum
from beastbox.config import RuntimeConfig
from beastbox.quantum import submit_real, submit_real_chunks
from beastbox.quantum_heart import HeartMode, QuantumHeart


def test_importing_public_package_does_not_require_qiskit_or_ollama():
    import beastbox
    from beastbox import MemoryStore, ProvenanceLedger, Runtime, StateController

    assert beastbox.__version__ == "0.6.0"
    assert Runtime is not None
    assert MemoryStore is not None
    assert StateController is not None
    assert ProvenanceLedger is not None


def test_importing_quantum_helper_does_not_import_qiskit():
    import sys

    assert "qiskit" not in sys.modules
    assert "qiskit_ibm_runtime" not in sys.modules
    with pytest.raises(RuntimeError, match="quantum extras"):
        quantum._imports()


def test_ibm_submit_refuses_without_human_confirm():
    with pytest.raises(RuntimeError, match="confirm=True"):
        submit_real("01", confirm=False)
    with pytest.raises(RuntimeError, match="confirm=True"):
        submit_real_chunks(["01"], confirm=False)


def test_ibm_submit_without_confirm_does_not_need_token(monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    monkeypatch.delenv("IBM_QUANTUM_INSTANCE", raising=False)
    with pytest.raises(RuntimeError, match="confirm=True"):
        submit_real("01")


def test_quantum_heart_defaults_off():
    heart = QuantumHeart()
    out = heart.update([1.0], [1.0])
    assert heart.mode is HeartMode.OFF
    assert out["mode"] == "off"
    assert out["coherence"] == 0.0


def test_runtime_config_defaults_are_local_and_off(tmp_path: Path):
    cfg = RuntimeConfig.load(tmp_path / "beastbox.json")
    assert cfg.quantum_heart_mode == "off"
    assert cfg.local_model_url.startswith("http://127.0.0.1")


def test_import_does_not_write_memory_or_evidence(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import importlib

    import beastbox

    importlib.reload(beastbox)
    stray = list(tmp_path.rglob("*"))
    assert stray == [], stray


def test_soul_import_is_software_only():
    from beastbox import soul

    assert "SoulToken" in soul.__all__
    text = Path(soul.__file__).read_text(encoding="utf-8")
    assert "does not claim a literal soul" in text


def test_env_example_has_empty_credential_slots():
    text = Path(__file__).resolve().parents[1].joinpath(".env.example").read_text(encoding="utf-8")
    token = next(line for line in text.splitlines() if line.startswith("IBM_QUANTUM_TOKEN="))
    instance = next(line for line in text.splitlines() if line.startswith("IBM_QUANTUM_INSTANCE="))
    assert token == "IBM_QUANTUM_TOKEN="
    assert instance == "IBM_QUANTUM_INSTANCE="


def test_product_docs_do_not_inflate_a_universal_negative():
    root = Path(__file__).resolve().parents[1]
    forbidden = "verified negative"
    hits = []
    for rel in [
        "README.md",
        "docs/CLAIM_BOUNDARIES.md",
        "docs/EVIDENCE_INDEX.md",
        "docs/SYSTEM_CAPABILITIES.md",
        "CHANGELOG.md",
        "PROJECT_STATUS.json",
    ]:
        text = (root / rel).read_text(encoding="utf-8").lower()
        if forbidden in text:
            hits.append(rel)
        assert "engineering_isolation_verified_causal_resource_source_not_established" in text or rel.endswith(
            (".json", "SYSTEM_CAPABILITIES.md")
        )
    assert hits == [], hits
