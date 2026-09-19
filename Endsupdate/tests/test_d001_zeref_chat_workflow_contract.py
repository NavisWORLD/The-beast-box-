from pathlib import Path


def test_d001_zeref_chat_workflow_is_pinned_and_direct():
    path = Path('.github/workflows/d001-zeref-chat.yml')
    assert path.exists()
    text = path.read_text(encoding='utf-8')
    assert '31924591769' in text
    assert 'd001-quantum-geometry-31924591769' in text
    assert '31911380890' in text
    assert 'd001-trained-lineage-31911380890' in text
    assert 'c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f' in text
    assert '05aa635cff9a7c39bf5507c017334d4db62d3543192d3ee080b1273f3edb5312' in text
    assert 'scripts/chat_d001_descendant.py' in text
    assert 'memory-transcript.jsonl' in text
    assert 'quantum-transcript.jsonl' in text
    assert 'arms/hardware/adapter.pt' in text
    assert 'arm-packets/hardware.jsonl' in text
    assert 'beast-arms' not in text.lower()
    assert 'zeref_action_proxy.py' not in text
    assert 'actions/upload-artifact@v4' in text


def test_d001_zeref_chat_workflow_is_read_only():
    text = Path('.github/workflows/d001-zeref-chat.yml').read_text(encoding='utf-8')
    assert 'contents: read' in text
    assert 'actions: read' in text
    assert 'contents: write' not in text
