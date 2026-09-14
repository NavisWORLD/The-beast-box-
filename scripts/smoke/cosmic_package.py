"""Build artifact integrity and clean-wheel resource loading checks."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import venv
import zipfile


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    wheels = list((root / "dist").glob("*.whl"))
    sources = list((root / "dist").glob("*.tar.gz"))
    assert len(wheels) == len(sources) == 1, (wheels, sources)
    resources = ("beastbox/ui_theme.css", "beastbox/cosmic_layout.css")
    with zipfile.ZipFile(wheels[0]) as wheel, tarfile.open(sources[0]) as source:
        for path in resources:
            expected = (root / path).read_bytes()
            assert wheel.read(path) == expected, ("wheel resource mismatch", path)
            members = [m for m in source.getmembers() if m.name.endswith("/" + path)]
            assert len(members) == 1, (path, members)
            stream = source.extractfile(members[0])
            assert stream and stream.read() == expected, ("source resource mismatch", path)
    with tempfile.TemporaryDirectory() as directory:
        clean = Path(directory)
        venv.EnvBuilder(with_pip=True).create(clean / "venv")
        python = clean / "venv/bin/python"
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(wheels[0])], check=True)
        code = """
from importlib.resources import files
import beastbox
from beastbox.cosmic_ui import render_cosmic_ui
assert 'site-packages' in beastbox.__file__, beastbox.__file__
html = render_cosmic_ui('clean-wheel-smoke')
assert '__BEAST_THEME__' not in html and '__BEAST_SESSION__' not in html
for name in ('ui_theme.css', 'cosmic_layout.css'):
    text = files('beastbox').joinpath(name).read_text(encoding='utf-8')
    assert text and text in html, name
print('Installed wheel renders both packaged CSS resources away from source.')
"""
        subprocess.run([str(python), "-I", "-c", code], cwd=clean, check=True)
        subprocess.run(
            [str(python), "-I", "-m", "beastbox.cosmic_entry", "--smoke",
             "--data-dir", str(clean / "state")],
            cwd=clean, check=True,
        )
    result = {"passed": True, "wheel": wheels[0].name, "sdist": sources[0].name,
              "checks": ["CSS bytes in wheel and sdist", "isolated wheel render", "installed runtime smoke"]}
    (root / "build/cosmic-package.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
