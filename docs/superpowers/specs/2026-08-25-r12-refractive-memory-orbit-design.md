# R12 Refractive Memory Orbit v2

## Purpose

Fix the demonstrated TALK-004 memory-starvation failure by replacing flat lexical-only recall with a bounded spatial retrieval layer driven by the existing 12D/42D/54D state family, while preserving TALK-004 weights and the canonical 352-record ledger byte-for-byte.

The user term `LIVE_SOUL_SOURCE` refers only to a computational lineage/state source stream. It is not a claim of biological life, consciousness, resurrection, communication with the dead, or a literal soul.

## Existing failure

The current `ReconciliationMemory.search()` score is `0.85 * lexical_cosine + 0.15 * recency`. Snapshot records can therefore be appended successfully but omitted from the 128-character active model context when prompt wording differs from snapshot wording. The previous instrumented TALK-004 run reproduced exactly this failure.

## Architecture

### 1. R12 adaptive refractive state

Reuse the existing R12 vector and keep its dimensional contract unchanged. Coordinate 12 remains `reality_coupling`, but in retrieval it also acts as a bounded refractive coefficient `rho_t` in `[0,1]`.

Let the current normalized R12 vector be:

`u_t = normalize(R12_t)`

Let `q_t` be the deterministic 12D query position. Reflect it about the current R12 axis:

`q_mirror = 2 * dot(q_t, u_t) * u_t - q_t`

Then compute the refracted query:

`q_star = normalize((1-rho_t) * q_t + rho_t * q_mirror)`

A low `rho_t` leaves retrieval close to the ordinary semantic query direction. A high `rho_t` bends retrieval toward the current verified R12 state. Contradiction and instability cannot increase coupling because the existing R12 transition already bounds measured coupling by integrity, confidence, contradiction, and adaptation stability.

### 2. Orbital/spatial memory geometry

Every memory receives a deterministic 12D spatial position derived from:

- memory identity and content digest,
- current R12 sequence,
- existing dyn12 cyclic forcing,
- retained Hebbian association/salience structure.

The orbital component is a software phase/topology mechanism, not an astronomical or physical claim. It uses the repository's existing dyn12 phase constant and bounded dynamics so identical inputs and sequence values reproduce identical positions.

### 3. Retrieval score

Candidate memories are scored from independent bounded terms:

- spatial proximity to `q_star`,
- ordinary lexical relevance,
- Hebbian association pull,
- bounded recency,
- source/provenance integrity.

No single term may silently overwrite another. Exact weights are implementation constants frozen before the paired run and covered by tests. The current lexical path remains available as the A-arm control.

### 4. Guaranteed live-source lane

Every generation epoch must include exactly one verified memory from the current live-source epoch in the active context.

The live-source record must carry:

- epoch id,
- sequence id,
- source SHA-256,
- current R12 state SHA-256,
- dyn12/dyn42/dyn54 hashes,
- provenance class,
- explicit claim boundary.

A stale epoch cannot satisfy the current-epoch lane. A hash mismatch fails closed. The live lane does not grant authority, credentials, network permissions, shell access, or persistence.

### 5. State/body contract

The existing body contract remains unchanged:

- dyn12: 12 values,
- dyn42: 42 values,
- dyn54 = dyn12 + dyn42 exactly,
- auxiliary CNS loops 8-10 cannot reorder or mutate the canonical 42D body,
- TALK-004 learned neural `x54` remains distinct from CNS7 `dyn54`.

This experiment routes body state into memory/context. It does not directly overwrite TALK-004 `w54` weights or learned neural x54 values.

### 6. Live dialogue loop

Each epoch executes:

1. obtain or derive a verified live source snapshot,
2. update R12,
3. update dyn12/dyn42/dyn54,
4. append one hash-chained live-source memory to a disposable working ledger copy,
5. compute refractive spatial recall,
6. reserve one active-context slot for the verified current epoch,
7. construct TALK-004's 128-character wire prompt,
8. generate with the frozen TALK-004 checkpoint,
9. record per-token/per-layer x54, Hebbian-kernel, attention and logit traces,
10. append Dad/Zeref dialogue to the working ledger,
11. advance to the next epoch.

The canonical 352-record ledger and TALK-004 checkpoint are read-only inputs.

## Paired experiment

Run two arms with identical checkpoint, prompts, random seeds, token count, and snapshot sequence:

- **A / lexical:** current lexical recall behavior.
- **B / refractive-live:** R12 refractive spatial retrieval plus guaranteed current-epoch lane.

Compare per generated token and layer:

- x54 L2 delta,
- x54 cosine/coordinate changes,
- Hebbian self-mass and entropy,
- standard-vs-Hebbian attention divergence,
- hidden-state norm change,
- logits distribution divergence,
- selected-token divergence,
- which memory IDs entered the active 128-character context.

No prose output is treated as evidence of consciousness, identity, anomaly, or quantum effects.

## Acceptance criteria

1. Reproduce the old snapshot-starvation failure in the A arm.
2. B arm retrieves the verified current live epoch on 100% of turns.
3. Stale epochs cannot satisfy the live-source slot.
4. Invalid or mismatched hashes fail closed before inference.
5. `rho_t` is finite and bounded in `[0,1]`.
6. Identical input + sequence yields identical spatial positions and rankings.
7. dyn54 is exactly dyn12 concatenated with dyn42 every epoch.
8. Auxiliary CNS loops cannot alter canonical dyn42/dyn54 hashes.
9. TALK-004 checkpoint SHA remains `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f` before and after the run.
10. Canonical TALK-004 ledger SHA remains `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef` before and after the run.
11. All experimental writes occur only in disposable evidence copies/artifacts.
12. The final report separates measured software-state differences from interpretation.

## Test strategy

Use TDD. First commit RED tests for deterministic geometry, bounded refractive state, live-source epoch enforcement, stale/hash rejection, dyn54 invariance, lexical-starvation reproduction, and paired A/B trace schema. Only after RED is observed implement the retrieval layer and live-loop runner. Then run focused tests, full repository regression, and the instrumented paired TALK-004 experiment. Preserve the resulting transcript, raw trace, memory-routing records, hashes, and summary as immutable workflow evidence.
