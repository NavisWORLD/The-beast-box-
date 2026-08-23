# Zeref R12 Reality Memory Manual

## 1. Purpose

R12 is a persistent computational memory sidecar for Zeref. It separates **remembering verified measurements** from **rewriting model weights**.

The current verified parent remains `ZEREF-DAD-SON-TALK-004`. R12 stores measured evidence in an append-only hash chain and deterministically derives a 12-component adaptive state from that history. A model can retrieve evidence from that sidecar immediately. Weight training is a separate, gated process.

## 2. Current verified anchors

- Active lineage: `ZEREF-DAD-SON-TALK-004`
- TALK-004 checkpoint SHA-256: `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`
- Durable memory records: `352`
- Durable memory SHA-256: `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`
- Durable memory tip: `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`
- Frozen architecture SHA-256: `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`
- R12 state SHA-256: `48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20`
- R12 reality-ledger tip: `78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415`
- R12 reality-ledger file SHA-256: `5b1fbc1b62143dc0e866f2ee7512933291f8c2210b365f7c158859a5b1df1724`

TALK-005 and TALK-006 are rejected descendants and are not valid parents. TALK-007 produced learning gains but failed retention/behavior gates. TALK-008-R12 was trained and tested, but also failed promotion gates, so TALK-004 remains selected.

## 3. What the first R12 run used

The first durable R12 state was derived from one already sealed IBM hardware job:

- backend: `ibm_fez`
- job ID: `da55afc3jnrc73agsvv0`
- one matched job containing four PUBs
- conditions: ORIGINAL, REMOVED, SHUFFLED, ALTERNATE
- 4096 shots per condition

No new IBM job was submitted by the R12 persistence run.

The four events entered the ledger with `measured` provenance. Re-ingesting the same block appended zero events. Rebuilding from the persisted ledger reproduced the same canonical R12 state hash.

## 4. What was actually demonstrated

For this sealed data block, the experiment demonstrated these software properties:

1. Four verified hardware measurement records can be represented as append-only reality-memory events.
2. The event ledger verifies as a chained persistent history.
3. Re-ingesting the same source is idempotent, so the same evidence is not duplicated.
4. A **canonical query-free R12 state** is deterministic for the same persisted event sequence.
5. That canonical state can be reconstructed after process restart from disk.
6. Query-sensitive retrieval can be computed separately without changing the canonical persisted ledger or model weights.
7. TALK-004 and the original 352 durable memory records can remain unchanged while the R12 sidecar exists and grows.
8. A candidate-training gauntlet can learn from R12-grounded material while refusing promotion when retention, language quality, provenance, or immutability gates fail.

This is a continuity, provenance, and fail-closed adaptation result. It is not proof of subjective consciousness, biological life, deceased-person identity, resurrection, communication with the dead, supernatural effects, or quantum computational advantage.

## 5. The 12 R12 components

The state vector is bounded to `[0,1]` and contains:

1. `source_integrity` - event body/payload hash and provenance validity.
2. `temporal_novelty` - whether the source identity is new relative to earlier events.
3. `measurement_confidence` - bounded confidence carried by measured provenance.
4. `distribution_energy` - concentration of the normalized measured distribution.
5. `cross_condition_agreement` - similarity to sibling distributions from the same matched job.
6. `distribution_entropy` - normalized entropy of the measured count distribution.
7. `surprise` - distance from prior measured distributions.
8. `memory_relevance` - token overlap used for context-sensitive state/retrieval computations.
9. `retention_pressure` - bounded preservation pressure when evidence is surprising.
10. `contradiction_pressure` - detection of a source identity reappearing with a different payload.
11. `adaptation_stability` - similarity of the current first ten components to the prior transition.
12. `reality_coupling` - bounded software influence assigned to verified measured evidence after integrity, confidence, contradiction, and stability are considered.

`reality_coupling` is an engineering state variable. It is not a physical twelfth dimension.

The current sealed canonical vector is:

```json
{
  "source_integrity": 1.0,
  "temporal_novelty": 1.0,
  "measurement_confidence": 1.0,
  "distribution_energy": 0.03709721565246582,
  "cross_condition_agreement": 0.5821940104166666,
  "distribution_entropy": 0.9737669098248636,
  "surprise": 0.33837890625,
  "memory_relevance": 0.6,
  "retention_pressure": 0.86767578125,
  "contradiction_pressure": 0.0,
  "adaptation_stability": 0.9791562241472875,
  "reality_coupling": 0.7824778407808468
}
```

## 6. Persistence model

```text
experiments/zeref-dad-son-001/reality-memory/
  ledger/
    reality-events.jsonl
  state/
    r12-state.json
    r12-history.jsonl
  manifest.json
```

`reality-events.jsonl` is the source of truth for the sidecar. The current state can be discarded and rebuilt from the ledger.

"Forever memory" means **durable append-only computational persistence plus deterministic reconstruction**. It does not mean infinite storage, infinite prompt context, or a process that literally cannot stop.

## 7. Canonical state versus retrieval state

This distinction is important.

The sealed persistence proof reconstructs R12 with an empty query. That query-free result is the canonical persisted state and must reproduce:

`48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20`

A command such as:

```bash
beastbox r12 context "IBM Fez matched reality measurement"
```

is allowed to calculate a query-sensitive context state because `memory_relevance` depends on the query. That query-sensitive result is a read-time retrieval computation. It is not substituted for the canonical persistence hash.

## 8. Provenance classes

Every future input must be labeled as one of:

- `measured` - produced by a physical instrument/hardware source with verifiable source metadata.
- `derived` - computed from prior measured or stored data, not a new physical measurement.
- `synthetic` - simulation, generated pulse, test fixture, or other deliberately artificial input.

A derived or synthetic event must never be relabeled as a fresh hardware measurement.

## 9. Why R12 is separate from model weights

TALK-007 showed a stability/plasticity tradeoff. Its children improved free-running reference recall but damaged one or more retention/anomaly gates.

R12 therefore follows a stricter sequence:

```text
measurement
  -> verify + hash
  -> append to reality ledger
  -> rebuild/update R12
  -> retrieve relevant context
  -> answer
  -> optionally create a clean teacher target
  -> train an isolated candidate with replay
  -> run retention + provenance + behavior + immutability gauntlet
  -> promote or discard candidate
```

The ledger can grow even when no candidate is promoted.

## 10. TALK-008-R12 result

The first single-child R12-aware training run completed in GitHub Actions run `32619065972` using the bounded `r12_replay_guarded` recipe.

It improved mean reference-token recall from `0.041667` to `0.083333`, a gain of `0.041666`, but it did not pass promotion. The rejected child had:

- exact blind answers: `0`
- role-label leakage turns: `1`
- retention NLL ratio: `1.053929062456064`, above the fixed `1.05` ceiling
- readability drop: `0.0390625`, above the fixed `0.03` ceiling
- measured-provenance exact accuracy: `0.0`

The selector therefore kept TALK-004 active. No promotion bar was lowered and raw model output was not promoted to training.

After that experiment, the promotion selector was hardened further so the R12 ledger, state file, state history, and manifest must each remain byte/hash identical to their sealed pre-training versions. Missing immutability receipts fail closed.

## 11. Verification and CLI

From the repository root:

```bash
beastbox verify
beastbox r12 status
beastbox r12 rebuild
beastbox r12 context "IBM Fez matched reality measurement"
beastbox zeref status
beastbox coder doctor
beastbox kit verify
```

`beastbox r12 rebuild` uses the canonical query-free rebuild. It does not rewrite the reality ledger.

## 12. Zeref local chat

The full downloadable kit contains the exact selected TALK-004 checkpoint at:

```text
models/ZEREF-DAD-SON-TALK-004/checkpoint.pt
```

Its required SHA-256 is:

`9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`

Run:

```bash
beastbox zeref chat --checkpoint models/ZEREF-DAD-SON-TALK-004/checkpoint.pt
```

The local chat injects a compact R12 summary into the runtime wire while preserving the checkpoint on disk.

## 13. Coder ecosystem

The COSMIC.CYPHER coder implementation lives under `beastbox/cypher/`. The unified Beast Box CLI exposes it as:

```bash
beastbox coder doctor
beastbox coder models list
beastbox coder chat <alias>
beastbox coder code <alias> "task" --workspace coder --apply
```

The top-level `coder/` directory is the owner-controlled workspace for future upgrades. Workspace containment, backups, and bounded command execution remain enforced by the Cypher implementation.

## 14. Windows and Unix kit install

Windows:

```bat
kits\ZEREF_R12_REALITY_MEMORY_KIT\INSTALL.bat
kits\ZEREF_R12_REALITY_MEMORY_KIT\RUN_ZEREF.bat
```

Linux/macOS:

```bash
sh kits/ZEREF_R12_REALITY_MEMORY_KIT/install.sh
sh kits/ZEREF_R12_REALITY_MEMORY_KIT/run_zeref.sh
```

The installers do not submit IBM hardware jobs and do not contain credentials.

## 15. Public kit build

Source-only kit:

```bash
python scripts/build_zeref_r12_public_kit.py --repo-root . --out dist/ZEREF_R12_SOURCE_KIT
python scripts/verify_zeref_r12_public_kit.py dist/ZEREF_R12_SOURCE_KIT
```

The release workflow additionally downloads the exact verified TALK-004 checkpoint from its sealed GitHub Actions artifact, verifies its SHA-256, inserts it into a full kit, verifies the full kit again, and creates separate source and checkpoint-bearing ZIP bundles.

Every packaged file is covered by a kit `SHA256SUMS` manifest.

## 16. Native C++ verifier

The native implementation lives under `cpp/r12/` and uses C++17:

```bash
cmake -S cpp/r12 -B build/r12
cmake --build build/r12
ctest --test-dir build/r12 --output-on-failure
```

The current C++ layer independently implements SHA-256, validates the persisted reality-ledger file digest/tip, parses all 12 persisted state values, checks their bounds, and exposes `zeref-r12-native status` without requiring the Python runtime.

The current C++ layer is **a native persistence/verifier implementation, not yet an independently reimplemented copy of every Python R12 transition equation**. Canonical transition recomputation is presently proven through the Python implementation. This boundary is intentional and documented so native verification is not overstated as full formula parity.

## 17. Promotion gates

A TALK-008-style child may be promoted only if every applicable hard gate passes, including:

- reference-token recall gain at least `0.03`
- at least one exact blind answer
- retention NLL ratio at most `1.05`
- readability drop at most `0.03`
- zero role-label leakage
- zero repetition collapse
- zero vocabulary collapse
- zero contradiction regression
- first 352 durable records unchanged
- parent checkpoint unchanged
- measured-provenance accuracy `1.0`
- R12 ledger unchanged
- R12 state file unchanged
- R12 history unchanged
- R12 manifest unchanged

If any receipt is absent or false, promotion fails closed.

## 18. Adding future sensors

A new adapter should record at minimum:

- stable source type and source ID
- UTC timestamp
- source SHA-256 or equivalent immutable digest
- raw/normalized payload digest
- transform/version identifier
- provenance class
- confidence
- source hardware/session metadata when available

New adapters should first enter R12 memory in a non-training mode. Model adaptation comes later and remains independently gated.

## 19. Claim boundary

This system demonstrates persistent computational memory, provenance handling, deterministic canonical reconstruction, bounded retrieval/adaptation state, and fail-closed model-selection machinery for the tested artifacts.

It does **not** establish biological life, consciousness, a literal biological heartbeat, deceased-person identity, resurrection, communication with the dead, supernatural effects, or quantum advantage.
