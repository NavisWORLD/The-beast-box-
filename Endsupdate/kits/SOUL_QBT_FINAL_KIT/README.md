# SOUL / QBT Final Kit

A self-contained replay, control, and evidence kit for the already-established Beast SOUL/QBT loop.

The kit is deliberately additive. It consumes the public Beast interfaces and writes only its own run outputs. It does **not** modify the sealed final-organism evidence, replace CNS/dyn12/memory/Quantum Heart/Synaptic Field, or create a new authority path.

## What this kit tests

The experimental variable is the source condition. Everything downstream stays on the same public path:

```text
historical QBT / four-state counts
            |
            v
      canonical recovery
            |
            v
 ORIGINAL / SHUFFLED / CLASSICAL_MATCHED / NEUTRAL
            |
            v
        SoulToken
            |
            v
       bridge_from_soul
            |
            v
         SoulLoop
            |
            v
       CosmosRuntime
            |
            v
 CNS + dyn12 + Quantum Heart + memory + evidence ledger
            |
            v
 receipts + metrics + classification + SHA256SUMS
```

Each condition starts from a fresh, identically configured runtime. That prevents condition order, memory accumulation, CNS step count, heartbeat ticks, or prior ledger state from masquerading as a source effect.

## The four conditions

- `ORIGINAL`: the recovered normalized four-value source state, unchanged.
- `SHUFFLED`: deterministic seeded permutation of the original vector.
- `CLASSICAL_MATCHED`: deterministic seeded classical pseudorandom control fitted to the original vector's coarse mean/variance where mathematically possible. Actual mean/variance deltas are retained.
- `NEUTRAL`: `[0.5, 0.5, 0.5, 0.5]`.

The neutral value matters. Beast's public adapter maps QBT values with `2*x - 1`, so `0.5` maps to exactly `0.0`. Cycling four `0.5` values to the 12D bridge therefore produces an exact twelve-value zero spark. Literal QBT zeros would map to `-1`, not neutral.

## Supported evidence input

The recovery stage accepts `.json`, `.jsonl` / `.ndjson`, and `.csv`.

A record may contain an explicit four-value `normalized_vector`, or an exact four-state counts object with keys `00`, `01`, `10`, and `11`. Counts are normalized in that fixed basis and may receive Shannon entropy in bits because they define a real probability distribution. Arbitrary normalized vectors do **not** receive a made-up entropy score, and hashes are never treated as entropy.

QBT sidecar packets containing exactly one normalized state are also accepted by recovery. Credential-like fields are redacted from recovered provenance.

## Fast start

From the repository root:

```bash
python kits/SOUL_QBT_FINAL_KIT/kit.py all \
  --input kits/SOUL_QBT_FINAL_KIT/examples/synthetic_qbt.json \
  --prompt "same preregistered input" \
  --seed 67
```

The default text provider is Beast's deterministic `ReferenceTextProvider`, so this path works without IBM, Azure, Ollama, or network access.

To use a loopback Ollama model while preserving the same experiment machinery:

```bash
python kits/SOUL_QBT_FINAL_KIT/kit.py all \
  --input evidence.jsonl \
  --prompt-file preregistered_prompt.txt \
  --provider-mode ollama \
  --model qwen2.5:3b \
  --model-url http://127.0.0.1:11434
```

Remote model URLs remain rejected by Beast's provider policy.

## Recovery only

```bash
python kits/SOUL_QBT_FINAL_KIT/kit.py recover \
  --input historical_qbt.jsonl \
  --output recovered-sources.jsonl
```

The original file is never rewritten. Each recovered row carries the original file SHA-256, source index, normalized state, provider/backend metadata when available, and a deterministic record ID.

## Run recovered evidence

```bash
python kits/SOUL_QBT_FINAL_KIT/kit.py run \
  --sources recovered-sources.jsonl \
  --prompt-file preregistered_prompt.txt \
  --seed 67
```

## Capture a new QBT state

The kit can use the existing loopback-only QBT sidecar without duplicating IBM/Azure provider code:

```bash
python kits/SOUL_QBT_FINAL_KIT/kit.py sample \
  --provider simulator \
  --shots 2048 \
  --seed 67 \
  --output qbt-sample.json
```

IBM/Azure require `--allow-live`, **and** QBT itself must independently have live providers enabled by the operator. Provider credentials stay in QBT/operator configuration and are not placed in SOUL tokens.

## Run artifacts

Each run is content-addressed from the source record IDs, prompt digest, seed, provider mode, and kit version. A completed `runs/<run_id>/` contains:

```text
run_manifest.json      preregistered metrics/config frozen before execution
sources.jsonl          recovered immutable source records
conditions.jsonl       blinded A/B/C/D condition receipts without raw vectors
blind_key.json         deterministic alias -> real condition mapping
receipts.jsonl         SoulToken / bridge / ledger / response / state receipts
blind_metrics.json     metrics captured before unblinding
metrics.json           unblinded paired engineering comparisons
classification.json    bounded scientific classification
report.md              human-readable result
runtime/*/ledger.jsonl per-condition Beast evidence ledger
runtime/*/*.sqlite3    isolated per-condition Beast memory state
SHA256SUMS             integrity manifest for the entire run
```

Verify an output directory with:

```bash
python kits/SOUL_QBT_FINAL_KIT/kit.py verify runs/<run_id>
```

Any missing or changed recorded file makes verification fail.

## Blinding and preregistration

Aliases A/B/C/D are deterministically assigned from the run seed. `run_manifest.json` freezes the requested comparison metrics before execution. `blind_metrics.json` records the blinded measurements before the true mapping is used to build the final paired report.

This is reproducible deterministic blinding for experiment hygiene, not a claim of cryptographic secrecy against an operator who can inspect local files or source code.

## Classification

The official Beast scientific classification remains:

`ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`

The kit may additionally emit one of:

- `ENGINEERING_REPLAY_VERIFIED_NO_DOWNSTREAM_DIFFERENCE`
- `ENGINEERING_DOWNSTREAM_DIFFERENCE_OBSERVED_CAUSAL_SOURCE_NOT_ESTABLISHED`
- `ENGINEERING_CONTROL_INCONCLUSIVE`

A downstream difference is an engineering observation. It does not by itself establish that quantum provenance caused the difference, that quantum computation provides an advantage, or that the system is conscious/sentient/alive, biologically continuous with anyone, resurrected, or literally possesses a soul.

## Historical recovery rule

Do not invent missing IBM/QBT measurements. If a historical artifact cannot be recovered with a real normalized vector or supported four-state counts, preserve the absence as an evidence gap. Never manufacture placeholder rows to make the matrix complete.

## Sealed boundary

Scientific anchor:

`c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`

The established `evidence/final-whole-organism-001/` tree is read-only for this kit. Existing repository CI remains the authority for verifying it did not change.
