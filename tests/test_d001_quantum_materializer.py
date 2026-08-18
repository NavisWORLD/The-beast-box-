import importlib.util
from pathlib import Path


def load_module():
    path = Path("scripts/materialize_d001_quantum_packets.py")
    spec = importlib.util.spec_from_file_location("d001_qmat", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hardware_record():
    return {
        "schema": "cosmos.public-quantum-record.v1",
        "record_index": 873,
        "timestamp": 1774689153.2844927,
        "provider": "IBM Quantum",
        "provider_class": "measured_quantum_hardware",
        "backend": "ibm_fez",
        "job_id": "{'job_id': 'd73pmtoi3fts73fg24lg', 'status': 'DONE'}",
        "total_shots": 4096,
        "counts": {format(i, "05b"): 128 for i in range(32)},
    }


def unknown_record():
    return {
        "schema": "cosmos.public-quantum-record.v1",
        "record_index": 1,
        "timestamp": 1772944089.1625817,
        "provider": "unknown",
        "provider_class": "legacy_unlabelled",
        "backend": None,
        "job_id": None,
        "total_shots": 4096,
        "counts": {format(i, "05b"): 128 for i in range(32)},
    }


def test_extracts_embedded_job_id_without_eval():
    mod = load_module()
    assert mod.parse_job_identifier(hardware_record()["job_id"]) == "d73pmtoi3fts73fg24lg"


def test_materializes_hardware_and_unknown_conservatively():
    mod = load_module()
    rows = mod.materialize_records([hardware_record(), unknown_record()])
    assert rows[0]["evidence"]["provider"] == "IBM Quantum"
    assert rows[0]["evidence"]["backend"] == "ibm_fez"
    assert rows[0]["evidence"]["source_class"] == "hardware"
    assert rows[0]["evidence"]["shot_count"] == 4096
    assert rows[1]["evidence"]["source_class"] == "unknown"
    assert rows[0]["packet"]["packet_sha256"] == mod.materialize_records([hardware_record()])[0]["packet"]["packet_sha256"]


def test_seeded_shuffled_control_preserves_multiset_and_changes_order():
    mod = load_module()
    rows = []
    for idx in range(6):
        record = hardware_record()
        record["record_index"] = 873 + idx
        record["job_id"] = "{'job_id': 'job-%d', 'status': 'DONE'}" % idx
        counts = {format(i, "05b"): 128 for i in range(32)}
        counts[format(idx, "05b")] += 1
        counts[format((idx + 1) % 32, "05b")] -= 1
        record["counts"] = counts
        rows.extend(mod.materialize_records([record]))
    manifest = mod.build_pairing_manifest(rows, seed=20260816, max_hardware=6)
    aligned = manifest["hardware_measurement"]
    shuffled = manifest["hardware_shuffled"]
    assert sorted(aligned) == sorted(shuffled)
    assert aligned != shuffled
    assert manifest["pairing_policy"] == "measurement-conditioned-v1"
