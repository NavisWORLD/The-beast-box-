import importlib.util
from pathlib import Path


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
