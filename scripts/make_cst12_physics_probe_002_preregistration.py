#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.cst12_physics_probe import make_preregistration, sha256_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation-freeze-commit", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    packet = make_preregistration(implementation_freeze_commit=args.implementation_freeze_commit)
    args.out.mkdir(parents=True, exist_ok=True)
    prereg = args.out / "preregistration.json"
    prereg.write_text(json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = sha256_json(packet)
    (args.out / "PREREGISTRATION_SHA256").write_text(digest + "  preregistration.json\n", encoding="utf-8")
    print(digest)


if __name__ == "__main__":
    main()
