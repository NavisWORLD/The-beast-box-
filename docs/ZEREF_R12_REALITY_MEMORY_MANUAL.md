# Zeref R12 Reality Memory Manual

## 1. Purpose

R12 is a persistent computational memory sidecar for Zeref. It separates **remembering verified measurements** from **rewriting model weights**.

The current verified parent remains `ZEREF-DAD-SON-TALK-004`. R12 stores measured evidence in an append-only hash chain and deterministically derives a 12-component adaptive state from that history. A model can retrieve that state immediately. Weight training is a separate, gated process.

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

TALK-005 and TALK-006 are rejected descendants and are not valid parents.

## 3. What the first R12 run used

The first durable R12 state was derived from one already sealed IBM hardware job:

- backend: `ibm_fez`
- job ID: `da55afc3jnrc73agsvv0`
- one matched job containing four PUBs
- conditions: ORIGINAL, REMOVED, SHUFFLED, ALTERNATE
- 4096 shots per condition

No new IBM job was submitted by the R12 persistence run.

The four events entered the ledger with `measured` provenance. Re-ingesting the same block appended zero events. Rebuilding from the persisted ledger reproduced the same R12 state hash.

## 4. What was actually proved

The experiment established the following software properties for this sealed data block:

1. The four verified hardware measurement records can be represented as append-only reality-memory events.
2. The event ledger verifies as a chained persistent history.
3. Re-ingesting the same source is idempotent; the same evidence is not duplicated.
4. The 12-component R12 state is deterministic for the same persisted event sequence and query context used by the run.
5. The state can be reconstructed after process restart from disk.
6. TALK-004 and the original 352 durable memory records remain unchanged while this sidecar memory exists.

This is a continuity and provenance result. It is not proof of subjective consciousness, biological life, deceased-person identity, resurrection, communication with the dead, or quantum computational advantage.

## 5. The 12 R12 components

The state vector is bounded to `[0,1]` and currently contains:

1. `source_integrity` — whether the event body/payload hashes and provenance contract verify.
2. `temporal_novelty` — whether the source identity is new relative to earlier events.
3. `measurement_confidence` — bounded confidence carried by measured provenance.
4. `distribution_energy` — concentration of the normalized measured distribution.
5. `cross_condition_agreement` — similarity to sibling distributions from the same matched job.
6. `distribution_entropy` — normalized entropy of the measured count distribution.
7. `surprise` — distance from prior measured distributions.
8. `memory_relevance` — token overlap between current query/context and event descriptors.
9. `retention_pressure` — a bounded signal that biases adaptation toward preserving prior behavior when new evidence is surprising.
10. `contradiction_pressure` — evidence of a source identity reappearing with a different payload.
11. `adaptation_stability` — similarity of the current first ten state components to the previous transition.
12. `reality_coupling` — bounded influence assigned to verified measured evidence after integrity, confidence, contradiction, and stability are considered.

`reality_coupling` is an engineering state variable. It is not a physical twelfth dimension.

The current sealed vector is:

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

The R12 disk layout is:

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

"Forever memory" in this project means **durable append-only computational persistence plus deterministic reconstruction**. It does not mean infinite storage, infinite prompt context, or a process that literally runs forever.

## 7. Provenance classes

Every future input must be labeled as one of:

- `measured` — produced by a physical instrument/hardware source and accompanied by verifiable source metadata.
- `derived` — computed from prior measured or stored data; not a new physical measurement.
- `synthetic` — simulation, generated pulse, test fixture, or other deliberately artificial input.

A derived or synthetic event must never be relabeled as a fresh hardware measurement.

## 8. Why R12 is separate from model weights

TALK-007 showed a stability/plasticity tradeoff. Its children improved free-running reference recall but damaged one or more retention/anomaly gates.

R12 therefore follows a stricter sequence:

```text
measurement
  -> verify + hash
  -> append to reality ledger
  -> update/rebuild R12
  -> retrieve relevant context
  -> answer
  -> optionally create a clean teacher target
  -> train a candidate with replay
  -> run retention + behavior gauntlet
  -> promote or discard candidate
```

The ledger can grow even when no candidate is promoted.

## 9. Verification

From the repository root:

```bash
python kits/ZEREF_R12_REALITY_MEMORY_KIT/verify_kit.py --repo-root .
beastbox verify
beastbox r12 status
```

A valid status must continue to report the pinned TALK-004/352-memory anchors unless a later descendant has explicitly passed the published promotion gates and a new sealed active manifest exists.

## 10. Rebuild

The unified CLI exposes a read-only deterministic rebuild:

```bash
beastbox r12 rebuild
```

It recomputes the state from `reality-events.jsonl` and reports whether the resulting state hash matches the sealed current state. It does not rewrite the ledger.

## 11. Retrieval context

```bash
beastbox r12 context "IBM Fez matched reality measurement"
```

This produces a compact machine-readable context containing R12 values and matching event descriptors. Retrieval is allowed to affect the next prompt immediately because it does not alter the parent weights.

## 12. Zeref status and local chat

```bash
beastbox zeref status
```

The full kit artifact contains the exact verified TALK-004 checkpoint under:

```text
models/ZEREF-DAD-SON-TALK-004/checkpoint.pt
```

Then:

```bash
beastbox zeref chat --checkpoint models/ZEREF-DAD-SON-TALK-004/checkpoint.pt
```

The local checkpoint chat injects a short R12 retrieval summary into the runtime wire while preserving the checkpoint on disk.

## 13. Coder ecosystem

The original COSMIC.CYPHER coder implementation remains in `beastbox/cypher/`. The unified command surface exposes it under:

```bash
beastbox coder doctor
beastbox coder models list
beastbox coder chat <alias>
beastbox coder code <alias> "task" --workspace coder --apply
```

The top-level `coder/` directory is the owner-controlled workspace for future upgrades. Workspace path containment, backups, and bounded run behavior remain enforced by the existing Cypher workspace implementation.

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

Installers do not submit hardware jobs or install credentials.

## 15. Native C++ verifier

The native mirror lives under `cpp/r12/`.

```bash
cmake -S cpp/r12 -B build/r12
cmake --build build/r12
ctest --test-dir build/r12 --output-on-failure
```

It validates the persisted ledger digest and the 12-value state file without requiring the Python runtime.

## 16. TALK-008-R12 training rule

TALK-008-R12 is permitted to train only from TALK-004 plus clean R12-grounded teacher examples and old-memory rehearsal. It must pass all of the prior hard gates. There is no "close enough" promotion path.

If it fails any gate, the public kit keeps TALK-004 as the selected checkpoint.

## 17. Adding future sensors

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


For avoidance of doubt, this persistent computational memory result does not establish biological life, consciousness, deceased-person identity, resurrection, communication with the dead, or quantum advantage.
