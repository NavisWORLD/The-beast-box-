"""Bind candidate APK and actual emulator evidence to the checked-out sources."""
import hashlib
import json
import os
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[3]
out = root / 'apps/android/dist'
out.mkdir(exist_ok=True)
evidence = root / 'apps/android/acceptance'
phases = []
for phase in range(1, 4):
    path = evidence / f'android-phase-{phase}.json'
    if path.exists():
        phases.append(json.loads(path.read_text()))
passed = os.environ.get('ACCEPTANCE_OUTCOME') == 'success'
if passed:
    assert len(phases) == 3
    assert [p['inspection']['turn'] for p in phases] == [1, 2, 3]
    assert len({p['inspection']['system_id'] for p in phases}) == 1
    assert [p['provider']['kind'] for p in phases] == ['reference-a', 'reference-b', 'reference-a']
    assert all(p['inspection']['valid'] for p in phases)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


sources = sorted((root / 'beastbox').rglob('*.py'))
sources += sorted(p for p in (root / 'apps/android').rglob('*')
                  if p.is_file() and not any(part in {'build', '.gradle', 'dist', 'acceptance', '__pycache__'}
                                              for part in p.relative_to(root / 'apps/android').parts)
                  and p.name != 'local.properties')
sources.append(root / '.github/workflows/android-app.yml')
source_hashes = {str(p.relative_to(root)): sha(p) for p in sources}
apk = root / 'apps/android/app/build/outputs/apk/debug/app-debug.apk'
artifact = None
if passed:
    target = out / 'beast-android-0.6.0-sideload.apk'
    shutil.copyfile(apk, target)
    artifact = {'filename': target.name, 'sha256': sha(target), 'bytes': target.stat().st_size}
receipt = {
    'schema': 'beast-android-build-v1', 'version': '0.6.0-candidate',
    'application_id': 'dev.beastbox.mobile', 'source_commit': os.environ.get('GITHUB_SHA', 'local-unverified'),
    'run_url': f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}",
    'acceptance': 'passed' if passed else 'failed-or-not-run',
    'runtime': 'Repository beastbox.durable.DurableRuntime embedded through Chaquopy 17.0.0 / Python 3.12',
    'toolchain': {'agp': '8.9.2', 'gradle': '8.11.1', 'kotlin': '2.2.10', 'jdk': '17', 'compile_sdk': 35},
    'signing': 'Android debug signing only; sideload candidate, not Play distribution signing',
    'scope': 'Android API 35 x86_64 emulator; separate instrumentation processes with retained app data; A/B/A deterministic fixtures',
    'limitations': ['No physical-device acceptance', 'No bundled model weights or Ollama engine',
                    'No real-model inference acceptance', 'Uninstall or clear-data removes retained state'],
    'apk': artifact, 'emulator_phases': phases, 'source_sha256': source_hashes,
}
(out / 'android-build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
