"""Regression: beastbox init must preserve user-authored configuration bytes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from beastbox.cli import main as beastbox_main
from beastbox.config import RuntimeConfig


def test_init_existing_custom_config_preserves_exact_bytes_and_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "custom" / "owner-beastbox.json"
    config_path.parent.mkdir()
    configured = RuntimeConfig(
        data_dir=str(tmp_path / "custom-data"),
        memory_db=str(tmp_path / "custom-data" / "important-memory.sqlite3"),
        evidence_dir=str(tmp_path / "custom-evidence"),
        proposals_dir=str(tmp_path / "custom-proposals"),
        local_model_name="my-private-local-model",
        local_model_url="http://127.0.0.1:12233",
    )
    # Deliberate non-default formatting catches any unintended reserialization.
    payload = (json.dumps(configured.__dict__, indent=4, ensure_ascii=False) + "\n").encode("utf-8")
    config_path.write_bytes(payload)
    monkeypatch.setattr(sys, "argv", ["beastbox", "init", "--config", str(config_path)])

    assert beastbox_main() == 0
    assert config_path.read_bytes() == payload
    loaded = RuntimeConfig.load(config_path)
    assert loaded.data_dir == configured.data_dir
    assert loaded.memory_db == configured.memory_db
    assert loaded.local_model_name == "my-private-local-model"
    assert loaded.local_model_url == "http://127.0.0.1:12233"
    for path in (configured.data_dir, configured.evidence_dir, configured.proposals_dir):
        assert Path(path).is_dir()


def test_init_missing_config_creates_defaults_and_directories(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "new-config" / "beastbox.json"
    assert not config_path.exists()
    monkeypatch.setattr(sys, "argv", ["beastbox", "init", "--config", str(config_path)])

    assert beastbox_main() == 0
    assert config_path.is_file()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["local_model_name"] == RuntimeConfig().local_model_name
    assert data["data_dir"] == RuntimeConfig().data_dir
    assert data["memory_db"] == RuntimeConfig().memory_db
    for path in (data["data_dir"], data["evidence_dir"], data["proposals_dir"]):
        assert Path(path).is_dir()
