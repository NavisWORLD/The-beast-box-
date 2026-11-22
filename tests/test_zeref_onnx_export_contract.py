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
    assert p["training_steps"] == 44144
    assert p["checkpoint_sha256"].startswith("679ae933535d")
    assert p["release_tag"] == "zeref-006-cycle-81-679ae933535d"
    assert MANIFEST["parity"]["onnxruntime_python_vs_torch_greedy"] == "9/9"
    assert all(c["bytes"] < 50_000_000 for c in MANIFEST["onnx"]["chunks"])
    assert sum(c["bytes"] for c in MANIFEST["onnx"]["chunks"]) == MANIFEST["onnx"]["bytes"]
    assert MANIFEST["decoding"]["repetition_penalty"] == 1.15 and MANIFEST["decoding"]["no_repeat_ngram"] == 3
    assert MANIFEST["senses"].startswith("none")


def _build_names():
    """Exec only build_names() from the exporter source (CI has no torch/onnx)."""
    import ast
    tree = ast.parse(SRC)
    ns = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "DTYPES" for t in node.targets):
            exec(compile(ast.Module([node], []), "dtypes", "exec"), ns)
        if isinstance(node, ast.FunctionDef) and node.name == "build_names":
            exec(compile(ast.Module([node], []), "build_names", "exec"), ns)
    return ns["build_names"]


def test_fp16_is_opt_in_and_fp32_names_unchanged():
    names = _build_names()
    assert names("fp32") == {"onnx": "zeref-step.onnx", "manifest": "manifest.json", "parity": "parity-reference.json"}
    fp16 = names("fp16")
    assert fp16["onnx"] == "zeref-step.fp16.onnx" and fp16["manifest"] == "manifest.fp16.json"
    assert fp16["parity"] == "parity-reference.fp16.json"
    assert not set(fp16.values()) & set(names("fp32").values())  # fp16 never overwrites the shipped fp32 files
    try:
        names("int8")
    except ValueError:
        pass
    else:
        raise AssertionError("int8 must not be accepted (it changed his words: 3/9 parity)")
    assert 'choices=DTYPES, default="fp32"' in SRC


def test_fp16_parity_is_reproved_on_the_converted_graph():
    i_conv = SRC.index('onnx.save(to_fp16(onnx.load(str(onnx_path))), str(onnx_path))')
    i_sess = SRC.index('ort.InferenceSession(str(onnx_path)')
    assert i_conv < i_sess  # the session that proves parity loads the fp16 graph
    assert "keep_io_types=True" in SRC  # page feeds the same float32 tensors
    assert '"default": False' in SRC and "fp16 build:" in SRC  # labelled, never the default
