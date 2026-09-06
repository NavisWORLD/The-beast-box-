# Beast Box 0.4.0 — Durable runtime integration

This release connects the existing COSMOS conversation loop to atomic SQLite
continuity checkpoints. Memory, CNS/dyn12 state, R12 routing metadata, Hebbian
associations and provenance recover across runtime restarts and provider changes.

It adds structured synthetic/text events, explicitly permitted simulated output,
fail-closed integrity inspection, hash-verified backup/restore, loopback HTTP
hardening, end-to-end subprocess receipts, and the combined developer kit `EnD`.

The preserved real frozen-model experiment 002 remains a separate historical
`COMPLETED_DESCRIPTIVE_MEASUREMENT`. Its exact original artifact is included for
verification; no new real-model measurement or scientific claim is implied by
reference-provider regression tests. Experiment 001 failures, unavailable Model-B
revision, nulls and rejected descendants are unchanged. v0.3.2 assets are untouched.

Supported baseline: owner-controlled local Python 3.10–3.12, no IBM credentials,
no model requirement for reference operation, no physical or privileged tools.
Classification: release-hardened experimental software. Python plugins are trusted
host code; there is no hostile-plugin sandbox. Large-store throughput, encrypted
storage and multi-tenant deployment are not certified. Optional world-store,
GGUF/cypher, bio and IBM research keep their separate boundaries.

Verify downloaded assets with `sha256sum -c SHA256SUMS.txt`. The combined ZIP also
contains `SHA256SUMS` and `RELEASE_PROVENANCE.json`, binding package bytes to the
source commit/tree. Start with `EnD` inside the ZIP.

`CI_EVIDENCE.zip` retains the Python matrix JUnit, architecture/restart traces and
clean-install logs. `RELEASE_VERIFICATION.json` identifies the exact source and
workflow run, validates the receipts and records final passing test counts.
