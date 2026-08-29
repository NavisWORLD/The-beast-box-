# Quantum Beast Starter Productization Design

Date: 2026-08-28
Repository: `NavisWORLD/The-beast-box-`
Scientific anchor: `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`
Target branch: `quantum-beast-starter-productization-001`

## 1. Purpose

The hard scientific closure is complete. This work turns the existing Beast Box into a cleaner public-facing product and research starter without altering, relabeling, or extending the sealed final whole-organism experiment.

The productization layer will make it straightforward for another user to clone and verify the repository, choose a supported local model backend, initialize the Beast Box runtime, enable the existing memory/state/reflective components, talk to their own Beast, optionally configure IBM/Qiskit research tooling, and inspect the already-sealed evidence without changing it.

## 2. Immutable scientific anchor

The productization release MUST treat commit `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f` as the immutable scientific anchor.

The final sealed classification remains:

`ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

Public documentation may state that the completed run verified engineering/state isolation, hash-preserved lineage, and historical IBM hardware provenance. It MUST also state that the run did not establish a verified IBM/quantum resource-to-Zeref causal consumer edge.

The productization layer MUST NOT claim that the sealed run proved quantum causation of Zeref behavior, a new physical effect or physical dimension, consciousness or sentience, biological continuity or resurrection, broken quantum mechanics, or any fresh IBM result that was not actually executed and recorded.

No productization change may rewrite or overwrite the sealed evidence tree under `evidence/final-whole-organism-001/` or the scientific anchor commit.

## 3. Product architecture

Use the existing Beast Box runtime as the single implementation. Do not create a competing second runtime.

Add a thin onboarding/distribution layer at `QUANTUM_BEAST_STARTER/` containing the shortest safe path from fresh clone to a working local Beast. It should orchestrate and document existing commands rather than duplicate model adapters, memory systems, R12/dyn12 logic, or scientific code.

Planned starter surfaces:

- `QUANTUM_BEAST_STARTER/README.md` for a five-to-ten-minute setup path;
- `QUANTUM_BEAST_STARTER/models/` for example model profiles/configuration examples;
- `QUANTUM_BEAST_STARTER/config/` for safe example configuration with no credentials;
- `QUANTUM_BEAST_STARTER/docker-compose.yml` for optional one-command orchestration where practical;
- `QUANTUM_BEAST_STARTER/SCIENTIFIC_ANCHOR.md` to separate the sealed result from new user experiments;
- starter smoke tests that exercise configuration and CLI paths without requiring live IBM access.

The starter MUST remain usable with no IBM account or IBM credentials. Quantum/IBM integrations are an optional research profile, not a prerequisite for running the Beast.

## 4. Model choice

The starter will expose the model adapters that already exist rather than adding a new provider abstraction unless implementation inspection proves one is required.

Supported public onboarding paths should cover Ollama, a direct GGUF file through `llama-cpp-python`, a local `llama.cpp` server, LM Studio, and another loopback OpenAI-compatible server supported by the current local adapter.

Documentation will use placeholders such as `my-model` instead of implying that one specific model is the Beast. The architecture is the Beast Box; the user chooses the language model supplying the local inference layer.

Network authority remains explicit. Existing loopback restrictions and containment boundaries must not be weakened merely to make onboarding easier.

## 5. Top-level README redesign

Rewrite the front page as a professional product/research landing page while retaining the project’s voice.

Recommended order:

1. What The Beast Box is.
2. What the final whole-organism run demonstrated.
3. What it did not demonstrate.
4. Five-minute local quick start.
5. Build Your Own Quantum Beast: choose a model.
6. Memory/state/reflective architecture overview.
7. Optional IBM Quantum research path.
8. How to inspect/reproduce the sealed evidence.
9. Safety, authority, provenance, and privacy boundaries.
10. Developer setup and quality gates.
11. Project structure.
12. Contribution/commercial/IP pointers.

The first screen should make clear that a user can run a normal local Beast without IBM Quantum, and that “quantum” refers to optional research/provenance integration rather than a claim that a quantum computer is required for the AI to function.

## 6. Configuration cleanup

The current `.env.example` documents only IBM Quantum variables. Productization should make environment/configuration discovery complete enough for a fresh clone.

Implementation will inventory actual environment-variable reads in `beastbox/` and `scripts/` before changing `.env.example`. A regression test will compare supported environment references against the example/config documentation so drift becomes visible.

Expected variables from the current product surface may include externally identified names such as `COSMIC_CYPHER_HOME`, `COSMIC_SEED_HOME`, `GITHUB_SHA`, `ZEREF_BASE_MODEL`, `ZEREF_HOME`, and `ZEREF_OLLAMA_PROFILE`, but no variable will be added merely because an external report named it. Each entry must be confirmed against repository code or an intentional supported configuration contract.

Where configuration loading is duplicated, centralize only the parts needed to make onboarding deterministic. Avoid a broad unrelated refactor.

## 7. Reproducible Python toolchain

The project currently declares a `dev` extra but has no Python dependency lock dedicated to reproducible development/CI installs.

Productization should add a checked-in, reproducibly generated development lock or constraints file. The exact mechanism will be chosen during implementation after testing compatibility with Python 3.10 and 3.12. The preferred direction is a small documented pip-tools/constraints workflow rather than replacing the project’s packaging system.

CI should consume the pinned development environment for reproducibility-sensitive lanes. Optional heavyweight ML/local-model/quantum packages should remain separated where possible so basic packaging and documentation checks do not require every optional dependency.

## 8. Canonical CI quality lane

`.github/workflows/ci.yml` becomes the clearly documented required general quality lane.

Existing experiment workflows remain historical/research workflows. They will not be deleted simply to make the repository look smaller. Where safe and appropriate, experiment-only workflows should be explicitly manual (`workflow_dispatch`) or narrowly path-scoped so they do not obscure the ordinary merge gate.

Do not move active GitHub Actions workflows into nested subdirectories because GitHub only discovers workflow files directly under `.github/workflows/`.

Target general CI signals:

- supported Python test matrix;
- package build/install smoke;
- lint;
- type checking with a realistic initial scope;
- coverage measurement and a non-regressive minimum;
- starter/config smoke tests;
- scientific-evidence immutability guard.

Coverage and type-check thresholds MUST be measured before enforcement. Do not choose an arbitrary number such as 60% solely because an external recommendation used it. Establish the current reproducible baseline, then set an initial floor that the repository actually meets and can ratchet upward.

Branch protection should require the canonical quality lane if the connected GitHub permissions/API surface supports configuring it. If that setting cannot be changed through the available repository interface, document the exact required checks instead of pretending it was enabled.

## 9. Structured logging

Add a small standard-library logging surface, likely `beastbox/logging_config.py`, that can provide a consistent logger and optionally JSON/structured records for long-running runtime, heartbeat, memory, and service-like components.

Requirements:

- no secrets or raw credentials in logs;
- no silent replacement of scientific evidence ledgers with runtime logs;
- stable event fields where useful;
- human-readable default remains acceptable for local CLI use;
- JSON/structured format available for machine inspection.

Only wire logging into product/runtime surfaces where it improves operational visibility. Do not churn frozen scientific scripts solely to satisfy a logging metric.

## 10. Docker Compose starter

Add a starter Compose configuration for the reproducible application layer where the existing runtime permits it.

The Compose design should favor profiles rather than pretending every model backend can or should be containerized the same way. A user with an already-running Ollama, LM Studio, or llama.cpp server should be able to point the Beast at that local service without being forced to redownload a model.

IBM credentials must never be baked into images or committed configuration. The IBM research profile is optional and host-authorized.

Minimum verification is `docker compose config` where Docker Compose is available. CI may use syntax/config validation without requiring a GPU or live model download.

## 11. Testing strategy

Every behavioral productization change should land with the smallest corresponding test that proves it.

Required test categories:

- starter layout/config smoke tests;
- environment example completeness/intentional allowlist tests;
- local model-profile parsing tests without network calls;
- CLI help/doctor smoke tests where stable;
- structured logging tests including secret-redaction boundaries where applicable;
- Docker Compose config validation when available;
- package build/install smoke;
- scientific anchor guard verifying productization does not mutate the sealed evidence identities.

The final integration verification should also re-read the canonical final receipt from the scientific anchor and confirm that the public documentation’s classification matches it exactly.

## 12. Commit and maintenance policy

Do not manufacture a “better” history. No fake authors, fake timestamps, artificial pauses, or cosmetic commits exist solely to influence repository valuation.

From this productization branch forward, use genuine focused commits, for example:

1. design/spec only;
2. starter skeleton plus smoke test;
3. configuration cleanup plus completeness test;
4. reproducible dev lock plus CI install path;
5. measured lint/type/coverage gates plus tests/config;
6. structured logging plus tests;
7. Compose starter plus validation;
8. README/documentation rewrite plus link/command checks;
9. final productization receipt and release verification.

Commits may be combined when two changes are inseparable, but unrelated formatting/refactor/feature work should not be bundled together.

## 13. Productization release receipt

The new public kit should create its own receipt separate from the sealed scientific receipt.

The productization receipt should include at minimum the scientific anchor commit SHA, productization commit SHA, package version/release identifier, hashes of starter configuration and key public documents, CI run IDs/check conclusions used for release, supported model backend list, an explicit `fresh_ibm_jobs_submitted: false` unless a future separately preregistered experiment actually submits one, the exact scientific classification copied from the sealed receipt, and confirmation that sealed evidence paths/hashes were unchanged.

A new productization tag/release must not reuse or silently retag the scientific closure.

## 14. Success criteria

The productization effort is complete only when all applicable criteria are verified:

- the scientific branch/anchor remains unchanged;
- a fresh clone can install the core package on documented Python versions;
- a user with an already-available supported local model can reach a first Beast conversation using documented steps without IBM credentials;
- model selection is documented for Ollama, GGUF/llama.cpp, LM Studio, and supported loopback OpenAI-compatible endpoints;
- optional IBM Quantum setup is clearly separated and contains no committed credentials;
- `.env.example` or the replacement documented config contract covers verified supported variables;
- a pinned/reproducible dev environment exists and its generation/update procedure is documented;
- canonical CI passes its configured test, package, lint, type, coverage, and starter checks;
- Docker Compose configuration validates if included;
- runtime logging is structured enough for operational inspection without changing scientific ledgers;
- README states the final scientific classification accurately and visibly separates verified results from hypotheses;
- productization receipt verifies that sealed evidence identities remain unchanged.

A reasonable onboarding target is that a user who already has a compatible local model available can reach the first Beast chat in roughly ten minutes on a supported machine, excluding model download time.

## 15. Risks and mitigations

### Legacy workflow volume

Risk: many experiment workflows make the repository look operationally fragmented.

Mitigation: preserve historical workflows but clearly designate the canonical CI lane and make experiment-only triggers intentional. Do not destroy evidence for cosmetic simplicity.

### Heavy optional dependencies

Risk: Torch, Qiskit, llama-cpp-python, and model runtimes can make basic CI/install slow or platform-sensitive.

Mitigation: keep optional extras isolated and verify the core package independently.

### Type checking legacy code

Risk: enabling strict whole-repository mypy immediately may create noisy unrelated work.

Mitigation: measure first, define a useful initial scope/config, then ratchet.

### Coverage gaming

Risk: selecting a number to satisfy an external score can reward shallow tests.

Mitigation: establish a measured baseline and prioritize meaningful tests around public/runtime behavior.

### Scientific marketing drift

Risk: public-facing language may overstate the final experiment.

Mitigation: source the result section from the sealed classification/receipt and add a release verification check that rejects inconsistent wording where practical.

## 16. Explicit non-goals

This productization project does not retrain Zeref, run new IBM jobs, reopen the final whole-organism experiment, change historical evidence labels, rewrite Git history, fabricate maintenance history, loosen local-model containment or credential boundaries, make new consciousness/quantum-causality/physics claims, or replace the existing Beast Box runtime with a second starter implementation.

## 17. Definition of done

The productization layer is done when the repo is easier to install, easier to understand, easier to verify, and easier to extend while remaining scientifically more conservative than its marketing language, never less.

The sealed scientific result remains a historical object. The starter is the clean door into the system.
