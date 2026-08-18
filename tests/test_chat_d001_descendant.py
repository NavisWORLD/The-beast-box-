import importlib.util
from pathlib import Path

import pytest


def load_chat():
    path = Path('scripts/chat_d001_descendant.py')
    spec = importlib.util.spec_from_file_location('chat_d001_descendant', path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_prompts_are_frozen_and_short_for_native_block():
    mod = load_chat()
    assert mod.CHAT_PROMPTS == (
        'Luna: Hi Zeref. Cory says hi.\nZeref:',
        'Luna: What should Cory know?\nZeref:',
    )
    assert all(len(prompt) < 96 for prompt in mod.CHAT_PROMPTS)


def test_chat_declares_no_sensors():
    mod = load_chat()
    assert mod.SENSOR_AVAILABILITY == {'camera': False, 'microphone': False}


def test_decoding_modes_include_reproducible_sampling():
    mod = load_chat()
    assert mod.DECODING_MODES == ('greedy-argmax', 'sampled-top-k')


def test_validate_sampling_config_accepts_frozen_probe():
    mod = load_chat()
    assert mod.validate_sampling_config(temperature=0.8, top_k=20) == (0.8, 20)


@pytest.mark.parametrize(
    ('temperature', 'top_k'),
    [(0.0, 20), (-1.0, 20), (0.8, 0), (0.8, -3)],
)
def test_validate_sampling_config_rejects_invalid_values(temperature, top_k):
    mod = load_chat()
    with pytest.raises(ValueError):
        mod.validate_sampling_config(temperature=temperature, top_k=top_k)
