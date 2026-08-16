import importlib.util
from pathlib import Path

SCRIPT = Path('scripts/zeref_memory_discontinuity.py')


def _load():
    spec = importlib.util.spec_from_file_location('zeref_memory_discontinuity', SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_frozen_replay_fragment_preserves_trailing_ascii_space(tmp_path: Path) -> None:
    mod = _load()
    fragment = tmp_path / 'fragment.txt'
    fragment.write_bytes(b'Right no ')

    loaded = mod.load_replay_fragment(fragment)

    assert loaded == 'Right no '
    assert loaded.encode('utf-8') == b'Right no '


def test_explicit_replay_fragment_is_not_recompacted() -> None:
    mod = _load()
    assert mod.replay_fragment_for_wire('Right no ') == 'Right no '
