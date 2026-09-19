# System closure execution

User specification: final one-shot system closure, 2026-09-05. Base:
`b43f2883425e56446d3db8c009ea301b0adc21bc`.

Approved design: adapt the existing CosmosRuntime, ReconciliationMemory, CNS,
SynapticField and RefractiveMemoryRouter. Add atomic SQLite continuity checkpoints,
versioned normalized events, a policy-controlled simulated tool, inspect/backup/
recovery CLI, and an EnD combined kit. Preserve the frozen experiment source and
all historical evidence. Formal external Synapse/HEARTLIGHT products are not
assumed present. The normal path needs no IBM or model credentials.

Execution gates (update with measured results in READINESS.json):
- [x] Source/evidence identity verification, manifest and claim audit.
- [x] Failing regression tests for restart, corruption, authority, A-B-A and rollback.
- [x] Runtime adapters plus CLI and actual end-to-end receipt.
- [x] Full tests, scoped lint/types, security, build, clean wheel/sdist installs.
- [x] Documentation, EnD kit, source-bound packaging and pushed Python 3.10–3.12 CI.
- [ ] Publication is recorded externally by the GitHub release and its final verification receipt.

Task ownership: controller owns implementation/CI/release; documentation agent
owns architecture manifest and claim/security documents. Their interfaces are
source paths and explicit status labels; no code-file overlap. Final code review
is independent. This is a fresh isolated clone on an integration branch.

Handoff reconciliation: preserved remote source-snapshot commit 138cf52 via merge beecfae.
Local gates: 767 tests, 62 focused swap tests, 69% coverage, 24 acceptance checks.
Publication remains gated on final source CI; see READINESS.json and Actions artifacts.

Verified pushed baseline c1f23d81db6299874a630a243c6c839f730de74c passed Product CI
33985209600. Final publication repeats all exact-source gates, preserves raw JUnit
and architecture receipts, verifies package provenance, and refuses existing-tag
or release replacement. See the attached RELEASE_VERIFICATION.json for measured
final counts and source identity. No general production-readiness claim is made.
