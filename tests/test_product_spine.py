from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from beastbox import HISTORICAL_ALIASES, MemoryStore, ProvenanceLedger, Runtime, __version__
from beastbox.cli import SCIENTIFIC_ANCHOR, SCIENTIFIC_CLASSIFICATION
from beastbox.cli import main as beastbox_main
from beastbox.config import RuntimeConfig
from beastbox.cypher.models import assert_loopback
from beastbox.evidence import EvidenceLedger
from beastbox.hashutil import sha256_obj
from beastbox.memory import ReconciliationMemory
from beastbox.providers import LocalOllamaProvider, ReferenceTextProvider
from beastbox.runtime import CosmosRuntime
from beastbox.state import MissionState


def test_version_and_aliases():
    assert __version__ == "0.6.0"
    assert "Zeref" in HISTORICAL_ALIASES
    assert Runtime is CosmosRuntime
    assert MemoryStore is ReconciliationMemory
    assert ProvenanceLedger is EvidenceLedger


def test_malformed_config_rejected(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not-json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        RuntimeConfig.load(p)


def test_config_missing_file_creates_defaults(tmp_path: Path):
    p = tmp_path / "new.json"
    cfg = RuntimeConfig.load(p)
    assert p.exists()
    assert cfg.quantum_heart_mode == "off"
    assert cfg.local_model_url.startswith("http://127.0.0.1")


def test_empty_memory_search(tmp_path: Path):
    m = ReconciliationMemory(tmp_path / "empty.sqlite3")
    try:
        assert m.search("anything") == []
        assert m.stats()["memories"] == 0
    finally:
        m.close()


def test_corrupted_memory_file(tmp_path: Path):
    path = tmp_path / "corrupt.sqlite3"
    path.write_bytes(b"this is not sqlite")
    with pytest.raises(sqlite3.DatabaseError):
        ReconciliationMemory(path)


def test_ledger_tamper_fails_verify():
    led = EvidenceLedger()
    led.append("a", {"n": 1})
    led.append("b", {"n": 2})
    assert led.verify()
    led.events[0].payload["n"] = 99
    assert led.verify() is False


def test_ledger_hashes_are_deterministic():
    a = EvidenceLedger()
    b = EvidenceLedger()
    a.append("turn", {"text": "same"})
    b.append("turn", {"text": "same"})
    assert a.head == b.head == sha256_obj(
        {"index": 0, "kind": "turn", "payload": {"text": "same"}, "previous_hash": "GENESIS"}
    )


def test_loopback_accepts_localhost_and_ipv6():
    assert_loopback("http://localhost:11434")
    assert_loopback("http://127.0.0.1:11434")
    assert_loopback("http://[::1]:11434")


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com:11434",
        "http://8.8.8.8:11434",
        "http://169.254.169.254/",
        "not-a-url",
        "http://127.0.0.1.attacker.example/",
    ],
)
def test_loopback_rejects_non_local(url):
    with pytest.raises(ValueError):
        assert_loopback(url)


def test_ollama_provider_rejects_remote():
    with pytest.raises(ValueError):
        LocalOllamaProvider(base_url="http://203.0.113.5:11434")


def test_unavailable_model_does_not_break_reference_chat(tmp_path: Path):
    cfg = RuntimeConfig(
        data_dir=str(tmp_path),
        memory_db=str(tmp_path / "m.sqlite3"),
        evidence_dir=str(tmp_path / "ev"),
        proposals_dir=str(tmp_path / "pr"),
    )
    rt = CosmosRuntime(cfg, provider=ReferenceTextProvider())
    try:
        out = rt.respond("ping")
        assert "COSMOS reference" in out["response"]
        assert out["state_hash"]
        assert rt.ledger.verify()
    finally:
        rt.close()


def test_cli_init_doctor_starter_chat(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["beastbox", "init"])
    assert beastbox_main() == 0
    assert Path("beastbox.json").exists()
    monkeypatch.setattr("sys.argv", ["beastbox", "doctor"])
    assert beastbox_main() == 0
    monkeypatch.setattr("sys.argv", ["beastbox", "starter"])
    assert beastbox_main() == 0
    monkeypatch.setattr("sys.argv", ["beastbox", "chat", "store the word lantern"])
    assert beastbox_main() == 0


def test_scientific_strings_unchanged():
    assert SCIENTIFIC_ANCHOR == "c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f"
    assert SCIENTIFIC_CLASSIFICATION == "ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED"


def test_mission_state_digest_stable():
    s1 = MissionState(mission_id="m", objective="o")
    s2 = MissionState(mission_id="m", objective="o")
    assert s1.digest() == s2.digest()
