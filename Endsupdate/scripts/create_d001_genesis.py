#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from beastbox.descendant.stage import create_genesis_manifest


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--prime-sha256', required=True)
    p.add_argument('--checkpoint-sha256', required=True)
    p.add_argument('--proof-sha256', required=True)
    p.add_argument('--training-allowed', action='store_true')
    p.add_argument('--out', type=Path, required=True)
    a=p.parse_args()
    m=create_genesis_manifest(
        prime_gguf_sha256=a.prime_sha256,
        canonical_checkpoint_sha256=a.checkpoint_sha256,
        reconstruction_proof_sha256=a.proof_sha256,
        training_allowed=a.training_allowed,
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(m, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps(m, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
