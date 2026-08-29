# Changelog

## 0.3.2 — 2026-08-29 (public-surface hardening)

Beast Box is a local-first runtime: memory, a software state controller, loopback model adapters, and a hash-chained evidence ledger. IBM Quantum is optional and is not required to install or talk to the reference synthesizer.

### What changed

- Public technical aliases: `Runtime`, `MemoryStore`, `StateController`, `ProvenanceLedger`, `EntropyCoupler`.
- Packaging now ships `beastbox*` only. Lab scripts, experiments, evidence, and starter docs stay in the source tree and out of the wheel.
- Coverage floor raised from 4% to 20% on the product spine (measured 32% on that suite).
- Product-spine tests plus experimental-boundary tests (import does not talk to IBM, does not require Qiskit/Ollama, quantum-heart defaults off, IBM submit refuses without confirm).
- Documentation split: architecture, claim boundaries, capabilities, evidence index, layer map, storage policy, CI hierarchy, license clarification.
- Machine-readable `PROJECT_STATUS.json`.
- README separates the stable product path from `experimental/pre-releases/` and `experimental/logs/`.
- Scientific wording frozen: official classification unchanged; interpretation is "not established," not a universal-negative proof.
- CI closure: numpy restored on `[dev]`/`[ml]`, product-spine suite used for the 20% floor, R12 public-kit phrases restored as software-routing language only.
- Product-surface main SHA after PR #44: `65a5b4f436d0d2b3f7be740c09c942bdb8e8f810` (Product CI, canonical CI, security audit, Cypher smoke, Quantum smoke all green).
- Experimental catalog now records the v0.3.2 hardening work under `experimental/pre-releases/` and `experimental/logs/` without treating it as a scientific result.
- Isolated wheel `cosmos_beast_box-0.3.2-py3-none-any.whl` and isolated source install proofs passed. GitHub Release tag `v0.3.2` remains owner-gated (`release.yml` fires on `v*` tags).

### How to install

```bash
pip install -e ".[dev]"
beastbox init
beastbox doctor
beastbox starter
beastbox chat "hello"
```

### Supported model backends

reference synthesizer (default), Ollama, GGUF, llama.cpp-server, LM Studio / OpenAI-compatible loopback.

### Optional

`[quantum]`, `[ml]`, `[huggingface]`, `[local-llm]`. None of these are required for the reference path.

### Experimental

`soul/`, R12 internals, IBM/QBT helpers, Zeref identifiers, `experimental/` snapshots and logs. Identifiers are retained. They are not the default path.

Public research surfaces:

- `experimental/pre-releases/`
- `experimental/logs/`

### What was tested

Product-spine tests (18), experimental-boundary tests (10), starter/receipt/workspace tests, wheel contents, CLI smoke, loopback URL rejection, workspace escape rejection, Product CI 3.10/3.12, canonical CI 3.10/3.12, security audit, sealed-evidence immutability guard.

### Scientific result

Official classification remains:

`ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

SOUL-QBT historical replay remains:

`ENGINEERING_CONTROL_INCONCLUSIVE`

What it says: a causal resource/source → downstream consumer effect has not been established.

What it does not say: that a universal negative causal effect was proved; that consciousness was measured; that quantum mechanics broke; that IBM hardware execution is the same thing as a consumer effect.

### Remaining debt

- OWNER LEGAL DECISION REQUIRED on historical MIT vs current proprietary terms.
- FUTURE OPTIONAL REPOSITORY TOPOLOGY for a physical product/lab split.
- Optional hygiene: rewrite historical workflow YAML (not required; observed auto-trigger set on a normal main product push is five workflows).
- OWNER-GATED: push git tag `v0.3.2` to fire `.github/workflows/release.yml`.

## 0.3.1 — productization-era (canonical tree)

- QUANTUM_BEAST_STARTER kit, productization receipt guard, sealed-evidence immutability check in CI.
- Loopback-only local model adapters and workspace path containment.
- Cosmic Cypher CLI entry points (`cosmic.cypher-cli`, `zeref`, `beast-arms`).
- Whole-organism seal published in README.

## 0.2.0 — 2026-08-12

- public E1-E20 Beast Box gauntlet
- host-enforced synthetic capability broker
- state capsules, authority stripping and fresh-process reconstruction
- seven-role CNS reference runtime
- dyn12/dyn42/dyn54/static54/tri3 state-family references
- Mixture-of-States attention utilities and trainable PHOS/dyn12 reference LM
- Reconciliation Memory, semantic recall, Hebbian associations and consolidation
- sensory freshness, local 16D WAV features and paired-state controls
- heartbeat, organism/evolution/internal-monologue slow state
- quantum-heart OFF/SHADOW/EXPERIMENTAL reference coupler
- Hugging Face QC67_cosmo integration/reference helper
- optional host-side IBM Quantum H-Z-H transport
- optional 128-bit required-state shard transport over multi-PUB IBM job
- audio and Spark ablation helpers
- loopback-only local dashboard
- cross-platform installation scripts, Dockerfile and package workflow

## 0.1.0 — 2026-08-12

Initial contained Beast Box reference harness.
