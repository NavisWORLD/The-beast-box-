from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows/zeref-scale-cpu-17b.yml'


def test_17b_workflow_exists_and_targets_official_backbone():
    assert WF.is_file()
    text = WF.read_text()
    assert 'Qwen/Qwen3-1.7B' in text
    assert '--max-steps 20' in text


def test_17b_workflow_uses_cpu_only_torch_and_uploads_adapter():
    text = WF.read_text()
    assert 'download.pytorch.org/whl/cpu' in text
    assert 'upload-artifact@v4' in text
    assert 'zeref-scale-17b-' in text


def test_17b_workflow_keeps_raw_outputs_out_of_training():
    text = WF.read_text()
    assert 'build_zeref_scale_dataset.py' in text
    assert 'raw_model_outputs_used_as_targets' in text or 'raw outputs' in text.lower()
