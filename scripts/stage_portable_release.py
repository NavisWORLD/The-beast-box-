#!/usr/bin/env python3
"""Fail closed on missing platform receipts, then stage platform downloads."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def archive(directory: Path, output: Path, executable: bool = False) -> None:
    files = sorted(p for p in directory.rglob('*') if p.is_file())
    require(bool(files), f'empty artifact: {directory.name}')
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            require(not path.is_symlink(), 'artifact symlink is not supported')
            info = zipfile.ZipInfo(path.relative_to(directory).as_posix())
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if executable and path.parent == directory and path.suffix == '' else 0o644
            info.external_attr = (0o100000 | mode) << 16
            bundle.writestr(info, path.read_bytes())


def stage(assets: Path, output: Path, source: str) -> None:
    results = {}
    for platform in ('ubuntu-24.04', 'windows-latest'):
        directory = assets / f'beast-desktop-{platform}-0.5.0'
        first, restart, installed = [read(directory / f'{name}.json') for name in ('first', 'restart', 'installer')]
        require(all(r.get('valid') is True for r in (first, restart, installed)), 'desktop integrity failure')
        require(first['system_id'] == restart['system_id'] and first['turn_after'] == restart['turn_before'], 'desktop restart failure')
        require(all(read(directory / f'{lang}.json').get('ok') is True for lang in ('cpp', 'rust')), 'native client failed')
        suffix = '.exe' if platform == 'windows-latest' else ''
        for name in ('BeastBox', 'beast-client-cpp', 'beast-client-rust'):
            require((directory / (name + suffix)).stat().st_size > 0, 'missing executable')
        archive(directory, output / f'beast-desktop-{platform}-0.5.0.zip', executable=True)
        results[platform] = 'PASS: executable, restart, native clients, checked installer'
    android = assets / 'beast-android-0.5.0'
    receipt = read(android / 'dist/android-build-receipt.json')
    require(receipt.get('source_commit') == source and receipt.get('acceptance') == 'passed', 'Android source or acceptance mismatch')
    apk = android / 'dist' / receipt['apk']['filename']
    require(hashlib.sha256(apk.read_bytes()).hexdigest() == receipt['apk']['sha256'], 'Android APK hash mismatch')
    shutil.copy2(apk, output / apk.name)
    archive(android, output / 'ANDROID_EVIDENCE.zip')
    results['android'] = 'PASS: API 35 x86_64 emulator, embedded runtime A/B/A and restart; debug signing'
    ios = assets / 'beast-ios-evidence-0.5.0'
    receipt = read(ios / 'acceptance.json')
    require(receipt.get('passed') is True and receipt.get('process_launches') == 3 and receipt.get('models') == ['A', 'B', 'A'], 'iOS acceptance mismatch')
    for flavor in ('simulator', 'unsigned-device'):
        matches = list((assets / f'beast-ios-{flavor}-0.5.0').glob('*.zip'))
        require(len(matches) == 1, 'missing or ambiguous iOS build')
        shutil.copy2(matches[0], output / matches[0].name)
    archive(ios, output / 'IOS_EVIDENCE.zip')
    results['ios'] = 'PASS: simulator A/B/A and restart, unsigned device archive; signing NOT VERIFIED'
    (output / 'PORTABLE_VERIFICATION.json').write_text(json.dumps({
        'schema': 'beastbox-portable-verification-v1', 'source_commit': source,
        'source_binding': 'All platform artifacts are required predecessor jobs of this exact-source release workflow',
        'platforms': results, 'production_ready': False,
        'limitations': ['Mobile fixture providers are deterministic test components, not trained models',
                        'iOS signing and physical device validation remain external gates',
                        'Android uses debug signing; no Play production distribution',
                        'IBM and Azure live jobs require owner credentials and have not been run here',
                        'Audio/light paths accept bounded supplied inputs; no physical sensor certification',
                        'Retained memory depends on storage, retention and backups'],
    }, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-sha', required=True)
    args = parser.parse_args()
    stage(args.assets, args.output, args.source_sha)
