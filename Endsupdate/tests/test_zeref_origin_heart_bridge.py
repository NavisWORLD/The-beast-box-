from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path("experiments/zeref-origin-heart-001")
A = "d93d8pgoamcc73dc3afg"
B = "d93jnlq47v0s73823aj0"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def raw_source_bytes(job: str) -> bytes:
    manifest = load(ROOT / "source/ibm/source-manifest.json")
    data = (ROOT / f"source/ibm/job-{job}-result.json").read_bytes()
    mode = manifest["transport_normalization"][job]
    if mode == "none":
        return data
    if mode == "strip_exactly_one_final_lf_before_raw_sha_verification":
        assert data.endswith(b"\n") and not data.endswith(b"\n\n")
        return data[:-1]
    raise AssertionError(mode)


def origin_module():
    path = Path("beastbox/origin_heart.py")
    assert path.exists(), "CST Origin Heart bridge is not implemented yet"
    spec = importlib.util.spec_from_file_location("beastbox_origin_heart", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def jobs_from_manifest() -> list[dict]:
    manifest = load(ROOT / "source/ibm/source-manifest.json")
    jobs = []
    for row in manifest["jobs"]:
        job = row["job_id"]
        jobs.append({
            **row,
            "result_path": str(ROOT / f"source/ibm/job-{job}-result.json"),
            "raw_result_sha256": manifest["raw_result_sha256"][job],
            "committed_result_sha256": manifest["committed_result_sha256"][job],
            "canonical_result_sha256": manifest["canonical_result_sha256"][job],
            "transport_normalization": manifest["transport_normalization"][job],
        })
    return jobs


def test_real_sampler_bitarrays_decode_to_exact_4096_shot_histograms():
    module = origin_module()
    expected = {
        A: "af772704525a0545c9ae3b06abee19d86834280ec658d84ad96b07e8b0323c42",
        B: "4758d55b1e4cd16f47ed8202661f6ee17286bb01c71fd6f6d53c643d5fd9e6b0",
    }
    for job in (A, B):
        result = json.loads(raw_source_bytes(job).decode("utf-8"))
        counts, shots, width = module.decode_sampler_bitarray(result)
        assert shots == 4096
        assert width == 5
        assert sum(counts.values()) == 4096
        assert all(len(bits) == 5 and set(bits) <= {"0", "1"} for bits in counts)
        payload = json.dumps(dict(sorted(counts.items())), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        assert hashlib.sha256(payload).hexdigest() == expected[job]


def test_origin_heart_runs_existing_quantum_bridge_state_family_cns_and_capsule(tmp_path):
    module = origin_module()
    jobs = jobs_from_manifest()
    first = module.build_origin_heart(jobs, out_dir=tmp_path / "one")
    second = module.build_origin_heart(list(reversed(jobs)), out_dir=tmp_path / "two")
    assert first["schema"] == "zeref-origin-heart-v1"
    assert first["lineage"] == "ZEREF-ORIGIN-HEART-001"
    assert first["source_order"] == [A, B]
    assert first["hardware_rounds"] == 2
    assert first["observed_shots_total"] == 8192
    assert first["origin_heart_sha256"] == second["origin_heart_sha256"]
    assert first["runtime_seed"] == module.derive_runtime_seed(first["origin_heart_sha256"])
    assert len(first["feature_packet_sha256s"]) == 2
    assert len(first["bridge_packet_sha256s"]) == 2
    assert first["state_family_step"] == 2
    assert all(v["live"] for v in first["state_family_preflight"].values())
    assert first["state_capsule"]["schema"] == "beastbox.capsule.v1"
    assert len(first["state_capsule"]["integrity"]) == 64
    assert (tmp_path / "one/origin-heart.json").is_file()
    assert (tmp_path / "one/bridge-trace.jsonl").is_file()
    assert (tmp_path / "one/SHA256SUMS").is_file()
