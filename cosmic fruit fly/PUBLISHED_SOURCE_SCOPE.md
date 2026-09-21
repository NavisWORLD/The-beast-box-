# Published research-source scope

This branch is an isolated research implementation under `cosmic fruit fly/`. Python is the complete simulation; C++17 and Rust implement only numerical parity. This is not a biological fly, production COSMOS runtime, or proven quantum/physiological advantage.

## Included

Source modules, test suite, deterministic fixture, attribution/licensing documentation, summarized historical results, optional IBM historical replay inputs, Windows batch launchers, and numerical parity adapters. The derived FlyWire 42-node input carries upstream CC BY-NC 4.0 conditions for noncommercial research only.

## Not committed in this source commit

The original full demo MP4s, large trial JSONL ledgers, and nonessential preview PNGs are retained in the separate archived evidence ZIP. Their reported hashes and study limitations remain in the report files. `assets/forest_world_clean.png` is included unchanged as decorative forest artwork used by video renderers; it is not the actual virtual retina. Do not describe missing media as hosted by GitHub.

No raw private physiological/audio recordings or credentials are included. The historical IBM input is replayed data, not new device execution. The simulated bio channel is not personal physiological measurement.

## Validation

Run `python -m pip install -r "cosmic fruit fly/requirements-research.txt"` and `python -m pytest -q "cosmic fruit fly/tests"` from the repository root. ffmpeg is required for optional MP4 output; native C++17 and Rust toolchains are optional and their parity tests skip if missing.

On the source-only checkout, archived video/large-ledger integrity tests explicitly skip when the corresponding media are absent (89 passed, 8 skipped in the isolated source-only local run). When the evidence archive is present, those checks run normally (93 passed, 4 skipped in the full local archive). Neither result is a GitHub CI result.
