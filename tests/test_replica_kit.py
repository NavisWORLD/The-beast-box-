"""The replica kit stays inside the checkout and keeps its pinned-commit clone path."""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "replica"
PIN = "8dbda0ae99736e649fbe0609ad9b0c377768f498"
REQUIRED = (
    "setup.sh",
    "run.sh",
    "constraints.txt",
    "README.md",
    "scripts/summarize.py",
    "dashboard/server.py",
    "dashboard/index.html",
)


def _plan(tmp_path: Path, *args: str, script: Path | None = None) -> dict[str, str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    target = script or (KIT / "setup.sh")
    result = subprocess.run(
        ["bash", str(target), "--plan", "--home", str(home), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "BB_REF": "", "BB_HOME": ""},
    )
    parsed: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, value = line.split("=", 1)
        parsed[key] = value
    assert not (home / "secrets").exists()
    return parsed


def test_replica_files_are_present_and_key_stays_outside_the_repo() -> None:
    for name in REQUIRED:
        path = KIT / name
        assert path.is_file(), name
    setup = (KIT / "setup.sh").read_text(encoding="utf-8")
    run = (KIT / "run.sh").read_text(encoding="utf-8")
    assert PIN in setup
    assert "html/tests/*.js" in setup
    assert 'BB_HOME/secrets' in setup or '"$BB_HOME/secrets"' in setup
    assert "rawrphos_api_key" in setup
    assert "chmod 600" in setup
    assert "RAWRPHOS_API_KEY" not in (KIT / "constraints.txt").read_text(encoding="utf-8")
    assert "secrets/rawrphos_api_key" in run
    for script in ("setup.sh", "run.sh"):
        mode = (KIT / script).stat().st_mode
        assert mode & stat.S_IXUSR
        subprocess.run(["bash", "-n", str(KIT / script)], check=True)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "replica/README.md" in readme
    manifest = (ROOT / "docs" / "ECOSYSTEM_MANIFEST.json").read_text(encoding="utf-8")
    assert "replica/setup.sh" in manifest


def test_in_checkout_plan_uses_this_repo_and_clone_keeps_the_pin(tmp_path: Path) -> None:
    inside = _plan(tmp_path)
    assert inside["cloned"] == "0"
    assert Path(inside["repo_dir"]).resolve() == ROOT.resolve()
    assert inside["ref"] == PIN

    cloned = _plan(tmp_path, "--clone")
    assert cloned["cloned"] == "1"
    assert cloned["ref"] == PIN
    assert cloned["repo_dir"].endswith("/The-beast-box-")
    assert Path(cloned["repo_dir"]).resolve() != ROOT.resolve()

    other = _plan(tmp_path, "--ref", "main")
    assert other["cloned"] == "1"
    assert other["ref"] == "main"

    chosen = tmp_path / "already-checked-out"
    explicit = _plan(tmp_path, "--repo-dir", str(chosen))
    assert explicit["cloned"] == "0"
    assert explicit["repo_dir"] == str(chosen)


def test_standalone_copy_plans_a_pinned_clone(tmp_path: Path) -> None:
    alone = tmp_path / "kit"
    alone.mkdir()
    script = alone / "setup.sh"
    script.write_text((KIT / "setup.sh").read_text(encoding="utf-8"), encoding="utf-8")
    script.chmod(0o755)
    planned = _plan(tmp_path, script=script)
    assert planned["cloned"] == "1"
    assert planned["ref"] == PIN
    assert planned["repo_dir"].endswith("/The-beast-box-")
