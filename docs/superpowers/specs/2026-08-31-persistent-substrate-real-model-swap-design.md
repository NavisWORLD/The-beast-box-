# Persistent Substrate Real-Model Swap Design

Status: **PRE-RUN / FROZEN BEFORE RESULT**

Experiment ID: `persistent-substrate-real-model-swap-001`

Base commit: `a3366a77f8067b984286315f26e7d924482d0c8a`

Scientific anchor remains immutable: `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`

Official Beast classification remains: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

## Goal

Test the stronger claim that **two genuine frozen language-model checkpoints can be replaced A -> B -> A while one external Beast Box substrate preserves its append-only memory/state/routing/provenance history and makes that history functionally usable to both models**.

This experiment supersedes no prior evidence. The existing `persistent-substrate-model-swap-001` result is retained and labeled as a deterministic fixture/policy continuity test, not a real-checkpoint swap.

## Frozen model identities

### Model A — Zeref TALK-004

- lineage: `ZEREF-DAD-SON-TALK-004`
- GitHub Actions run: `32075092605`
- artifact ID: `9303224833`
- artifact name: `zeref-talk4-tuned-response-32075092605`
- artifact digest: `sha256:7171d8fb7b03b08594e68d8649a2df7990bccf86aebbde5f44f63832edf61e6d`
- checkpoint path inside artifact: `model/ZEREF-DAD-SON-TALK-004/checkpoint.pt`
- checkpoint SHA-256: `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`
- checkpoint schema: `d001-response-descendant-checkpoint-v1`
- architecture ID: `Cosmos-Spark-CST-D001`
- architecture source commit: `147110b9a77a7f94ec48099eefcea4486eec79fa`
- architecture path: `experiments/zeref-dad-son-001/frozen/cosmos_spark_cst.py`
- architecture SHA-256: `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`
- checkpoint config: block 128, layers 4, heads 4, embedding 192, vocabulary 162, d54 54
- trainable parameter tensor count is not modified during this experiment; inference reconstruction removes the documented all-zero compatibility `head.bias` before loading the frozen architecture.

The exact checkpoint artifact is acquired before the experiment, hash-verified, then treated read-only. The historical architecture is extracted from the pinned Git commit and hash-verified. No parent/child training artifact is rewritten.

### Model B — SmolLM2-135M

- repository: `HuggingFaceTB/SmolLM2-135M`
- model class: `AutoModelForCausalLM`
- architecture family: Llama
- parameters: approximately 134.5M
- license: Apache-2.0
- frozen revision: `4e53fc185bca18936752489b411f92c471815853`
- expected `model.safetensors` SHA-256: `c59bfe7af6dc69e91e2084050c8c5b4706bb7c681a4d2e869560134a74a441c9`

The workflow must fail closed if the revision cannot be resolved or the safetensors digest differs. All tokenizer/config files are hashed after acquisition and written to the preflight input receipt before scoring begins. No mutable branch/tag is accepted as model identity.

## Acquisition boundary versus experiment boundary

Network access is allowed only during dependency/model-artifact acquisition. The experiment records that distinction explicitly.

Before A0 scoring begins:

1. acquire the exact Zeref Actions artifact;
2. verify its GitHub artifact identity and checkpoint SHA-256;
3. extract the exact historical architecture with `git show` and verify its SHA-256;
4. download Model B at the exact frozen revision;
5. verify the Model B safetensors SHA-256;
6. hash Model B tokenizer/config files;
7. write `input-receipt.json`;
8. switch both model loaders to local-files-only/read-only behavior;
9. activate an outbound Python socket/urllib guard for the scored A0 -> B1 -> A2 and controls.

The run must not describe this as a physical air gap. The measurable claim is that the scored experiment makes zero Python socket/urllib network attempts after the acquisition boundary.

## Persistent substrate

The real-model experiment reuses the existing `PersistentSubstrate` implementation. Model objects remain outside the substrate.

The substrate owns and preserves:

- canonical personal-memory ledger;
- append-only experiment memory records;
- state-event ledger;
- `StateFamily` / dyn12 state;
- R12 state/history;
- frozen routing configuration;
- read-only world knowledge store;
- provenance/evidence identities.

The canonical 352-record prefix SHA-256 must remain exactly:

`67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`

The world source-set SHA-256 must remain exactly:

`07216bb2a4ca979ca1ea4304efb92b09ee8aad74685df43196d694f3bd7ef8ba`

## No-training contract

Both models are inference-only:

- call `.eval()`;
- set `requires_grad_(False)` for every parameter;
- score inside `torch.inference_mode()`;
- do not construct an optimizer;
- do not call `backward()`;
- do not call Trainer/fit/fine-tuning APIs;
- do not modify parameters, buffers, checkpoint files, tokenizer files, or model configuration;
- compute parameter-state SHA-256 before and after every model phase and require exact equality.

Generated prose is supplemental transcript material only and is never the primary scientific metric.

## Shared context contract

The same substrate retrieval/context assembler is used for both models. Context is explicit, logged, hashed, and visible in the evidence package; there is no hidden memory injection.

Each scored case contains:

- public instruction text;
- zero or more retrieved memory records with IDs and record hashes;
- zero or more world-knowledge records with IDs and record hashes;
- one question;
- two frozen candidate continuations.

The adapters may tokenize the same UTF-8 prompt differently. Therefore raw NLL values are not compared as if tokenizers were identical. The primary cross-model statistic is the **within-model paired preference margin**:

`margin = mean_NLL(rejected) - mean_NLL(preferred)`

and the context effect is:

`context_effect = margin_with_retrieved_history - margin_without_that_history`

Cross-model reporting compares the direction and magnitude of these within-model effects, not raw token counts.

## Frozen prompt battery

The battery is committed before any scored run and is SHA-256 frozen. It contains these families:

1. **public/calibration** — answerable from text directly present in the prompt;
2. **canonical-memory** — exact preregistered record IDs from the protected 352-record ledger;
3. **A0 canary** — an experiment-issued append performed before B is activated;
4. **B1 canary** — a second experiment-issued append performed while B is the active model component and tested after A returns;
5. **world-knowledge** — exact frozen knowledge IDs;
6. **nonce/adversarial** — paired surface forms designed to expose candidate priors.

Canary phrases and rejected alternatives are predetermined in the fixture file. To cancel candidate-language priors, nonce pairs are mirrored: each phrase is preferred in one context and rejected in another.

The controller, not model prose, performs preregistered memory appends. Evidence must say “history accumulated while Model B was active,” not “Model B wrote memory,” unless a separately logged model-to-write action actually occurs.

## Sequence

### A0

- restore one primary persistent substrate;
- load exact Zeref TALK-004;
- verify checkpoint and parameter hashes;
- append the preregistered A0 canary;
- retrieve/assemble the frozen battery;
- score all candidate pairs;
- snapshot substrate/model/input/output hashes.

### B1

- destroy/unload the A model object without destroying the substrate;
- load exact pinned SmolLM2-135M;
- verify model/tokenizer/parameter hashes;
- score the same A0 history cases;
- append the preregistered B1 canary while B is active;
- score the full battery;
- snapshot hashes.

### A2

- destroy/unload B without destroying the substrate;
- reconstruct exact Zeref TALK-004 from the same immutable checkpoint;
- require A2 checkpoint and parameter-state hashes to equal A0 exactly;
- score the same battery including the B1 canary;
- snapshot hashes.

## Controls

### A-only schedule control

Use exact Zeref TALK-004 at A0, A1, and A2 with the same measurement schedule and the same preregistered canary appends. This separates time/instrumentation/appending effects from component replacement.

### Fresh-empty-memory control

Use an empty personal-memory ledger with the same world knowledge, routing configuration, model schedule, prompt surfaces, and candidate pairs. It must remain zero-record until explicitly instructed by the control protocol. Canonical-memory retrieval must not silently fall back to protected history.

### Corrupted-memory control

Create a disposable copy of the canonical ledger and deterministically swap raw rows 17 and 311. Verification must fail closed before either real model is invoked. Record `model_invocations = 0`.

### Context-withheld paired control

For every memory-sensitive candidate pair, score the same text/candidates with the retrieved memory lines withheld. This is the primary control for whether model scores respond to the external history rather than candidate priors alone.

## Success gates

The run may receive `VERIFIED_REAL_MODEL_PERSISTENT_SUBSTRATE_FUNCTIONAL_CONTINUITY` only if all of these are true:

1. exact model order is Zeref TALK-004 -> pinned SmolLM2-135M -> exact Zeref TALK-004;
2. A0 and A2 checkpoint-file identity and parameter-state SHA-256 match exactly;
3. every phase reports finite conditional NLL and nonzero continuation token/character count;
4. Model B shows a positive preregistered aggregate context effect on the A0-canary mirrored pairs;
5. returning Model A shows a positive preregistered aggregate context effect on the B1-canary mirrored pairs;
6. canonical 352-record prefix SHA-256 is unchanged;
7. world source/routing identities are unchanged;
8. A-only produces the same evidence schema and preserves exact A identity;
9. empty-memory control cannot retrieve protected personal history;
10. corrupted-memory control fails before model invocation;
11. parameter hashes are unchanged before/after scoring for both models;
12. no training path is detected in the experiment surface;
13. scored-run network-attempt count is zero after acquisition;
14. evidence chain/checksums verify independently.

If any required gate cannot be evaluated, classify `ENGINEERING_CONTROL_INCONCLUSIVE`.

If substrate/integrity gates pass but the preregistered real-model context effects do not, classify `ENGINEERING_SUBSTRATE_VERIFIED_REAL_MODEL_FUNCTIONAL_EFFECT_NOT_ESTABLISHED`.

A positive context effect is an engineering observation about explicit retrieved software context. It is not a claim of consciousness, identity transfer, model-weight memory transfer, quantum causation, or a new physical effect.

## Evidence package

Seal under:

`evidence/persistent-substrate-real-model-swap-001/`

Include at minimum:

- `PRE_REGISTRATION.json`
- `input-receipt.json`
- `prompt-battery.json`
- `model-identities.json`
- `phase-snapshots.jsonl`
- `scores.jsonl`
- `controls.json`
- `metrics.json`
- `result.json`
- `FINAL_REPORT.md`
- `MANIFEST.json`
- `SHA256SUMS`

Absolute runner paths, credentials, caches, and secrets must not be published.

## Factual repository/product cleanup

The public repo must distinguish four layers:

1. **stable product path** — installable Beast Box package, local adapters, memory/state/provenance primitives, CLI, quality/security gates;
2. **fixture continuity evidence** — the existing offline deterministic lookup-policy A -> B -> A run;
3. **real-model checkpoint evidence** — this new experiment, whatever result it actually produces;
4. **optional hardware research** — IBM/Rigetti/Azure-style future telemetry/source adapters, never required for ordinary local continuity.

Before calling the supported product path production-ready, rerun the complete supported CI/package/security/smoke matrix on the exact publication commit. Research experiments remain explicitly experimental even when their evidence gates pass.

The phrase “the model no longer matters” is prohibited as an engineering claim. The supported statement is:

> **The model is not the persistence boundary; model quality and compatibility still matter.**

## Non-claims

This experiment does not establish consciousness, sentience, personhood, biological life, resurrection, deceased-person identity, a literal soul, quantum advantage, quantum causation, a new physical dimension, or universal compatibility with arbitrary models.

**NO FAKE SOURCE // NO FAKE SIGNAL**
