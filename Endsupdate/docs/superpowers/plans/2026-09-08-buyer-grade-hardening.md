# Buyer-Grade Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use a test-first workflow for behavior changes and verify each batch in Product CI before proceeding.

**Goal:** Harden the existing Beast Box 0.6.0 codebase into a reproducible, independently testable, buyer-diligence-ready engineering asset without rebuilding, deleting, rewriting history, altering sealed evidence, or weakening the model/system/authority separation.

**Architecture:** Preserve the current durable substrate, COSMIC.CYPHER owner surface, CST/dyn12/CNS/R12/continuity semantics, model-provider adapters, experimental lineages, optional integrations, and evidence boundaries. Add engineering controls around the existing system: deterministic dependency resolution, clean-clone/container paths, honest whole-package quality gates, explicit health/readiness and environment contracts, reproducibility receipts, security checks, and buyer-facing diligence documentation.

**Tech stack:** Python 3.10-3.12, setuptools, pytest/coverage, Ruff, mypy, uv, Docker Compose, GitHub Actions, JSON receipts, existing local-first reference provider.

**Spec:** User-approved `CORY DAVIS // BEAST BOX // BUYER-GRADE PRODUCT HARDENING` directive supplied 2026-09-08.

## Global constraints

- Base commit is `e16ab50839497fab6f831267dd8c3b513936ea3e`; never force-push or rewrite history.
- `MODEL != SYSTEM`, `MODEL != MEMORY`, `MODEL != STATE`, `MODEL != PROVENANCE`, `MODEL != AUTHORITY`.
- State/information may travel; authority must never automatically travel with it.
- Preserve supported, experimental, historical, legacy-compatibility, deprecated-but-preserved, sealed-evidence, generated, and optional surfaces unless a security/build defect requires a documented migration.
- Preserve sealed scientific results and historical failure/null evidence exactly.
- Keep the deterministic reference path cloud-free and model-download-free.
- Do not add fake tests, fake evidence, fake contributors, fabricated receipts, or coverage exclusions used only to improve a percentage.
- Release only after real release gates pass.

---

### Task 1: Baseline and evidence boundary

**Files:** `docs/superpowers/plans/2026-09-08-buyer-grade-hardening.md`, `docs/diligence/baseline-e16ab508.json`.

- Record starting SHA, current release, Product CI run/job/artifact IDs, test count, current measured coverage and its exclusion caveat, acceptance/security/sealed-evidence results, and branch-protection state.
- Verify the existing sealed-evidence guard and productization anchor remain the canonical non-mutation boundary.

### Task 2: Reproducible dependencies

**Files:** `pyproject.toml`, `uv.lock`, `requirements-dev.txt`, `scripts/check_lock.py`, `.github/workflows/product-ci.yml`, `docs/DEPENDENCIES.md`.

- Pin a documented uv tool version.
- Generate and commit `uv.lock` from the real project metadata; never hand-author resolver output.
- Make CI run `uv sync --frozen` for the buyer-grade lane and fail when lock metadata is stale.
- Keep heavy providers optional; base install remains dependency-light.
- Export a pip-consumer lock only when generated from the same lock and clearly labeled.

### Task 3: Honest whole-package quality gate

**Files:** `pyproject.toml`, `Makefile`, `.github/workflows/product-ci.yml`, relevant tests.

- Remove first-party coverage omissions for `descendant`, `arms`, `autonomy`, and `soul`.
- Enable branch coverage and XML output.
- Establish an honest first-pass whole-package floor of at least 60%; raise only after meaningful tests justify it.
- Expand Ruff to the actual supported first-party surface rather than a hand-selected scanner-friendly list.
- Expand mypy to core durable/provider/COSMIC/persistent-substrate contracts in controlled batches; suppressions must be local and justified.

### Task 4: Container and clean-clone runtime

**Files:** `Dockerfile`, `compose.yaml`, `.dockerignore`, `docs/QUICKSTART.md`, tests/smoke scripts.

- `docker compose up --build` launches the real local COSMIC.CYPHER runtime using the deterministic reference provider with no cloud credentials/model downloads.
- Persist Beast state in a named volume, bind UI to loopback, run non-root, add a real readiness healthcheck, and keep Ollama optional via a profile rather than mandatory.

### Task 5: Health, readiness, logging, diagnostics

**Files:** `beastbox/cosmic_web.py`, `beastbox/logging_config.py`, `beastbox/doctor.py`, tests.

- Add `/healthz` for process liveness and `/readyz` for durable runtime readiness; neither endpoint exposes prompt/memory contents or secrets.
- Emit stable privacy-safe structured request/runtime events with duration/status/provider/runtime identifiers where available.
- Extend `beastbox doctor` with package version, lock/build metadata, durable-state verification, and actionable status while preserving existing keys.

### Task 6: External contracts and validation

**Files:** existing dataclasses/validators plus `docs/schema/*.schema.json` and tests.

- Publish schemas for current public provider/runtime/event/checkpoint/backup structures without creating a parallel incompatible model.
- Test missing/unexpected/oversized/non-finite/path-traversal/unsafe-URL/authority-escalation inputs and keep fail-closed behavior.

### Task 7: Environment inventory

**Files:** `.env.example`, `scripts/check_env_documentation.py`, tests, Makefile/CI.

- Statically inventory literal environment-variable reads in supported first-party Python and scripts.
- Require every discovered variable to appear in `.env.example` with safe blank/example semantics and subsystem/sensitivity documentation.
- Fail CI when a new literal environment read is undocumented.

### Task 8: Experiment reproducibility

**Files:** `configs/experiments/`, experiment runner/adapter modules, `docs/REPRODUCE.md`, tests.

- Wrap future/re-runnable experiments in versioned config + machine-readable receipts containing git SHA/dirty state/platform/lock hash/seed/provider identity/input hashes/state hashes/timings/classification/output hashes.
- Keep three explicit modes: deterministic reference reproduction, external-model reproduction, and historical receipt verification.
- Missing source artifacts must fail closed; never synthesize replacement evidence.

### Task 9: Security/threat model

**Files:** `SECURITY.md`, `docs/THREAT_MODEL.md`, `scripts/security_audit.py`, tests/CI.

- Document and test trust boundaries for model→host/tools, memory/import→authority, external providers/URLs/filesystem, backups/plugins/sensors/cloud credentials.
- Preserve provider-swap authority revocation and restarted default denial as mandatory acceptance checks.
- Add dependency audit/static checks only where signal is actionable; do not normalize noisy ignored findings.

### Task 10: Buyer-grade CI and release artifacts

**Files:** `.github/workflows/product-ci.yml`, release workflows, Makefile, smoke scripts.

- Separate fast PR, full integration, and release evidence responsibilities while reusing canonical commands.
- Archive coverage XML, JUnit, acceptance receipt, package smoke, Compose smoke, security result, SBOM/checksums where available.
- Pin action/tool versions appropriately and keep permissions least-privilege.

### Task 11: Clean-room acceptance

**Files:** `scripts/run_architecture_acceptance.py` or focused companion, Makefile, CI.

- Extend the existing real acceptance harness to prove locked install, init, deterministic conversation, restart continuity, inspect, backup/restore, corruption rejection, A→B→A continuity, authority non-persistence, wheel/sdist install, installed CLI, and Compose smoke.
- Emit `artifacts/acceptance/latest.json` in runtime/CI output (not fabricated or committed as a passing receipt).

### Task 12: Diligence documentation and closure

**Files:** `docs/REPRODUCE.md`, `docs/BUYER_TECHNICAL_DILIGENCE.md`, `docs/THREAT_MODEL.md`, `docs/CONFIGURATION.md`, existing guides/README links, machine-readable diligence summary.

- State measured tests/coverage/security/reproducibility/install facts with exact evidence references.
- List supported vs experimental vs historical vs optional surfaces and explicit scientific non-claims.
- List genuine limitations, including repository-history maturity as time-dependent rather than cosmetically repairable.
- Final verification: inspect diff for accidental deletion/evidence mutation, run Product CI/acceptance/package/Compose/security gates, then open a PR to `main`; do not merge/release unless all intended gates are green.
