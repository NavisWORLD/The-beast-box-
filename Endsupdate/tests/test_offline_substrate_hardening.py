from __future__ import annotations

import json
import socket
import urllib.request
from pathlib import Path

import pytest

from beastbox.persistent_substrate.offline import (
    FUNCTION_NOT_ESTABLISHED,
    GATE_NAMES,
    INVALID,
    OFFICIAL_BEAST_CLASSIFICATION,
    VERIFIED,
    OfflineModelCheckpoint,
    PythonNetworkGuard,
    _append_runtime_point,
    classify_offline_gates,
)


def _fixture(tmp_path: Path, *, model_id: str = "OFFLINE_MODEL_A", algorithm: str = "keyed_latest_memory_v1") -> Path:
    path = tmp_path / f"{model_id}.json"
    path.write_text(
        json.dumps(
            {
                "schema": "beastbox-offline-model-fixture-v1",
                "version": 1,
                "model_id": model_id,
                "algorithm": algorithm,
                "fallback": "NO_MEMORY",
                "write_phrase": "written-by-fixture",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_classification_fails_closed_for_missing_or_failed_structural_gate() -> None:
    assert classify_offline_gates({}) == INVALID
    gates = {name: True for name in GATE_NAMES}
    gates["OFFLINE_NO_NETWORK_ATTEMPTS"] = False
    assert classify_offline_gates(gates) == INVALID


def test_classification_distinguishes_functional_claim_from_structure() -> None:
    gates = {name: True for name in GATE_NAMES}
    gates["MODEL_B_PRE_SWAP_ACCESS"] = False
    assert classify_offline_gates(gates) == FUNCTION_NOT_ESTABLISHED
    gates["MODEL_B_PRE_SWAP_ACCESS"] = True
    assert classify_offline_gates(gates) == VERIFIED


def test_model_fixture_rejects_invalid_schema_version_identity_and_algorithm(tmp_path: Path) -> None:
    path = _fixture(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = 2
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="version mismatch"):
        OfflineModelCheckpoint.load(path)

    path = _fixture(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["model_id"] = "UNTRUSTED_MODEL"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="unsupported offline model identity"):
        OfflineModelCheckpoint.load(path)

    path = _fixture(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["algorithm"] = "unknown"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="unsupported offline model algorithm"):
        OfflineModelCheckpoint.load(path)


def test_model_fixture_recall_and_identity_are_deterministic(tmp_path: Path) -> None:
    model = OfflineModelCheckpoint.load(_fixture(tmp_path))
    assert model.recall([{"text": "PRE_SWAP_CANARY=amber cedar"}], key="PRE_SWAP_CANARY") == "amber cedar"
    assert model.recall([], key="missing") == "NO_MEMORY"
    assert model.create_write() == "written-by-fixture"
    assert model.invocation_count == 3
    assert model.identity["model_id"] == "OFFLINE_MODEL_A"
    assert len(model.identity["checkpoint_sha256"]) == 64


def test_runtime_points_chain_previous_hashes() -> None:
    points: list[dict[str, object]] = []
    identity = {"model_id": "OFFLINE_MODEL_A", "checkpoint_sha256": "a" * 64}
    first = _append_runtime_point(
        points,
        stage="A",
        model_identity=identity,
        memory_tip_sha256="b" * 64,
        state_tip_sha256="c" * 64,
        source_point_sha256s=["d" * 64],
    )
    second = _append_runtime_point(
        points,
        stage="B",
        model_identity=identity,
        memory_tip_sha256="e" * 64,
        state_tip_sha256="f" * 64,
        source_point_sha256s=[first["point_sha256"]],
    )
    assert first["previous_point_sha256"] == "0" * 64
    assert second["previous_point_sha256"] == first["point_sha256"]
    assert second["source_point_sha256s"] == [first["point_sha256"]]


def test_network_guard_blocks_and_restores_python_network_apis() -> None:
    original_connect = socket.socket.connect
    original_urlopen = urllib.request.urlopen
    guard = PythonNetworkGuard()
    with guard:
        with pytest.raises(RuntimeError, match="forbids network access"):
            socket.socket.connect(None, ("example.invalid", 443))  # type: ignore[arg-type]
        with pytest.raises(RuntimeError, match="forbids network access"):
            urllib.request.urlopen("https://example.invalid")
        assert guard.attempt_count == 2
    assert socket.socket.connect is original_connect
    assert urllib.request.urlopen is original_urlopen
    assert not guard.active


def test_network_guard_cannot_be_entered_twice() -> None:
    guard = PythonNetworkGuard()
    with guard:
        with pytest.raises(RuntimeError, match="already active"):
            guard.__enter__()


def test_official_scientific_boundary_is_explicit() -> None:
    assert "NOT_ESTABLISHED" in OFFICIAL_BEAST_CLASSIFICATION
