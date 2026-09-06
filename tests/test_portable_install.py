import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kits/BEAST_BOX_COMBINED/install.py'


def installer():
    assert BOOTSTRAP.is_file(), 'portable installer is missing'
    spec = importlib.util.spec_from_file_location('portable_install', BOOTSTRAP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bundle(tmp_path):
    wheel = tmp_path / 'cosmos_beast_box-0.4.0-py3-none-any.whl'
    wheel.write_bytes(b'checked bytes')
    (tmp_path / 'SHA256SUMS').write_text(hashlib.sha256(wheel.read_bytes()).hexdigest() + '  ' + wheel.name + '\n')
    return wheel


def test_verified_snapshot_keeps_original_bytes(tmp_path):
    module = installer()
    wheel = bundle(tmp_path)
    with module.verified_wheel(tmp_path) as checked:
        wheel.write_bytes(b'changed after verification')
        assert checked.read_bytes() == b'checked bytes'
    assert not checked.exists()


@pytest.mark.parametrize('mode', ['changed', 'missing', 'duplicate', 'symlink'])
def test_bad_manifest_or_wheel_fails_before_install(tmp_path, mode):
    module = installer()
    wheel = bundle(tmp_path)
    manifest = tmp_path / 'SHA256SUMS'
    if mode == 'changed':
        wheel.write_bytes(b'tampered')
    elif mode == 'missing':
        manifest.write_text('')
    elif mode == 'duplicate':
        manifest.write_text(manifest.read_text() * 2)
    else:
        original = tmp_path / 'original.whl'
        wheel.rename(original)
        wheel.symlink_to(original)
    with pytest.raises((ValueError, FileNotFoundError)):
        with module.verified_wheel(tmp_path):
            pytest.fail('accepted invalid distribution')


def test_verify_only_works_from_paths_with_spaces(tmp_path):
    module = installer()
    bundle(tmp_path)
    target = tmp_path / 'new install with spaces'
    assert module.main(['--verify-only', '--install-dir', str(target)], bundle_dir=tmp_path) == 0
    assert not target.exists()


def test_python_version_gate_is_explicit():
    module = installer()
    for version in [(3, 9), (3, 13), (2, 7)]:
        with pytest.raises(ValueError, match='3.10'):
            module.check_python(version)
    module.check_python((3, 12))


def test_invalid_wheel_does_not_create_environment(tmp_path):
    module = installer()
    bundle(tmp_path).write_bytes(b'tampered')
    target = tmp_path / 'environment'
    assert module.main(['--install-dir', str(target)], bundle_dir=tmp_path) == 1
    assert not target.exists()


def test_install_refuses_non_environment_and_data_directory(tmp_path, monkeypatch):
    module = installer()
    wheel = bundle(tmp_path)
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    for target in [tmp_path, tmp_path / '.beastbox' / 'data',
                   tmp_path / '.beastbox' / 'data' / 'venv']:
        with pytest.raises(ValueError):
            module.install(wheel, target)
