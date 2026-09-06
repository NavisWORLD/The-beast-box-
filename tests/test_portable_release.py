import hashlib
import json

import pytest

from scripts.stage_portable_release import stage


def write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


@pytest.fixture
def artifacts(tmp_path):
    assets, output = tmp_path / 'assets', tmp_path / 'output'
    output.mkdir()
    for platform in ('ubuntu-24.04', 'windows-latest'):
        d = assets / f'beast-desktop-{platform}-0.5.0'
        for name, before, after in [('first', 0, 1), ('restart', 1, 2), ('installer', 0, 1)]:
            write(d / f'{name}.json', dict(valid=True, system_id='test', turn_before=before, turn_after=after))
        for lang in ('cpp', 'rust'):
            write(d / f'{lang}.json', {'ok': True})
        for name in ('BeastBox', 'beast-client-cpp', 'beast-client-rust'):
            (d / (name + ('.exe' if platform == 'windows-latest' else ''))).write_bytes(b'test fixture')
    d = assets / 'beast-android-0.5.0/dist'
    write(d / 'android-build-receipt.json', dict(source_commit='test-source', acceptance='passed', apk=dict(filename='test.apk', sha256=hashlib.sha256(b'test fixture').hexdigest())))
    (d / 'test.apk').write_bytes(b'test fixture')
    write(assets / 'beast-ios-evidence-0.5.0/acceptance.json', dict(passed=True, process_launches=3, models=['A', 'B', 'A']))
    for flavor in ('simulator', 'unsigned-device'):
        p = assets / f'beast-ios-{flavor}-0.5.0' / f'{flavor}.zip'
        p.parent.mkdir(parents=True)
        p.write_bytes(b'test fixture')
    return assets, output


def test_stages_fixtures_without_claiming_production(artifacts):
    assets, output = artifacts
    stage(assets, output, 'test-source')
    assert json.loads((output / 'PORTABLE_VERIFICATION.json').read_text())['production_ready'] is False


@pytest.mark.parametrize('failure', ['source', 'apk', 'restart', 'missing'])
def test_refuses_broken_platform_chain(artifacts, failure):
    assets, output = artifacts
    if failure == 'apk':
        (assets / 'beast-android-0.5.0/dist/test.apk').write_bytes(b'corrupt')
    elif failure == 'restart':
        write(assets / 'beast-desktop-ubuntu-24.04-0.5.0/restart.json', dict(valid=True, system_id='different', turn_before=1))
    elif failure == 'missing':
        (assets / 'beast-ios-evidence-0.5.0/acceptance.json').unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        stage(assets, output, 'wrong' if failure == 'source' else 'test-source')
