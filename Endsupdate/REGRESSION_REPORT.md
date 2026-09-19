# Regression scope

New numerical module: 10/10 unittest methods passed locally (Python standard library). Baseline source: byte-for-byte Git blob copy of all 1,325 files, with no changes to original root runtime and no production-import connection to `cst_candidate`. Source identity is not the same as an independently passing copy's full test suite.

Unexecuted: full copied Python tests; live model swaps and A/B task loss; browser/desktop/mobile end-to-end; native Rust/C++ builds; packaging on all hosts; optional device and service tests. Report these as NOT RUN, not PASS. The operational legacy/corrected/ablated/control runtime feature flag is deliberately not wired: physical inputs and dyn12 software inputs have no evidenced mapping.

## Full copied-runtime regression (GitHub Actions)

The initial nested suite failed **three** tests: two product README/documentation contracts and one historical-evidence receipt path comparison. These were reconstruction failures, not model- or math-benefit results. Commit `89313074b090f5d9da17a45479c218b8a1189e05` restored the original README exactly, moved the successor notes to `ENDSUPDATE_README.md`, and changed the copy's receipt guard to compare the copied Git blobs against the frozen baseline after checking that the original historical evidence is unchanged. The fixed [run 35429376824](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35429376824) passed the **complete copied Python suite on 3.10 and 3.12**, package installation, local CLI smoke and evidence guard. GitHub's `pytest -qq` output suppressed the numeric total; the next gate invokes `pytest -q` without inherited extra `-q` to report exact counts. This is a Python and source-snapshot result, not proof of GUI/native/hardware portability.

## Final verified candidate Python regression

[GitHub Actions 35429552663](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35429552663), source `bb5345e854b9897aaa2612bd1e5904de9bb995b8`: full copied suite `1,131 passed, 0 failed` on Python 3.10 and independently `1,131 passed, 0 failed` on 3.12; mathematical unit tests `17/17` and launcher contract tests `3/3` on each. Nine reference-only fresh-process checks passed on both. Package installation, CLI entry points, original scientific receipt, root CI, repository security audit and configuration contract also passed. The 3 prior copied-suite reconstruction failures remain disclosed above; they were corrected, not erased. Non-Python device/platform, real model-swap and model-level A/B gates remain NOT RUN.
