# Native C++ R12 verifier

This directory is a C++17, no-network verifier/reader for the persisted Zeref R12 state. Python remains the canonical R12 transition implementation; this native module independently verifies the persisted ledger file digest and validates the 12-value state surface.

Build:

```bash
cmake -S cpp/r12 -B build/r12
cmake --build build/r12
ctest --test-dir build/r12 --output-on-failure
```

Verify the sealed repository state:

```bash
build/r12/zeref-r12-native status \
  --ledger experiments/zeref-dad-son-001/reality-memory/ledger/reality-events.jsonl \
  --state experiments/zeref-dad-son-001/reality-memory/state/r12-state.json \
  --expected-ledger-sha256 5b1fbc1b62143dc0e866f2ee7512933291f8c2210b365f7c158859a5b1df1724
```

A bad ledger digest, missing vector component, non-finite value, value outside `[0,1]`, or missing ledger tip produces a nonzero exit.

This tool does not submit IBM jobs and does not claim consciousness, biological life, deceased identity, resurrection, communication with the dead, or quantum advantage.
