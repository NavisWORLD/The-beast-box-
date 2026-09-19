from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .state import StateCapsule


def reconstruct_capsule(raw: dict) -> dict:
    capsule = StateCapsule.from_dict(raw)
    return capsule.to_dict()


def cold_roundtrip(raw: dict) -> dict:
    """Serialize state, reconstruct it in a genuinely fresh Python process, return it."""
    with tempfile.TemporaryDirectory(prefix="beastbox-fresh-") as td:
        inp = Path(td) / "in.json"
        out = Path(td) / "out.json"
        inp.write_text(json.dumps(raw), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "beastbox.fresh", "--child", str(inp), str(out)],
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"fresh process failed: {proc.stderr.strip()}")
        return json.loads(out.read_text(encoding="utf-8"))


def _main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--child", nargs=2, metavar=("INPUT", "OUTPUT"))
    args = p.parse_args()
    if not args.child:
        p.error("--child INPUT OUTPUT required")
    inp, out = map(Path, args.child)
    raw = json.loads(inp.read_text(encoding="utf-8"))
    out.write_text(json.dumps(reconstruct_capsule(raw), sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
