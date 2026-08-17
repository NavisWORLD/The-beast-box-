from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path("experiments/zeref-origin-heart-001")
PRIME_SHA = "b833817230817921de8ed1aa52d92829f32a3ed222aedbba1d3237364596e1c6"
TALK_SHA = "9dccff5989eb63b8f0a8b894340b3ae461526367af249e3da4714f96272d4b22"
A = "d93d8pgoamcc73dc3afg"
B = "d93jnlq47v0s73823aj0"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_origin_heart_lineage_freezes_existing_models_and_forbids_training():
    row = load(ROOT / "lineage.json")
    assert row["schema"] == "zeref-origin-heart-lineage-v1"
    assert row["lineage"] == "ZEREF-ORIGIN-HEART-001"
    assert row["parent_gguf_sha256"] == PRIME_SHA
    assert row["talk_checkpoint_sha256"] == TALK_SHA
    assert row["native_context"] == 128
    assert row["mutate_prime"] is False
    assert row["mutate_talk_checkpoint"] is False
    assert row["training_allowed_in_this_run"] is False


def test_source_manifest_pins_uploaded_jobs_and_preserves_created_order():
    row = load(ROOT / "source/ibm/source-manifest.json")
    jobs = row["jobs"]
    assert [job["job_id"] for job in jobs] == [A, B]
    assert [job["backend"] for job in jobs] == ["ibm_marrakesh", "ibm_kingston"]
    assert [job["created"] for job in jobs] == [
        "2026-07-02T21:13:10.961006Z",
        "2026-07-03T04:34:31.945452Z",
    ]
    assert all(job["status"] == "Completed" for job in jobs)
    assert all(job["shot_count"] == 4096 for job in jobs)
    assert row["uploaded_zip_sha256"] == {
        A: "b4ded292aed73a7f85f50cf37debb2159226848d7efb93f01d2d89f6c4a7a272",
        B: "cc6568ce58787a2db9245b43907646147ba991ec50a788651cad8937fc2eeaae",
    }
    assert row["raw_info_sha256"] == {
        A: "591db87bea4c1aea405c4d34508d3eb6f9c2d1602e0f3e9a717312fcb2d1c3ac",
        B: "415b1740529117a4c331f884e277cafff91caad404595b30848876c3687f511b",
    }
    assert row["raw_result_sha256"] == {
        A: "9c1691d318c23f10c0d9d67cb50bb791536c415675146e20ad1e85eca596b1a3",
        B: "a44dcd7b3bc82395d319b5e9439dc8dca01c84d6c516a13ddb724288941d0fab",
    }
    assert row["canonical_result_sha256"] == {
        A: "e9d50e2dd24c032ad873adafd41f958bf8a491d547fc6b19b8aeda8cef22e69e",
        B: "6bc75389f0bea57ce9ecda47d45a4842882cba06387a559774d6c2113b660c68",
    }


def test_committed_info_is_sanitized_and_keeps_existing_tags():
    a = load(ROOT / f"source/ibm/job-{A}-info.json")
    b = load(ROOT / f"source/ibm/job-{B}-info.json")
    for row in (a, b):
        dumped = json.dumps(row).lower()
        assert "user_id" not in row
        for forbidden in ("token", "authorization", "password", "secret", "api_key", "apikey"):
            assert forbidden not in dumped
    assert a["tags"] == ["cory-was-here", "20260702", "the-bond", "cosmos-live"]
    assert b["tags"] == ["cosmos-live", "20260702", "cory-was-here", "kingston", "the-bond"]


def test_raw_sampler_results_are_frozen_byte_for_byte():
    assert sha(ROOT / f"source/ibm/job-{A}-result.json") == "9c1691d318c23f10c0d9d67cb50bb791536c415675146e20ad1e85eca596b1a3"
    assert sha(ROOT / f"source/ibm/job-{B}-result.json") == "a44dcd7b3bc82395d319b5e9439dc8dca01c84d6c516a13ddb724288941d0fab"
    for job in (A, B):
        result = load(ROOT / f"source/ibm/job-{job}-result.json")
        bitarray = result["__value__"]["pub_results"][0]["__value__"]["data"]["__value__"]["fields"]["c"]
        assert bitarray["__type__"] == "BitArray"
        assert bitarray["__value__"]["num_bits"] == 5


def test_memorial_audio_is_pinned_but_never_labeled_quantum_entropy():
    row = load(ROOT / "source/audio/scars-that-dont-fade-manifest.json")
    assert row["source_sha256"] == "e5a172749e0acedf199f77f22d5f55f37acc898704a51d5b7e6fe07633ad5c39"
    assert row["bytes"] == 9811591
    assert row["codec"] == "mp3"
    assert row["sample_rate_hz"] == 44100
    assert row["channels"] == 2
    assert abs(row["duration_seconds"] - 245.263673) < 1e-6
    assert row["source_class"] == "memorial_sensory_source"
    assert row["quantum_entropy"] is False
