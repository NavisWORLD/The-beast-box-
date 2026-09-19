"""Constrained local launch surface for the Endsupdate source snapshot.

This is a software path guard, NOT an OS sandbox or independent security
certification. It exposes only reference-provider durable init/chat/inspect.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
DATA_NAME = ".endsupdate-data"
ENV_ALLOW = ("PATH", "SYSTEMROOT", "WINDIR", "HOME", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP")


def dedicated_data_dir(base: Path = HERE) -> Path:
    """Require a non-symlink, child-only data root before any runtime writes."""
    if base.is_symlink() or not base.is_dir():
        raise ValueError("candidate source root is missing or is a symlink")
    candidate = base / DATA_NAME
    if candidate.is_symlink() or (candidate.exists() and not candidate.is_dir()):
        raise ValueError("candidate data root must be a real directory, not a link or file")
    if candidate.resolve().parent != base.resolve():
        raise ValueError("candidate data root resolves outside the isolated copy")
    return candidate


def build_command(action: str, text: str | None = None, *, base: Path = HERE) -> list[str]:
    if action not in ("init", "inspect", "chat"):
        raise ValueError("this local launcher only accepts init, inspect, chat")
    data = dedicated_data_dir(base)
    command = [sys.executable, "-m", "beastbox", "runtime", action, "--data-dir", str(data)]
    if action == "chat":
        if text is None or not text.strip():
            raise ValueError("chat requires text")
        command += ["--provider", "reference", text]
    elif text is not None:
        raise ValueError("only chat takes text")
    return command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Isolated reference-only Beast Box local launcher")
    parser.add_argument("action", choices=("init", "chat", "inspect"))
    parser.add_argument("text", nargs="?")
    args = parser.parse_args(argv)
    if not (HERE / "beastbox" / "runtime_cli.py").is_file():
        parser.error("Endsupdate source copy is incomplete")
    try:
        command = build_command(args.action, args.text)
    except ValueError as exc:
        parser.error(str(exc))
    # Prevent accidentally forwarding IBM/cloud tokens, API keys or model
    # endpoints into the constrained reference-only launcher.
    env = {k: os.environ[k] for k in ENV_ALLOW if k in os.environ}
    env["PYTHONNOUSERSITE"] = "1"
    result = subprocess.run(command, cwd=HERE, env=env, check=False)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
