#!/usr/bin/env python3
"""Decide whether the public package-wheel smoke should run for a release tag.

A tag that starts with evidence- is an evidence pin and is skipped.
Every other tag runs the existing smoke. A v* release with no wheel is not
skipped: the smoke fails on the missing download, as it did before this gate.
"""

from __future__ import annotations

import argparse
import sys


def scope_decision(tag: str, asset_names: list[str]) -> tuple[str, str]:
    """Return (decision, reason). decision is 'run' or 'skip'.

    evidence-* skips. Any other tag runs, whether or not a .whl is attached.
    """
    if not tag:
        raise ValueError("tag is required")
    if tag.startswith("evidence-"):
        return (
            "skip",
            f"tag {tag} starts with evidence- and is not a package release",
        )
    wheels = [name for name in asset_names if name.endswith(".whl")]
    if wheels:
        return ("run", f"tag {tag} is not an evidence pin; the package smoke runs")
    return (
        "run",
        f"tag {tag} is not an evidence pin; the package smoke runs and a missing wheel fails there",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--asset", action="append", default=[])
    args = parser.parse_args(argv)
    decision, reason = scope_decision(args.tag, list(args.asset))
    sys.stdout.write(f"decision={decision}\nreason={reason}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
