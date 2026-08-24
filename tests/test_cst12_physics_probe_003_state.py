from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_token_ids_are_deterministic():
    from scripts.build_cst12_physics_probe_003_state import derive_token_ids

    seed = "12" * 32
    a = derive_token_ids(seed, 50257, 12)
    b = derive_token_ids(seed, 50257, 12)
    assert a == b
    assert len(a) == 12
    assert all(0 <= v < 50257 for v in a)


def test_state_builder_rejects_bad_seed(tmp_path: Path):
    from scripts.build_cst12_physics_probe_003_state import build_state_packet

    with pytest.raises(ValueError):
        build_state_packet(tmp_path, "not-a-sha")


def test_full_source_snapshot_is_byte_reproducible(tmp_path: Path):
    source = os.environ.get("CST12_CORRECTED_SOURCE_ROOT", "").strip()
    if not source:
        pytest.skip("CST12_CORRECTED_SOURCE_ROOT not configured")
    pytest.importorskip("torch")

    script = Path("scripts/build_cst12_physics_probe_003_state.py")
    seed = "34" * 32
    out1 = tmp_path / "a.json"
    out2 = tmp_path / "b.json"
    for out in (out1, out2):
        subprocess.run(
            [sys.executable, str(script), "--source-root", source, "--seed-root", seed, "--output", str(out)],
            check=True,
            env={**os.environ, "IBM_QUANTUM_TOKEN": "SHOULD_NOT_BE_READ"},
        )
    assert out1.read_bytes() == out2.read_bytes()
    data = json.loads(out1.read_text())
    packet = data["bridge_packet"]
    assert len(packet["phase12"]) == 12
    assert len(packet["dynamic12"]) == 12
    assert len(packet["hebbian24"]) == 24
    assert len(packet["chaos18"]) == 18
    assert len(packet["phase12"] + packet["dynamic12"] + packet["hebbian24"] + packet["chaos18"]) == 66
    assert data["model_config"]["d_model"] == 512
    assert data["model_config"]["n_layers"] == 6
    assert data["model_config"]["dropout"] == 0.0
    assert data["source_commit"] == "0e2bca3895bd40243cc12a9d64ad119544759f95"
    assert data["credential_material_recorded"] is False
