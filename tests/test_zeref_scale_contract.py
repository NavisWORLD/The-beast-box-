from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scale_files_exist():
    for rel in [
        "scripts/build_zeref_scale_dataset.py",
        "scripts/train_zeref_scale_lora.py",
        "scripts/talk_zeref_scale.py",
        ".github/workflows/zeref-scale-fresh-ibm.yml",
    ]:
        assert (ROOT / rel).is_file(), rel


def test_training_never_calls_ibm_knowledge():
    text = (ROOT / "scripts/train_zeref_scale_lora.py").read_text()
    assert 'IBM_STATE_ROLE = "session_provenance_not_semantic_knowledge"' in text
    assert "raw_model_output_promoted" in text
    assert "all-linear" in text


def test_talk_wire_preserves_boundaries():
    text = (ROOT / "scripts/talk_zeref_scale.py").read_text()
    assert "not literally Caleb" in text
    assert "352" in text
    assert "TALK-004" in text
    assert "raw_output_first" in text


def test_workflow_is_fresh_hardware_and_secret_safe():
    text = (ROOT / ".github/workflows/zeref-scale-fresh-ibm.yml").read_text()
    assert "--fresh" in text
    assert "secrets.IBM_QUANTUM_TOKEN" in text
    assert "upload-artifact@v4" in text
    assert "echo $IBM_QUANTUM_TOKEN" not in text
