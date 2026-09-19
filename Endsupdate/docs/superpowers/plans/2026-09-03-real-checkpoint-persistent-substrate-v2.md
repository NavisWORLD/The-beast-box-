# Persistent Substrate Real-Checkpoint Model Swap v2 Implementation Plan

> **For maintainers:** Execute this plan with test-driven development. Do not reinterpret or relabel historical evidence. The v1 offline fixture run and the immutable final-organism real-model swap remain separate historical records.

**Goal:** Demonstrate one continuous `PersistentSubstrate` surviving a real frozen Model A -> real frozen Model B -> exact Model A round trip, with no training or hidden adaptation, while preserving canonical memory/world identities and emitting hash-tracked evidence suitable for factual public documentation.

**Architecture:** Keep model objects outside `PersistentSubstrate`; model authority never becomes substrate state. Reuse the already-sealed Zeref loader/scorer and SmolLM2 snapshot/scorer semantics from `scripts/final_reality_bridge_reference.py` and `scripts/final_reality_bridge_model_swap.py`. Add a v2 measurement adapter layer, fixed prompt/candidate battery, A->B->A runner, controls, verification, and a manual/branch-isolated workflow. Preserve all historical evidence byte-for-byte.

**Scientific boundary:** Passing v2 establishes an engineering property: persistent software state can remain usable across controlled real model checkpoint substitution and exact restoration. It does not establish consciousness, identity continuity, biological life, a literal soul, or any quantum/physical causal effect. A model-effect classification may be emitted only from preregistered numeric rules and controls; prose is never evidence.

## Frozen inputs

- Source branch base: `main` at `a3366a77f8067b984286315f26e7d924482d0c8a`
- Working branch: `upgrade/real-checkpoint-persistent-substrate-002`
- Model A checkpoint SHA-256: `454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425`
- Model A recovery artifact: Actions run `33132925890`, artifact `zeref-world-r12-downstream-diagnostic-v2-33132925890`; fail closed if unavailable or hash mismatched.
- Model A architecture: `experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py`
- Model B: `HuggingFaceTB/SmolLM2-135M`
- Model B revision: `4e53f736cbb20a9a0f56b4c4bf378d9f306ff915`
- Model B snapshot manifest SHA-256: `f75e3350cdeda2c553f2cae22d493eb5f6fa303d84c28c7cf085ca25e4112bfc`
- Model B weight SHA-256: `80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1`
- Canonical memory: 352 records; SHA-256 `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`
- World source set SHA-256: `07216bb2a4ca979ca1ea4304efb92b09ee8aad74685df43196d694f3bd7ef8ba`
- Historical final-organism scientific classification remains `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`.

## Task 1: Freeze v2 protocol and resolve factual boundaries

**Files:**
- Create: `beastbox/persistent_substrate/real_models.py`
- Create: `tests/test_persistent_substrate_real_models.py`
- Modify public text only after the experiment is sealed.

Write failing contract tests first for exact checkpoint identities, parameter immutability, finite conditional NLL, and nonzero continuation-token counts. Verify RED because the v2 adapter module does not yet exist.

Implement reusable frozen adapters that:
- load the exact Zeref checkpoint through the existing `_load_model` path;
- load only the pinned SmolLM2 snapshot with `trust_remote_code=False`;
- call `.eval()` and inference/no-grad mode;
- never construct an optimizer, trainer, fine-tuner, or generation-based scorer;
- expose immutable checkpoint identity receipts and `parameter_sha256()`.

## Task 2: Freeze a paired battery and metric semantics

**Files:**
- Create: `beastbox/persistent_substrate/real_prompts.py`
- Create: `beastbox/persistent_substrate/real_metrics.py`
- Create: `tests/fixtures/persistent-substrate-real-v2/prompts-v2.json`
- Create: `tests/test_persistent_substrate_real_prompts.py`
- Create: `tests/test_persistent_substrate_real_metrics.py`

Use fixed public/control, canonical-memory, world-knowledge, calibration, and nonce/counterfactual families. Freeze the battery SHA before the real run. Use conditional-NLL deltas only; no learned probe, classifier, calibration fit, hyperparameter sweep, or post-hoc threshold.

## Task 3: Real A -> B -> A runner over one substrate

**Files:**
- Create: `beastbox/persistent_substrate/real_runner.py`
- Create: `tests/test_persistent_substrate_real_runner.py`

Sequence:
1. Construct one `PersistentSubstrate` and record object identities/hash receipts.
2. A0: activate Model A identity; score frozen battery with real A weights.
3. Transition substrate to Model B identity without replacing substrate-owned ledgers/router/state objects.
4. Append exactly one experiment-issued memory record after the canonical 352-record prefix; freeze its digest.
5. B1: score the identical frozen battery with real B weights.
6. Transition substrate back to exact Model A identity.
7. A2: reload the exact same Model A checkpoint and score the identical battery again.
8. Require Model A checkpoint/parameter identity to match A0 exactly and the canonical 352-record prefix/world identities to remain unchanged.

Do not require cross-device floating-point byte identity unless the locked runtime demonstrates it. Require exact model/checkpoint identity and deterministic receipt structure.

## Task 4: Controls and rollback

**Files:**
- Create: `beastbox/persistent_substrate/real_verification.py`
- Create: `tests/test_persistent_substrate_real_verification.py`

Run:
- A-only schedule control with identical measurement timing/instrumentation and no B exposure;
- no-memory control with zero memory records, same world store, same real model schedule;
- transactional rollback check proving baseline memory/world identities restore after removing only the experiment append.

Verify evidence-chain integrity, read-only world store, stable substrate component identities, final active A identity, and no authority leakage from model object into substrate.

## Task 5: Preregistered classifier and evidence format

**Files:**
- Create: `beastbox/persistent_substrate/real_result.py`
- Create: `tests/test_persistent_substrate_real_result.py`

Allowed result classes:
- `ENGINEERING_REAL_MODEL_SUBSTRATE_VERIFIED_MODEL_EFFECT_NOT_ESTABLISHED`
- `ENGINEERING_REAL_MODEL_SUBSTRATE_VERIFIED_MODEL_EFFECT_OBSERVED_CAUSAL_INTERPRETATION_NOT_ESTABLISHED`
- `ENGINEERING_CONTROL_INCONCLUSIVE`
- `INVALID_REAL_MODEL_SUBSTRATE_RUN`

A passing substrate gate is independent from whether a model effect is observed. Do not upgrade a null/inconclusive result.

## Task 6: Reproducible real execution workflow

**Files:**
- Create: `.github/workflows/persistent-substrate-real-model-v2.yml`
- Create: `scripts/run_persistent_substrate_real_model_v2.py`
- Create: `tests/test_persistent_substrate_real_workflow.py`

Workflow requirements:
- branch-isolated/manual execution;
- restore Model A only from run `33132925890`, verify SHA before use;
- download Model B only at pinned revision, verify full snapshot manifest and weight SHA;
- install frozen inference dependencies;
- no IBM/Rigetti step;
- no training/adaptation;
- minimum permissions and `persist-credentials: false`;
- external Actions pinned to immutable commit SHAs before production merge;
- write evidence only under `evidence/persistent-substrate-real-model-swap-002/<run-id>/`;
- generate checksums before upload;
- preserve raw numeric receipts but no secrets/absolute host paths.

## Task 7: Execute and seal

Run the exact real-weight workflow. Preserve all outputs whether positive, null, inconclusive, or failed. Seal:
- protocol/preregistration;
- model identities and parameter hashes;
- prompt battery/hash;
- A0/B1/A2 numeric scores;
- controls;
- substrate transition/evidence ledger;
- memory/world/state receipts;
- verification report;
- deterministic classification;
- `SHA256SUMS` and manifest.

No factual claim is upgraded until this run succeeds and verification passes.

## Task 8: Production and public-surface hardening

Only after Task 7:
- audit README, product docs, experimental index, package metadata, release docs, and claim-boundary files;
- distinguish historical final-organism real-model swap, historical v1 offline substrate proof, and v2 combined real-model persistent-substrate proof;
- remove/qualify any statement not supported by sealed evidence;
- document stable public API, failure modes, optional ML dependencies, deterministic evidence verification, and support matrix;
- do not call research paths production-grade merely because the product package is production-hardened.

## Task 9: Full verification before merge

Run at minimum:

```bash
python -m pytest tests/test_persistent_substrate_real_*.py -q
python -m pytest -q
make quality
bash scripts/smoke/install-and-run.sh
bash scripts/smoke/sealed-evidence-guard.sh
bash scripts/security-audit.sh
git grep -nE 'optimizer|backward\(|loss\.backward|Trainer\(|\.fit\(' -- beastbox/persistent_substrate scripts/run_persistent_substrate_real_model_v2.py tests/test_persistent_substrate_real_*.py
```

The grep must show no training path in v2 runtime code. Re-verify immutable historical evidence and ensure the original scientific anchor remains unchanged.

## Merge gate

Merge reusable software only after tests/security/smoke pass and sealed v2 evidence validates. Do not rewrite v1 evidence or the final-organism evidence. Public wording must name exactly which experiment supports each claim.