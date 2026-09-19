from pathlib import Path


def test_sampled_chat_workflow_is_pinned_and_reproducible():
    path = Path('.github/workflows/d001-zeref-sampled-chat.yml')
    assert path.exists()
    text = path.read_text(encoding='utf-8')
    assert '31924591769' in text
    assert 'd001-quantum-geometry-31924591769' in text
    assert '31911380890' in text
    assert 'd001-trained-lineage-31911380890' in text
    assert 'c650d1051e8a8bc83eb99b41179ecc909f19ac011a8802396f8993227fb1bc8f' in text
    assert '05aa635cff9a7c39bf5507c017334d4db62d3543192d3ee080b1273f3edb5312' in text
    assert '--decoding sampled-top-k' in text
    assert '--temperature "$TEMPERATURE"' in text
    assert '--top-k "$TOP_K"' in text
    assert '--tokens "$TOKENS"' in text
    assert 'TEMPERATURE: "0.8"' in text
    assert 'TOP_K: "20"' in text
    assert 'TOKENS: "70"' in text
    assert 'memory-sampled.jsonl' in text
    assert 'quantum-sampled.jsonl' in text
    assert 'arms/hardware/adapter.pt' in text
    assert 'arm-packets/hardware.jsonl' in text
    assert 'zeref_action_proxy.py' not in text
    assert 'beast-arms' not in text.lower()
    assert 'actions/upload-artifact@v4' in text


def test_sampled_chat_workflow_is_read_only():
    text = Path('.github/workflows/d001-zeref-sampled-chat.yml').read_text(encoding='utf-8')
    assert 'contents: read' in text
    assert 'actions: read' in text
    assert 'contents: write' not in text
