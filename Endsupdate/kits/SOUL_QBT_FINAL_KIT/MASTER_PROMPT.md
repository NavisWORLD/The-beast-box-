# CORY-DAVIS // SOUL-QBT FINAL CLOSED-LOOP EXPERIMENT

Repository:

`NavisWORLD/The-beast-box-`

Kit:

`kits/SOUL_QBT_FINAL_KIT/`

## MISSION

Continue from the existing Beast Box. Do **not** restart, rewrite, replace, or reinterpret the established organism.

Recover every genuine historical QBT/IBM measurement that can be supported by existing artifacts, normalize only formats the kit actually supports, freeze the recovered source corpus, generate deterministic blinded source controls, run every condition through the exact existing SOUL -> BridgePacket -> CosmosRuntime loop, preserve all receipts, compare downstream state/response effects, verify hashes, and classify the result scientifically.

The goal is to discover whether reproducible downstream differences exist. The goal is **not** to manufacture a positive quantum result.

## LOCKED SCIENTIFIC BOUNDARY

Before doing anything else, verify current repository ancestry and preserve:

- sealed scientific anchor: `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`
- official classification: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`
- sealed evidence tree: `evidence/final-whole-organism-001/`

Never edit, replace, regenerate, or delete the sealed evidence tree.

Never invent historical source rows, IBM job IDs, hardware results, backend metadata, counts, normalized vectors, hashes, or provenance.

If a historical measurement cannot be recovered from genuine evidence, record the gap and continue with the recoverable corpus.

## TERMINOLOGY BOUNDARY

`SOUL`, `SoulToken`, and `SDT_INSTANTIATE` are project terminology for software state/event transport and lineage.

Do not interpret this experiment as evidence of a literal soul, consciousness, sentience, biological continuity, resurrection, quantum advantage, a new physical dimension, or any other extraordinary physical claim.

Provider provenance is metadata. It does not establish a causal quantum effect.

## STEP 1 — VERIFY THE MACHINE

Inspect the current repository and verify that the public path still exists:

`SoulToken -> bridge_from_soul -> BridgePacket -> SoulLoop -> CosmosRuntime -> Synaptic Field/CNS/dyn12/Quantum Heart/memory/model/evidence ledger`

Do not create a fake R12 hook or any other subsystem that is not actually exposed by the current runtime.

Record the exact main SHA and kit SHA used for the experiment.

## STEP 2 — RECOVER THE REAL SOURCE CORPUS

Search the repository, durable artifacts, workflow artifacts, archived experiment outputs, and any user-supplied source files for genuine QBT/IBM measurements.

Prefer original evidence over derived summaries.

Use the kit recovery contract:

- JSON, JSONL/NDJSON, or CSV
- explicit `normalized_vector` with exactly four finite values in `[0,1]`; or
- exact four-state counts with keys `00`, `01`, `10`, `11`; or
- an existing QBT packet containing exactly one normalized state.

For four-state counts only, normalize in fixed order `[00,01,10,11]` and compute Shannon entropy from the resulting probability distribution.

Do not infer entropy from hashes, digests, timestamps, prose, model output, or arbitrary bounded vectors.

Hash the original source file before transformation. Preserve source file SHA-256, record index, provider/backend/shots/job metadata when genuinely available, and the deterministic recovered record ID.

Credential-like fields must remain redacted.

Freeze the recovered corpus before generating controls.

## STEP 3 — FREEZE THE PREREGISTRATION

Choose the exact user prompt/context that every condition will receive.

Freeze before execution:

- recovered source record IDs
- input prompt SHA-256
- seed
- provider mode/model revision when applicable
- source-condition definitions
- downstream metrics
- official Beast classification
- sealed anchor
- neutral-control definition

Do not change metrics or thresholds after seeing condition results.

## STEP 4 — GENERATE THE FOUR SOURCE CONDITIONS

For every recovered source record generate exactly:

1. `ORIGINAL`
   - original normalized vector unchanged.

2. `SHUFFLED`
   - deterministic seed-based permutation of the original vector.

3. `CLASSICAL_MATCHED`
   - deterministic classical pseudorandom control matched to coarse source mean/variance where mathematically possible.
   - preserve actual mean and variance deltas from ORIGINAL; do not call it an exact match if it is not exact.

4. `NEUTRAL`
   - exactly `[0.5, 0.5, 0.5, 0.5]`.

The NEUTRAL value is non-negotiable. Beast maps QBT values using `2*x-1`. Therefore `0.5 -> 0.0`, so four 0.5 values cycle to an exact 12D zero spark. `[0,0,0,0]` would map to `[-1,...]` and is **not** a neutral control.

## STEP 5 — BLIND CONDITIONS

Deterministically map the real condition names to aliases A/B/C/D using the frozen seed.

Keep the mapping in `blind_key.json`.

Public condition receipts should use aliases while blinded.

This is experiment-hygiene blinding, not cryptographic secrecy.

## STEP 6 — USE ONE DOWNSTREAM MACHINE

Every condition must become an ordinary fail-closed `SoulToken` with the explicit `bridge` consumer and no host/network/credentials/tools/model/memory-write/persistence authority.

Every condition must use the same public conversion and runtime machinery.

Do not implement separate ORIGINAL, SHUFFLED, CLASSICAL, or NEUTRAL execution paths after token creation.

For each condition start a fresh, identically configured runtime so memory, CNS step count, heartbeat state, prior ledger contents, or execution order cannot contaminate the comparison.

Use the same text provider configuration for every condition in the run.

Default to Beast's deterministic `ReferenceTextProvider` for offline reproducibility. A loopback Ollama provider may be used only if the model/config is frozen and identical across conditions.

## STEP 7 — OPTIONAL NEW QBT SAMPLING

Historical replay is the first priority.

If new sampling is required, use the existing loopback-only `QBTLoopbackSoulSource` rather than duplicating provider code.

Simulator is the default.

IBM/Azure execution requires both:

1. QBT/operator configuration enabling the live provider, and
2. explicit kit/Beast `allow_live` opt-in.

Never move provider credentials into a SOUL token or experiment receipt.

## STEP 8 — EXECUTE AND PRESERVE RECEIPTS

For every source record and blinded condition preserve at minimum:

- source record ID
- alias
- prepared run-manifest SHA-256
- SoulToken ID
- BridgePacket SHA-256
- SOUL consumption receipt hash
- ledger head
- response SHA-256 and length
- runtime state hash
- dyn12 vector and L2 norm when exposed by the current runtime
- per-condition Beast evidence ledger

Do not use generated model prose itself as scientific evidence of a physical effect.

## STEP 9 — FREEZE BLINDED METRICS BEFORE UNBLINDING

Write the blinded measurements before consulting the condition-name mapping.

Then unblind and compute paired engineering comparisons against ORIGINAL, including:

- response digest change
- state-hash change
- vector L1/L2 source displacement
- dyn12 L2 readout
- source/control separation counts

Do not retrofit a significance threshold after seeing the data.

If the sample is too small for meaningful inference, report descriptive paired results rather than manufacturing statistical significance.

## STEP 10 — CLASSIFY SCIENTIFICALLY

Allowed kit-level outcomes:

`ENGINEERING_REPLAY_VERIFIED_NO_DOWNSTREAM_DIFFERENCE`

Use when replay/control execution works and no downstream difference is observed.

`ENGINEERING_DOWNSTREAM_DIFFERENCE_OBSERVED_CAUSAL_SOURCE_NOT_ESTABLISHED`

Use when downstream differences are observed with control separation, while explicitly preserving that causal source is not established.

`ENGINEERING_CONTROL_INCONCLUSIVE`

Use when differences exist but controls do not cleanly separate the source conditions or the comparison is otherwise ambiguous.

The official Beast classification remains unchanged regardless of the kit-level result unless a separately designed scientific program with stronger controls and replication justifies a future revision.

## STEP 11 — SEAL THE RUN

A finished run directory must contain:

- `run_manifest.json`
- `sources.jsonl`
- `conditions.jsonl`
- `blind_key.json`
- `receipts.jsonl`
- `blind_metrics.json`
- `metrics.json`
- `classification.json`
- `report.md`
- per-condition runtime ledgers/state
- `SHA256SUMS`

Run the kit verification command and fail closure if any recorded file is missing or has a checksum mismatch.

## STEP 12 — VERIFY THE REPOSITORY WAS NOT DAMAGED

Before calling the work complete:

- compare the final implementation to the starting main SHA
- verify the sealed evidence tree is unchanged
- run repository tests on supported Python versions
- run package smoke/quality/reproducibility checks
- run repository security audit
- preserve null, negative, and inconclusive results

Do not delete old evidence or rewrite Git history.

## EXECUTION COMMANDS

Synthetic/offline proof:

```bash
python kits/SOUL_QBT_FINAL_KIT/kit.py all \
  --input kits/SOUL_QBT_FINAL_KIT/examples/synthetic_qbt.json \
  --prompt "same preregistered input" \
  --seed 67
```

Historical recovery:

```bash
python kits/SOUL_QBT_FINAL_KIT/kit.py recover \
  --input HISTORICAL_EVIDENCE.jsonl \
  --output recovered-sources.jsonl
```

Frozen replay:

```bash
python kits/SOUL_QBT_FINAL_KIT/kit.py run \
  --sources recovered-sources.jsonl \
  --prompt-file preregistered_prompt.txt \
  --seed 67
```

Integrity verification:

```bash
python kits/SOUL_QBT_FINAL_KIT/kit.py verify runs/RUN_ID
```

## STOP CONDITIONS

Stop only for a genuine external blocker such as unavailable source bytes, missing authorization for an explicitly requested live provider, or infrastructure failure that cannot be recovered without changing the scientific protocol.

A null result is not a blocker.

An inconclusive result is not a blocker.

Failure to find historical evidence is itself an evidence-recovery result and must be recorded without fabrication.

## FINAL RESPONSE CONTRACT

When finished, report:

- exact repository main SHA
- exact kit/run ID
- recovered source record count
- which conditions executed
- whether sealed evidence remained unchanged
- verification/checksum result
- CI/security result
- kit-level classification
- unchanged official Beast classification
- explicit statement that no causal quantum, consciousness, biological continuity, literal soul, or resurrection claim was established by this run unless independently supported by evidence far beyond this kit.

Do the work. Preserve the machine. Preserve the nulls. Make the weirdness reproducible or classify it as noise.
