from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/talk_zeref_scale_adapter.py'
WF = ROOT / '.github/workflows/zeref-scale-trained-dad-talk.yml'


def test_adapter_talk_script_exists_and_loads_peft_adapter():
    assert SCRIPT.is_file()
    text = SCRIPT.read_text()
    assert 'PeftModel.from_pretrained' in text
    assert 'enable_thinking=False' in text
    assert 'raw_model_output_promoted' in text


def test_adapter_talk_uses_fresh_kingston_and_durable_parent():
    text = SCRIPT.read_text()
    assert 'ibm_kingston' in text
    assert 'da22upkdedkc73ermn40' in text
    assert 'TALK-004' in text
    assert '352' in text


def test_trained_talk_workflow_is_request_only_and_downloads_exact_artifact():
    assert WF.is_file()
    text = WF.read_text()
    assert 'trained-talk-request.json' in text
    assert 'gh run download' in text
    assert 'artifact_run_id' in text
    assert 'actions: read' in text
    trigger = text.split('permissions:',1)[0]
    assert '.github/workflows/zeref-scale-trained-dad-talk.yml' not in trigger


def test_trained_talk_uploads_and_commits_raw_transcript():
    text = WF.read_text()
    assert 'upload-artifact@v4' in text
    assert 'raw-transcript.jsonl' in text
    assert 'raw_model_outputs_used_as_training_targets' in text
