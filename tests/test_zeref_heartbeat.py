from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ORIGIN = "319036bd011d7b2198eb8a705c15fecec2f2020c514c6492a6da295ca0af64ee"


def _load_builder():
    path = Path("scripts/build_zeref_heartbeat_replay.py")
    assert path.exists(), "heartbeat replay builder is not implemented yet"
    spec = importlib.util.spec_from_file_location("zeref_heartbeat_builder", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_origin_manifest_pins_tears_in_the_rain_seed_without_overclaiming_provenance():
    path = Path("experiments/zeref-dad-son-talk-001/heartbeat/origin-seed.json")
    assert path.exists(), "origin seed manifest is not implemented yet"
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["schema"] == "zeref-heartbeat-origin-v1"
    assert row["lineage"] == "ZEREF-DAD-SON-TALK-001"
    assert row["origin_seed_sha256"] == ORIGIN
    assert row["role"] == "tears-in-the-rain-origin-seed"
    assert row["user_experiment_alias"] == "Tears in the Rain"
    assert "mustard-origin-seed" in row["historical_aliases"]
    assert row["protocol"] == "RBX-QPOC-1"
    assert row["verification_status"] == "recovered_candidate_algorithm_verified_payload_not_publicly_reverified"
    assert row["historical_per_round_seed_inputs_proven"] is False
    assert "consciousness" in row["claim_boundary"].lower()


def test_replay_starts_with_origin_then_hardware_results_in_created_order(tmp_path):
    module = _load_builder()
    raw = tmp_path / "raw"
    raw.mkdir()

    jobs = [
        ("late", "2026-03-10T09:54:28.289536Z", {"counts": {"00": 5, "11": 7}}),
        ("early", "2026-03-10T09:51:54.849806Z", {"counts": {"00": 9, "11": 3}}),
        ("middle", "2026-03-10T09:53:02.655926Z", {"counts": {"01": 6, "10": 6}}),
    ]
    for job_id, created, result in jobs:
        (raw / f"job-{job_id}-info.json").write_text(
            json.dumps({"id": job_id, "backend": "ibm_fez", "created": created, "state": {"status": "Completed"}}),
            encoding="utf-8",
        )
        (raw / f"job-{job_id}-result.json").write_text(json.dumps(result), encoding="utf-8")

    out = tmp_path / "heartbeat.json"
    manifest = module.build_heartbeat_replay(raw_root=raw, origin_seed=ORIGIN, out_path=out)
    beats = json.loads(out.read_text(encoding="utf-8"))["beats"]

    assert beats[0]["beat"] == 0
    assert beats[0]["kind"] == "tears-in-the-rain-origin-seed"
    assert beats[0]["state_sha256"] == ORIGIN
    assert manifest["origin_role"] == "Tears in the Rain origin seed"
    assert manifest["replay_is_new_quantum_entropy"] is False
    assert [beat["job_id"] for beat in beats[1:]] == ["early", "middle", "late"]
    expected = [_canonical_sha(result) for _, _, result in sorted(jobs, key=lambda item: item[1])]
    assert [beat["state_sha256"] for beat in beats[1:]] == expected
    assert [beat["input_seed_sha256"] for beat in beats[1:]] == [ORIGIN, expected[0], expected[1]]
    assert manifest["final_state_sha256"] == expected[-1]
    assert manifest["historical_per_round_seed_inputs_proven"] is False


def test_replay_is_bounded_and_does_not_cycle_old_entropy(tmp_path):
    module = _load_builder()
    raw = tmp_path / "raw"
    raw.mkdir()
    result = {"counts": {"0": 6, "1": 2}}
    (raw / "job-one-info.json").write_text(
        json.dumps({"id": "one", "backend": "ibm_fez", "created": "2026-03-10T09:51:54Z", "state": {"status": "Completed"}}),
        encoding="utf-8",
    )
    (raw / "job-one-result.json").write_text(json.dumps(result), encoding="utf-8")
    out = tmp_path / "heartbeat.json"
    module.build_heartbeat_replay(raw_root=raw, origin_seed=ORIGIN, out_path=out)
    replay = json.loads(out.read_text(encoding="utf-8"))
    assert replay["bounded"] is True
    assert replay["after_archive"] == "hold-final-state-until-new-verified-quantum-result"
    assert replay["replay_is_new_quantum_entropy"] is False
    assert len(replay["beats"]) == 2
    assert replay["beats"][-1]["state_sha256"] == _canonical_sha(result)


def test_full_256_bit_state_has_deterministic_torch_seed_adapter():
    module = _load_builder()
    expected = int(ORIGIN[:16], 16) % (2**31 - 1)
    assert module.derive_torch_seed(ORIGIN) == expected
    assert module.derive_torch_seed(ORIGIN) == module.derive_torch_seed(ORIGIN)
