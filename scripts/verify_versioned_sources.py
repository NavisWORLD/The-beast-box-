#!/usr/bin/env python3
"""Verify sealed V1 and secure V2 exact bytes against the reviewed manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.versioning import VersionIntegrityError, verify_versioned_sources


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--git-anchor", action="store_true", help="also verify original Git anchor objects")
    args = parser.parse_args()
    try:
        result = verify_versioned_sources(args.root, verify_git_anchor=args.git_anchor)
    except (VersionIntegrityError, OSError) as exc:
        parser.exit(1, "versioned source integrity failed: " + str(exc) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
