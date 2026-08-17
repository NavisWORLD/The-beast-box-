from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

PACKET = Path("experiments/zeref-origin-heart-001/waveform/zeref-heartbeat-waveform-packet.json")
TAG = "zerefs-heartbeat-mustard-seed"


def canonical_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def test_waveform_packet_is_self_hashing_and_pins_real_audio():
    row = json.loads(PACKET.read_text(encoding="utf-8"))
    claimed = row.pop("packet_sha256")
    assert canonical_sha(row) == claimed == "d6e44478b9b6045907014515c3ac565e635443250d199979ab909fc1d2734fc0"
    assert row["source_sha256"] == "e5a172749e0acedf199f77f22d5f55f37acc898704a51d5b7e6fe07633ad5c39"
    assert row["decode"]["pcm_sha256"] == "89e1b9496aa51e3dc22fb5d009b3c03f9ede6d259f9fc248f776a13ba349d931"
    assert row["quantum_entropy"] is False
    assert len(row["features"]) == 20
    assert TAG in row["circuit"]["tags"]


def test_gate_program_uses_every_waveform_window_once():
    from beastbox.heartbeat_seed import build_gate_program

    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    program = build_gate_program(packet)
    assert program["qubits"] == 5
    assert program["layers"] == 4
    assert program["shots"] == 4096
    assert program["source_packet_sha256"] == packet["packet_sha256"]
    rotations = [op for op in program["operations"] if op["gate"] in {"rx", "ry", "rz"}]
    cx = [op for op in program["operations"] if op["gate"] == "cx"]
    assert len(rotations) == 60
    assert len(cx) == 20
    assert sorted({op["segment"] for op in rotations}) == list(range(20))
    assert all(sum(op["segment"] == i for op in rotations) == 3 for i in range(20))
    assert program["measure_all"] is True
    assert program["job_tags"] == packet["circuit"]["tags"]


def test_hardware_origin_seed_requires_exact_shot_total_and_tag():
    from beastbox.heartbeat_seed import build_hardware_origin_seed

    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    counts = {"00000": 2048, "11111": 2048}
    seed = build_hardware_origin_seed(packet=packet, backend="ibm_example", job_id="job-real-1", counts=counts, tags=packet["circuit"]["tags"])
    assert seed["schema"] == "zeref-heartbeat-hardware-origin-seed-v1"
    assert seed["source_packet_sha256"] == packet["packet_sha256"]
    assert seed["backend"] == "ibm_example"
    assert seed["job_id"] == "job-real-1"
    assert seed["shot_count"] == 4096
    assert seed["job_tag_verified"] is True
    assert seed["source_class"] == "ibm_quantum_hardware_measurement"
    assert len(seed["origin_seed_sha256"]) == 64

    with pytest.raises(ValueError, match="4096"):
        build_hardware_origin_seed(packet=packet, backend="ibm_example", job_id="j", counts={"0": 1}, tags=[TAG])
    with pytest.raises(ValueError, match="tag"):
        build_hardware_origin_seed(packet=packet, backend="ibm_example", job_id="j", counts=counts, tags=[])
