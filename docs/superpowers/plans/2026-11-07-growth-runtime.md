# Growth runtime and interruption scoring implementation plan

**Goal:** Finish and score growth measurements without trimming curriculum or moving any gate.
**Architecture:** Keep the established training and gate computations; give the bounded multi-variant work realistic CI headroom. Save verified immutable candidate snapshots during updates. An independent always-on-failure job scores the latest snapshot using the same trainer gate code, never publishing or promoting recovery weights.
**Tech Stack:** Python/PyTorch, Node contract tests, GitHub Actions (existing CPU runner).

## Global Constraints
- No pin, gate, threshold, label, sealed schema, or TRAIN mechanic changes.
- No paid compute, QPU work, cancellation of run 42387671507, force push, auto merge, or curriculum trimming.
- Recovery evidence includes model state and existing public native observations, never private teaching transcripts or credentials.

## Tasks
- [ ] Add failing real checkpoint round-trip / corruption / bundle tests and workflow integration contracts.
- [ ] Implement immutable, hash-verified snapshots with actual attempted/applied counts and atomic latest pointer.
- [ ] Reuse unchanged trainer gates in score-only recovery; no training or publication in recovery.
- [ ] Raise CI headroom from 90 to 180 minutes; add independent recovery job and post-eval evidence upload.
- [ ] Run regression suites and confirm gate expressions are byte-for-byte unchanged.
- [ ] PR, wait for all gating checks, merge without auto; observe a post-merge scored round.
- [ ] Record timing comparison and report-only leak diagnosis with exact public benchmark replies.
