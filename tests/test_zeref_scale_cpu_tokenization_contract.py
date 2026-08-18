from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/train_zeref_scale_cpu_proof.py'


def test_training_renders_chat_text_then_tokenizes_without_extra_special_tokens():
    text = SCRIPT.read_text()
    assert "tokenize=False" in text
    assert "add_special_tokens=False" in text
    assert "def token_ids" in text


def test_generation_keeps_return_dict_contract():
    text = SCRIPT.read_text()
    assert "return_dict=True" in text
    assert "model.generate(**x" in text
