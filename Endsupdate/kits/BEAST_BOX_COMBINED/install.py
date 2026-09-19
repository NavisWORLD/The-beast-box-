"""Offline, non-admin installation of the release's checksum-verified wheel."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import venv


def check_python(version=None):
    version = sys.version_info[:2] if version is None else version[:2]
    if not (3, 10) <= tuple(version) <= (3, 12):
        raise ValueError('Python 3.10–3.12 is required; install a supported Python for your user account.')


def default_install_dir():
    return Path.home() / '.beastbox' / 'venv'


def environment_python(root):
    return root / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')


@contextmanager
def verified_wheel(bundle_dir):
    """Copy and hash the exact wheel bytes pip receives, before touching the venv."""
    root = Path(bundle_dir)
    manifest = root / 'SHA256SUMS'
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 1048576:
        raise ValueError('SHA256SUMS must be a regular file smaller than 1 MiB')
    entries = {}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r'([0-9a-fA-F]{64})  (.+)', line)
        if not match or match[2] in entries:
            raise ValueError('Malformed or duplicate SHA256SUMS entry')
        entries[match[2]] = match[1].lower()
    wheels = list(root.glob('cosmos_beast_box-*.whl'))
    if len(wheels) != 1:
        raise ValueError('Expected exactly one cosmos_beast_box wheel in the release folder')
    source = wheels[0]
    if source.is_symlink() or not source.is_file() or source.name not in entries:
        raise ValueError('Wheel must be a regular file listed in SHA256SUMS')
    with tempfile.TemporaryDirectory(prefix='beastbox-checked-') as temporary:
        checked = Path(temporary) / source.name
        digest = hashlib.sha256()
        with source.open('rb') as src, checked.open('xb') as dst:
            for block in iter(lambda: src.read(1024 * 1024), b''):
                digest.update(block)
                dst.write(block)
        if digest.hexdigest() != entries[source.name]:
            raise ValueError('Wheel SHA-256 mismatch; installation stopped')
        yield checked


def install(checked, target):
    target = target.expanduser().absolute()
    data = (Path.home() / '.beastbox' / 'data').resolve()
    resolved = target.resolve()
    if resolved == data or resolved in data.parents or data in resolved.parents:
        raise ValueError('Installation environment must be separate from durable user data')
    if target.is_symlink() or (target.exists() and not (target / 'pyvenv.cfg').is_file()):
        raise ValueError('Installation directory must be new or an existing Python virtual environment')
    venv.EnvBuilder(with_pip=True, clear=False, system_site_packages=False).create(target)
    python = environment_python(target)
    subprocess.run([str(python), '-I', '-m', 'pip', '--isolated', 'install',
                    '--no-index', '--no-deps', '--disable-pip-version-check',
                    '--force-reinstall', str(checked)], check=True)
    subprocess.run([str(python), '-I', '-c', 'import beastbox.desktop'], check=True)
    return target


def main(argv=None, *, bundle_dir=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-dir', type=Path, default=default_install_dir())
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        check_python()
        with verified_wheel(bundle_dir or Path(__file__).resolve().parent) as checked:
            if args.verify_only:
                print('Release wheel checksum verified; no installation changed.')
            else:
                target = install(checked, args.install_dir)
                print(f'Installed in {target}. Run LAUNCH.bat or UnixLAUNCH.sh.')
                print(f'Durable data stays in {Path.home() / ".beastbox" / "data"}.')
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'Installation failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
