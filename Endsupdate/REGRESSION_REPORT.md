# Regression scope

New numerical module: 10/10 unittest methods passed locally (Python standard library). Baseline source: byte-for-byte Git blob copy of all 1,325 files, with no changes to original root runtime and no production-import connection to `cst_candidate`. Source identity is not the same as an independently passing copy's full test suite.

Unexecuted: full copied Python tests; live model swaps and A/B task loss; browser/desktop/mobile end-to-end; native Rust/C++ builds; packaging on all hosts; optional device and service tests. Report these as NOT RUN, not PASS. The operational legacy/corrected/ablated/control runtime feature flag is deliberately not wired: physical inputs and dyn12 software inputs have no evidenced mapping.
