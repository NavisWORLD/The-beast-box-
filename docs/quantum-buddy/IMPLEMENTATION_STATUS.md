# Quantum Buddy Shadow Core — Implementation Status

**Branch:** `feature/quantum-buddy-shadow-core-001` (isolated; not merged)
**Design:** `docs/superpowers/specs/2026-09-24-quantum-buddy-cosmos-design.md`
**Plan:** `docs/superpowers/plans/2026-09-24-quantum-buddy-shadow-core.md`

## Implemented code

1. **Persistent substrate contract:** immutable 12D person state and separate 12D metric packet, canonical float32 SHA-256, opt-in consent and strict mode/source classes.
2. **Existing-account Cosmos repository:** `buddy-state` / `buddy-history` via exact `/userId` point operations, If-Match/ETag conditional writes, monotonic person state versions, idempotent provenance receipts. Tests use SDK-shaped fakes only. **No live Azure write attested or resources provisioned.**
3. **Frozen qb-v1 operator:** six-qubit fixed circuit, 24 rotations, 12 CNOTs in entangled mode, six Z and six X expectations; classical amplitude-matched, archived replay and ideal-entangled/unentangled software simulation share the same state contract. Hardware modes fail closed without separately granted execution authority and verified costs.
4. **CNS fusion fix:** explicit `person_state12` is not hidden behind a preceding 12D quantum packet; buddy `qstate12` is never used as the person drive.
5. **Refresh service:** revocable consent, source/version/ETag comparison, stale results rejected with history receipts, sanitized failures.
6. **Native RAWRPHOS metric:** frozen weights; qstate affects the existing 12D state-attention geometry rather than granting model authority. Cached/uncached metric tests, baseline/off compatibility and model-authored shadow endpoint.
7. **Phase-8 shadow harness:** preregistered frozen 32 synthetic states, four nearby drifts, five offline arms, numerical identity/response/quality telemetry and matched prompts/seeds. `--smoke` is explicitly a **synthetic model fixture**, not RAWRPHOS experimental evidence. Actual full native-14K holdout requires a separately pinned local checkpoint and an explicitly acknowledged long CPU run.
8. **Owner-only bridge:** disabled-by-default state and shadow routes; ordinary chat stays unaffected even if shadow fails; no public multi-user rollout.
9. **Acceptance runner:** reproducible test commands, source commit, bounded numeric evidence and SHA-256 manifest. Attestation is false unless actual scoped checks pass.

## Reproducible verification

- Full Product CI **previously passed** at GitHub Actions run [36100031433](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36100031433) for an earlier feature-branch commit. The final integration needs its own current-HEAD CI success.
- Dedicated native attention tests: [36098640724](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36098640724) passed on a preceding task commit.
- Owner shadow route tests: [36099413938](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36099413938) passed on a preceding task commit.
- Complete current-HEAD verdict and final artifact must be taken from the latest branch `Quantum Buddy final offline acceptance` workflow; do not infer that verdict from earlier commits.

## Explicitly not done

- No real Cosmos DB containers have been created, modified or tested live in this branch.
- No fresh Rigetti/IBM QPU job, quantum credit usage or pay-as-you-go execution.
- No Vercel/Railway production deployment or user-facing buddy responses.
- No retraining, no proven product improvement, no demonstrated quantum advantage.
- No full 32-person x 8-prompt x 4-seed native-checkpoint generation run has been claimed complete here.
- No independent fresh-context reviewer was available through this harness; author self-review and automated CI do not replace an independent pre-merge review.

## Execution rulings

- **Remote isolation:** the local container could not resolve GitHub; the owner approved a new isolated GitHub branch and GitHub Actions RED-to-GREEN verification instead of a local worktree.
- **Offline simulator:** qb-v1 uses an auditable 64-amplitude Python ideal statevector implementation rather than requiring Qiskit for offline shadow tests. Future QPU promotion requires cross-simulator/hardware validation.
- **Product CI dependency:** Product CI installs `requirements-dev.txt`, distinct from the `pyproject.toml` dev extra. Both now include the Azure ETag type so SDK-shaped fake tests can pass across CI environments.
- **Conservative promotion:** changes remain shadow-only. Numerical diversity and qstate retrieval are not equivalent to useful personalization or quantum superiority.

## Next authorized boundary

Recheck current-HEAD Product CI, contract/native and offline acceptance. Obtain independent code review and provision the two containers in the existing account only after a separate live-resource authorization. Then run frozen Phase-8 with actual native weights and preregistered quality labels. Fresh QPU execution and any production deployment remain separate owner decisions.
