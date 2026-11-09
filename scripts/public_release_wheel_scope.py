#!/usr/bin/env python3
"""Decide whether the public package-wheel smoke should run for a release tag.

Evidence pins and other releases that ship no wheel are not package releases.
A v* tag that publishes a wheel still runs the existing smoke unchanged.
"""

from __future__ import annotations

import argparse
import sys


def scope_decision(tag: str, asset_names: list[str]) -> tuple[str, str]:
    """Return (decision, reason). decision is 'run' or 'skip'."""
    if not tag:
        raise ValueError("tag is required")
    if tag.startswith("evidence-"):
        return (
            "skip",
            f"tag {tag} starts with evidence- and is not a package release",
        )
    if not any(name.endswith(".whl") for name in asset_names):
        return ("skip", f"release {tag} has no wheel asset")
    return ("run", f"tag {tag} is a package release with a wheel asset")


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
