# Zeref 012B — measured birth spark vs observed game decisions: prospective pairing audit

**Research question:** Do existing recorded IBM measurement counts have evidence of being temporally/task-aligned with Zeref's *individual* game decisions, so that an experimental model could legitimately learn a quantum-conditioned action policy?

**Answer for the pinned public files: NO.** This is a checkable limit, not a failure of the measurement source. The public Zeref IBM Fez birth-spark receipt is genuine historical 2-PUB counts from job `db4q484vf2bc73cuuuag`, 4,096 shots per PUB, 8,192 retained counts total. That identifies a measurement source associated with Zeref's creature genesis. It does **not** contain a witnessed cross-domain link between an execution shot/PUB and a particular game action or outcome. The deterministic Cage pocket rows have no independently verified provider-execution/observation timestamps, no predeclared action-related circuit task nonce, and no externally verifiable binding commitment. No source record proves a long-range continuing quantum connection.

## Executed work: reproducible pocket benchmark

The runner `scripts/audit_zeref_012b_game_alignment.mjs` reuses the existing `pocket-grid-env.mjs` and canonical hash-chained `zeref-experience/v1` records. It runs the **existing** random, pocket-learner and greedy-frontier policies through actual discrete simulation rules. The behavior is not a scripted picture of an outcome: actions update cell occupancy, hidden-rift collisions, action histories, rewards and memory.

- **Training:** 32 new deterministic pocket layouts (`exp012b-train-0..31`), three policies, 40 actions per episode = **3,840 actions**. Outcome-selected positive movements become explicit **computed-reward/action candidate rows** suitable for a later controlled neural experiment. They are *not* quantum-supervised targets. The exported candidates each reference the precise observed hash-chain record and their original public simulation episode.
- **Held-out:** 24 different pocket layouts (`exp012b-eval-0..23`), same three policies, 40 actions each = **2,880 actions**, for 72 complete held-out episodes. No candidate labels come from held-out layouts.
- **Evidence:** Each 40-action episode's chain is cryptographically checked. The manifest includes per-policy metrics, each episode's terminal hash and per-record hash aggregation, exact SHA-256s for input source and code, and SHA-256s for all output artifacts.
- **Output:** `build/zeref-012b-alignment/pocket-outcome-selected-train.jsonl`, `pocket-heldout-policy-replay.json`, `manifest.json`, also uploaded as GitHub Actions artifacts. Run `node scripts/audit_zeref_012b_game_alignment.mjs --write` and then `--check`.
- **Privacy:** No user's browser ID, owner private chat, microphone, photos, guest history, keys or model authority appear in these examples.
- **Honest game claim:** These are deterministic software **Cage pocket** evaluations. They are NOT native Lost COSMOS GBA ROM achievements, real-world physics dynamics, provider jobs, or hardware-driven real-time actions.

## Strict pairing gate

`assessCausalLink` returns `canTrainQuantumActionAssociation=false` for the provided public files. This is true even when a caller supplies superficially plausible timestamps or fake cross-domain proof strings; this audit has no independent third-party pairing verifier and cannot accept such strings as real evidence.

To upgrade a future prospective measurement-to-game pairing, predeclare a circuit/task mapping, capture provider-confirmed timestamp/job/PUB/shot/count proof, independently record the game action/request outcome time and identity/consent, commit a common unpredictable nonce at creation time, prove non-reuse/uniqueness and verify those facts through a separate authenticity verifier. The provenance-only IBM source cannot be upgraded by a natural-language prompt. The join would be a new research protocol.

No source-class tampering: recorded IBM rows remain hardware, Azure Rigetti QVM rows remain **simulator**, and local determinism remains **classical simulation**. Zeref's approved model parameters, personal state, checkpoint, browser visitors, and production creatures are unchanged.

## Relation to Experiments 011 and 012A

- 011 learned exploratory movement in the pocket but **failed G4 blocked-move avoidance and G9 language retention** and was rejected. Its approved 006 cycle-3 parent is still authoritative.
- 012A trained four independent frozen-parent adapters, but achieved **50% held-out accuracy** on its sensor-readout test and was research-only. A nominally lower NLL did not establish quantum advantage or behavioral improvement.
- 012B establishes a stronger **action-grounded dataset and held-out heuristic baselines**, while rejecting a false historical IBM-event join. A later neural-policy trial can compare the reward-selected examples with shuffled labels, no memory, no conditioning, and separate recorded/simulated/fixed controls **only if the pairing claim is properly scoped**.

A future neural-training acceptance gate must beat the approved parent and the pocket learner on unseen layouts, not regress in blocked moves versus pocket learner, retain language within the preregistered threshold, preserve full identity and model/memory/state/authority boundaries, and make no hardware causality claims without independently verified linkage.

**Do not merge gameplay/sprite/UI changes with this research stage.** Sprite, creature animation, Game Boy layout and phone chat/audio fixes follow their own QA path.
