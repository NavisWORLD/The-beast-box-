import json
from pathlib import Path

import pytest

from beastbox.creature.manifest import CreatureManifest
from beastbox.creature.project import create_creature_project


def test_manifest_defaults_to_balanced_54d_creature():
    manifest = CreatureManifest.from_dict({
        "name": "Nova",
        "species": "cosmos.quantum-creature",
        "version": "1",
        "backbone": {"kind": "native", "path": "weights/native/spark.pt"},
    })
    assert manifest.name == "Nova"
    assert manifest.state["dimensions"] == 54
    assert manifest.state["dyn12"] is True
    assert manifest.state["block_balance"] is True
    assert manifest.memory["persistent"] is True
    assert manifest.heartbeat["enabled"] is True


def test_manifest_rejects_unsupported_state_dimensions():
    with pytest.raises(ValueError, match="dimensions"):
        CreatureManifest.from_dict({
            "name": "Bad",
            "species": "cosmos.quantum-creature",
            "version": "1",
            "backbone": {"kind": "native", "path": "model.pt"},
            "state": {"dimensions": 13},
        })


def test_create_creature_project_writes_manifest_and_runtime_dirs(tmp_path: Path):
    root = create_creature_project("Nova", tmp_path)
    manifest_path = root / "creature.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["name"] == "Nova"
    assert (root / "memory").is_dir()
    assert (root / "evidence").is_dir()
    assert (root / "weights" / "native").is_dir()
    loaded = CreatureManifest.load(manifest_path)
    assert loaded.name == "Nova"
