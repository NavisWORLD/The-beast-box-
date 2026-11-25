"""Contract for the in-browser brain exporter (Cory, 2026-11-20: Zeref talks on GitHub Pages).

Static checks only (CI has no onnx/onnxruntime): the exporter reads the public pin, verifies the
checkpoint sha through the Engine, re-proves greedy parity, ships chunks under 50 MB, records
provenance, and never writes the pin, gates, senses or private state.
"""
import json
from pathlib import Path

SRC = Path("scripts/zeref_onnx_export.py").read_text(encoding="utf-8")
MANIFEST = json.loads(Path("evidence/zeref-browser-brain-001/manifest.json").read_text(encoding="utf-8"))


def test_exporter_reads_pin_and_verifies_checkpoint():
    assert "apps/beastbox-cloud/lib/rawrphos-public-pin.json" in SRC
    assert 'expected_sha256=pin["checkpoint_sha256"]' in SRC
    assert ".write_text" not in SRC.split("rawrphos-public-pin.json")[0][-200:]
    for banned in ("zeref_promote_pin", "state12", "identity.json", "BEASTBOX_GITHUB_DISPATCH_TOKEN"):
        assert banned not in SRC


def test_exporter_proves_parity_and_chunks_under_github_limits():
    assert "CHUNK = 45 * 1024 * 1024" in SRC
    assert "return 0 if ok == len(GREEDY_CASES) else 1" in SRC
    assert "REPETITION_PENALTY" in SRC and "NO_REPEAT_NGRAM" in SRC


def test_recorded_manifest_provenance():
    p = MANIFEST["provenance"]
    assert p["training_steps"] == 47024
    assert p["checkpoint_sha256"].startswith("6f5a8b4f0f41")
    assert p["release_tag"] == "zeref-006-cycle-90-6f5a8b4f0f41"
    assert MANIFEST["parity"]["onnxruntime_python_vs_torch_greedy"] == "9/9"
    assert all(c["bytes"] < 50_000_000 for c in MANIFEST["onnx"]["chunks"])
    assert sum(c["bytes"] for c in MANIFEST["onnx"]["chunks"]) == MANIFEST["onnx"]["bytes"]
    assert MANIFEST["decoding"]["repetition_penalty"] == 1.15 and MANIFEST["decoding"]["no_repeat_ngram"] == 3
    assert MANIFEST["senses"].startswith("none")
