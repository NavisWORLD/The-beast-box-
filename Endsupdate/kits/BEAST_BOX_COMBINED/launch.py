"""Launch the installed desktop without depending on the current directory."""
import argparse
from pathlib import Path
import subprocess
import sys
from install import default_install_dir, environment_python


def main(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--install-dir', type=Path, default=default_install_dir())
    args, desktop_args = parser.parse_known_args(argv)
    python = environment_python(args.install_dir.expanduser().absolute())
    if not python.is_file():
        print('Beast Box is not installed. Run INSTALL.bat or UnixINSTALL.sh first.', file=sys.stderr)
        return 1
    return subprocess.call([str(python), '-I', '-m', 'beastbox.desktop', *desktop_args])


if __name__ == '__main__':
    raise SystemExit(main())
