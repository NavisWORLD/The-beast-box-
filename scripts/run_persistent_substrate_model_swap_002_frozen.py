#!/usr/bin/env python3
"""Frozen execution shim for persistent-substrate-model-swap-002-historical-b4e53.

The underlying runner was committed with stale R12 seed-file SHA constants.
After failed run 33913541101, the genesis R12 object's own embedded integrity
hash was repaired before any model inference occurred. After failed run
33913905926, the repository root is also inserted on sys.path so the existing
Model-A loader can import scripts.run_zeref_dad_son_chat when this shim is
executed by file path. Neither correction changes any model, prompt, metric,
control, or success criterion.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


R12_STATE_SHA256 = "f8b02245daf0d48ec8b404eef1105b92558e619ea3865f792bf52b34d6b06559"
R12_HISTORY_SHA256 = "f8b02245daf0d48ec8b404eef1105b92558e619ea3865f792bf52b34d6b06559"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _ensure_repo_root_importable() -> None:
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_runner():
    _ensure_repo_root_importable()
    path = Path(__file__).with_name("run_persistent_substrate_model_swap_002.py")
    spec = importlib.util.spec_from_file_location("persistent_substrate_model_swap_002_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load underlying 002 runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    runner = _load_runner()
    runner.R12_STATE_SHA256 = R12_STATE_SHA256
    runner.R12_HISTORY_SHA256 = R12_HISTORY_SHA256
    return int(runner.main())


if __name__ == "__main__":
    raise SystemExit(main())
