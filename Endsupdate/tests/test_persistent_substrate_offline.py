from __future__ import annotations

import json
import socket
import urllib.request
from pathlib import Path

import pytest

from beastbox.persistent_substrate.ledger import (
    MemoryChainVerificationError,
    assemble_canonical_memory,
    verify_memory_chain,
    write_corrupted_control,
)
from beastbox.persistent_substrate.offline import (
    OfflineModelCheckpoint,
    PythonNetworkGuard,
    build_archived_workload_points,
    classify_offline_gates,
)
from beastbox.persistent_substrate.protocol import sha256_file


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "persistent-substrate-model-swap-001"
MODEL_A = EXP / "fixtures" / "model_a.json"
MODEL_B = EXP / "fixtures" / "model_b.json"
PREREG = EXP / "offline-preregistration.json"
MEMORY_MANIFEST = ROOT / "experiments" / "zeref-dad-son-001" / "memory" / "ledger-manifest.json"
WITNESSES = ROOT / "evidence" / "final-whole-organism-001" / "resource-source" / "historical-hardware-witnesses.jsonl"


def test_offline_preregistration_and_fixture_hashes_are_frozen() -> None:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    assert prereg["experiment_id"] == "persistent-substrate-model-swap-001"
    assert prereg["cloud_dependency_required"] is False
    assert prereg["fresh_ibm_jobs"] == 0
    assert prereg["fresh_rigetti_jobs"] == 0
    assert prereg["model_order"] == ["OFFLINE_MODEL_A", "OFFLINE_MODEL_B", "OFFLINE_MODEL_A"]
    assert sha256_file(MODEL_A) == "6aaa7f6a922dd3cde5c8c154c6d71e479393797d366eef8f6c28c077d69a2470"
    assert sha256_file(MODEL_B) == "cb9b280e3acd43de49cbf31bf519efdd00ac84099739e229b7fab0f335a19f7f"


def test_offline_models_are_distinct_and_returning_a_is_identical() -> None:
    first_a = OfflineModelCheckpoint.load(MODEL_A)
    model_b = OfflineModelCheckpoint.load(MODEL_B)
    return_a = OfflineModelCheckpoint.load(MODEL_A)

    assert first_a.identity["model_id"] == "OFFLINE_MODEL_A"
    assert model_b.identity["model_id"] == "OFFLINE_MODEL_B"
    assert first_a.identity["checkpoint_sha256"] != model_b.identity["checkpoint_sha256"]
    assert return_a.identity == first_a.identity


def test_b_reads_pre_swap_history_and_returning_a_reads_b_write() -> None:
    model_a = OfflineModelCheckpoint.load(MODEL_A)
    model_b = OfflineModelCheckpoint.load(MODEL_B)
    memory = [
        {"memory_id": 353, "text": "PRE_SWAP_CANARY=amber cedar river"},
    ]

    assert model_b.recall(memory, key="PRE_SWAP_CANARY") == "amber cedar river"
    assert model_b.create_write() == "silver orbit"

    memory.append({"memory_id": 354, "text": "MODEL_B_WRITE=silver orbit"})
    assert model_a.recall(memory, key="MODEL_B_WRITE") == "silver orbit"
    assert model_b.invocation_count >= 2
    assert model_a.invocation_count >= 1


def test_empty_memory_does_not_reproduce_persistent_history() -> None:
    model_a = OfflineModelCheckpoint.load(MODEL_A)
    model_b = OfflineModelCheckpoint.load(MODEL_B)
    assert model_b.recall([], key="PRE_SWAP_CANARY") == "NO_MEMORY"
    assert model_a.recall([], key="MODEL_B_WRITE") == "NO_MEMORY"


def test_archived_ibm_witnesses_become_provenance_points_not_entropy() -> None:
    points = build_archived_workload_points(WITNESSES)
    assert len(points) == 10
    assert [point["point_index"] for point in points] == list(range(1, 11))
    assert all(point["source_kind"] == "archived_ibm_hardware_witness" for point in points)
    assert all(point["provider"] == "IBM Quantum Platform" for point in points)
    assert all(point["backend"] == "ibm_fez" for point in points)
    assert all(point["shots"] == 4096 for point in points)
    assert all(point["status"] == "Completed" for point in points)
    assert points[0]["previous_point_sha256"] == "0" * 64
    assert all(points[index]["previous_point_sha256"] == points[index - 1]["point_sha256"] for index in range(1, 10))
    forbidden = {"entropy", "normalized_vector", "counts", "measurement_distribution", "authority"}
    assert not forbidden.intersection({key for point in points for key in point})


def test_corrupted_memory_fails_at_line_17_before_model_use(tmp_path: Path) -> None:
    manifest = json.loads(MEMORY_MANIFEST.read_text(encoding="utf-8"))
    parent = str(manifest["parent_gguf_sha256"])
    valid = tmp_path / "valid.jsonl"
    receipt = assemble_canonical_memory(ROOT, MEMORY_MANIFEST, valid)
    assert receipt.record_count == 352
    assert receipt.sha256 == "67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef"

    damaged = tmp_path / "damaged.jsonl"
    write_corrupted_control(valid, damaged, first_memory_id=17, second_memory_id=311)
    model = OfflineModelCheckpoint.load(MODEL_A)
    assert model.invocation_count == 0
    with pytest.raises(MemoryChainVerificationError) as caught:
        verify_memory_chain(damaged, parent_sha256=parent)
    assert caught.value.line_number == 17
    assert caught.value.expected_memory_id == 17
    assert caught.value.actual_memory_id == 311
    assert model.invocation_count == 0


def test_python_network_guard_blocks_outbound_attempts() -> None:
    guard = PythonNetworkGuard()
    with guard:
        with pytest.raises(RuntimeError, match="offline experiment forbids network access"):
            socket.create_connection(("example.com", 80), timeout=0.01)
    assert guard.active is False
    assert guard.attempt_count == 1


def test_offline_classification_is_mechanical() -> None:
    gates = {
        "MODEL_SEQUENCE": True,
        "STABLE_STORE_IDENTITIES": True,
        "CANONICAL_MEMORY_PREFIX": True,
        "MODEL_B_PRE_SWAP_ACCESS": True,
        "MODEL_A_RETURN_ACCESS": True,
        "EMPTY_MEMORY_CONTROL": True,
        "CORRUPTED_MEMORY_CONTROL": True,
        "IMMUTABLE_ROUTING_AND_SOURCE": True,
        "POINT_LEDGER_APPEND_ONLY": True,
        "OFFLINE_NO_NETWORK_ATTEMPTS": True,
    }
    assert classify_offline_gates(gates) == "VERIFIED_OFFLINE_PERSISTENT_SUBSTRATE_FUNCTIONAL_CONTINUITY"

    functional_failure = dict(gates)
    functional_failure["MODEL_B_PRE_SWAP_ACCESS"] = False
    assert classify_offline_gates(functional_failure) == "OFFLINE_SUBSTRATE_PRESERVED_FUNCTION_NOT_ESTABLISHED"

    invalid = dict(gates)
    invalid["CORRUPTED_MEMORY_CONTROL"] = False
    assert classify_offline_gates(invalid) == "INVALID_OFFLINE_SUBSTRATE_OR_CONTROL_FAILURE"


def test_offline_fixture_loader_rejects_non_object_json(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text("[]\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="expected JSON object"):
        OfflineModelCheckpoint.load(fixture)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema", "beastbox-offline-model-fixture-v0", "schema mismatch"),
        ("version", 2, "version mismatch"),
        ("model_id", "OFFLINE_MODEL_C", "unsupported offline model identity"),
        ("algorithm", "unregistered_algorithm", "unsupported offline model algorithm"),
        ("fallback", "UNKNOWN", "fallback must be NO_MEMORY"),
    ],
)
def test_offline_fixture_loader_fails_closed_on_contract_drift(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    payload = json.loads(MODEL_A.read_text(encoding="utf-8"))
    payload[field] = value
    fixture = tmp_path / f"invalid-{field}.json"
    fixture.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match=message):
        OfflineModelCheckpoint.load(fixture)


def test_offline_model_recall_rejects_empty_key_and_ignores_malformed_rows() -> None:
    model_a = OfflineModelCheckpoint.load(MODEL_A)
    memory = [
        {"text": "not-a-key-value-record"},
        {"text": "=missing-key"},
        {"text": "MISSING_VALUE="},
        {"text": "MODEL_B_WRITE=silver orbit"},
    ]

    with pytest.raises(ValueError, match="recall key must be non-empty"):
        model_a.recall(memory, key="   ")
    assert model_a.recall(memory, key="MODEL_B_WRITE") == "silver orbit"


def test_python_network_guard_rejects_reentry_and_restores_callables() -> None:
    originals = {
        "connect": socket.socket.connect,
        "connect_ex": socket.socket.connect_ex,
        "create_connection": socket.create_connection,
        "urlopen": urllib.request.urlopen,
    }
    guard = PythonNetworkGuard()

    with pytest.raises(ValueError, match="probe"):
        with guard:
            with pytest.raises(RuntimeError, match="network guard is already active"):
                guard.__enter__()
            with pytest.raises(RuntimeError, match="offline experiment forbids network access"):
                urllib.request.urlopen("https://example.com", timeout=0.01)
            raise ValueError("probe")

    assert guard.active is False
    assert guard.attempt_count == 1
    assert socket.socket.connect is originals["connect"]
    assert socket.socket.connect_ex is originals["connect_ex"]
    assert socket.create_connection is originals["create_connection"]
    assert urllib.request.urlopen is originals["urlopen"]


def test_offline_classification_rejects_missing_required_gate() -> None:
    gates = {
        name: True
        for name in (
            "MODEL_SEQUENCE",
            "STABLE_STORE_IDENTITIES",
            "CANONICAL_MEMORY_PREFIX",
            "MODEL_B_PRE_SWAP_ACCESS",
            "MODEL_A_RETURN_ACCESS",
            "EMPTY_MEMORY_CONTROL",
            "CORRUPTED_MEMORY_CONTROL",
            "IMMUTABLE_ROUTING_AND_SOURCE",
            "POINT_LEDGER_APPEND_ONLY",
            "OFFLINE_NO_NETWORK_ATTEMPTS",
        )
    }
    del gates["MODEL_SEQUENCE"]
    assert classify_offline_gates(gates) == "INVALID_OFFLINE_SUBSTRATE_OR_CONTROL_FAILURE"


def _write_witness_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _witness_rows() -> list[dict[str, object]]:
    return [json.loads(line) for line in WITNESSES.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("short", "expected 10 archived IBM hardware witnesses"),
        ("incomplete", "archived hardware witness 1 is incomplete"),
        ("duplicate_job", "job IDs must be unique"),
        ("provider", "provider mismatch"),
        ("backend", "backend mismatch"),
        ("execution", "execution metadata mismatch"),
    ],
)
def test_archived_ibm_witness_validation_fails_closed(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    rows = _witness_rows()
    if mutation == "short":
        rows.pop()
    elif mutation == "incomplete":
        rows[0].pop("result_sha256")
    elif mutation == "duplicate_job":
        rows[1]["job_id"] = rows[0]["job_id"]
    elif mutation == "provider":
        rows[0]["provider"] = "not-ibm"
    elif mutation == "backend":
        rows[0]["backend"] = "not-fez"
    elif mutation == "execution":
        rows[0]["shots"] = 1
    else:  # pragma: no cover - parametrization is the closed mutation set.
        raise AssertionError(f"unknown mutation: {mutation}")

    witness_path = tmp_path / "witnesses.jsonl"
    _write_witness_rows(witness_path, rows)
    with pytest.raises(RuntimeError, match=message):
        build_archived_workload_points(witness_path)
