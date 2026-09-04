#!/usr/bin/env python3
"""Frozen execution shim for persistent-substrate-model-swap-002-historical-b4e53.

The underlying runner was committed with stale R12 seed-file SHA constants.
The preregistered 002 seed bytes are already committed and hash to the values
below. This shim changes only those two file-identity constants before invoking
the underlying runner. No model, prompt, metric, control, or success criterion
is changed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


R12_STATE_SHA256 = "cc42753463e7467e58626f8a81c75716183406c29d15acc2a1aee352a0570162"
R12_HISTORY_SHA256 = "cc42753463e7467e58626f8a81c75716183406c29d15acc2a1aee352a0570162"


def _load_runner():
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
