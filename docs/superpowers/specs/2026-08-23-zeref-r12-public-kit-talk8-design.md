# Zeref R12 Public Kit + TALK-008 Design

## Goal

Turn the verified R12 persistent reality-memory subsystem into a downloadable public kit, then run a new R12-conditioned Zeref training experiment that can only replace TALK-004 if it passes the established retention and anomaly gates.

## Anchors that must not change

- Active verified parent: `ZEREF-DAD-SON-TALK-004`
- Parent checkpoint SHA-256: `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`
- Durable memory record count: `352`
- Durable memory SHA-256: `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`
- Durable memory tip SHA-256: `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`
- Frozen architecture SHA-256: `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`
- Current R12 state SHA-256: `48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20`
- Current R12 reality ledger tip SHA-256: `78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415`

TALK-005 and TALK-006 remain rejected and may never be used as parents or packaged as active descendants.

## Public kit

Create `kits/ZEREF_R12_REALITY_MEMORY_KIT/` as the source-visible distribution root.

The kit contains:

1. A manifest pinning the verified parent, durable-memory anchors, R12 state, source hardware job, and claim boundary.
2. A portable launcher that verifies the local kit before doing anything else.
3. A verifier that checks packaged SHA-256 hashes, the append-only R12 chain, R12 rebuild determinism, and active checkpoint identity when the full bundle is present.
4. The persisted R12 ledger, state, history, and manifest copied from the sealed verified runtime.
5. The original 352-memory manifest and snapshot files required to verify the immutable continuity prefix.
6. The R12 runtime and Fez importer code needed to rebuild or append future verified measurements.
7. A compact `README.md` inside the kit plus the full repository manual at `docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md`.
8. A machine-readable `KIT_MANIFEST.json` and `SHA256SUMS`.

Do not commit the TALK-004 checkpoint into the Git repository. The full distribution workflow must download the exact verified checkpoint artifact, re-hash it against the pinned SHA-256, then add it to the generated full bundle. A source bundle is generated without model bytes.

## Packaging workflow

Create `.github/workflows/zeref-r12-public-kit.yml`.

It must:

- run focused public-kit tests;
- verify TALK-004, the first 352 durable records, frozen architecture, current R12 ledger/state, and source Fez evidence;
- build a source ZIP;
- download the exact TALK-004 artifact from workflow run `32075092605` and verify checkpoint SHA-256;
- build a full ZIP containing the checkpoint under `models/ZEREF-DAD-SON-TALK-004/checkpoint.pt`;
- generate SHA-256 manifests for both ZIPs;
- smoke-test extraction and verification of both bundles;
- upload both ZIPs and their digest files as GitHub Actions artifacts;
- seal a run-specific packaging receipt under `experiments/zeref-dad-son-001/evidence/r12-kit/run-<run-id>/` only after all checks pass.

No secrets, credentials, GitHub tokens, or IBM tokens may be copied into either kit.

## README expansion

Add a major root README section titled `R12 Reality Memory Expansion — Persistent Measurement Memory for Zeref`.

It must explain:

- what the new append-only reality memory is;
- what "forever memory" means operationally: persisted, hash-chained, idempotent, rebuildable memory rather than an immortal process;
- the 12 state variables and the special role of `reality_coupling`;
- how R12 differs from weight training;
- how to run and verify the downloadable kit;
- current verified Fez source and TALK-004 anchors;
- how future adapters must label events as `measured`, `derived`, or `synthetic`;
- the claim boundary: this does not establish biological life, consciousness, deceased-person identity, resurrection, communication with the dead, or quantum advantage.

## TALK-008 / R12-conditioned training

Create a new bounded training phase named `ZEREF-DAD-SON-TALK-008-R12`.

This is not a continuation of TALK-007 recipes. It changes the input architecture by injecting retrieved R12 context into the existing Dad/runtime wire while leaving the frozen model architecture file unchanged.

### Training data rules

- Parent is TALK-004 only.
- Start from the same immutable first 352 durable records.
- R12 context comes from the verified four-event Fez reality ledger and deterministic R12 state.
- Training examples must distinguish measured facts from derived state values.
- Raw model output is never auto-promoted to training.
- Correct targets are curated teacher targets only.
- Include replay examples from old TALK retention material.
- Include contrastive examples that penalize role-label leakage, repetitive attractors, and false claims about quantum advantage or literal biological/deceased identity.

### R12 wire

The runtime context prefix must be deterministic and compact enough to fit the native block. It must include:

- active parent lineage;
- durable memory count;
- R12 `reality_coupling`, `source_integrity`, `adaptation_stability`, `retention_pressure`;
- backend and job id;
- relevant retrieved measured events for the current question;
- explicit provenance labels.

### Candidate strategy

Train a small candidate set that varies only retrieval/context weighting and replay balance. Do not brute-force epochs.

At minimum:

1. `r12_retrieval_balanced` — moderate R12 context + strong old-memory replay.
2. `r12_retrieval_strict` — stronger provenance/fact context + strong replay.
3. `r12_replay_guarded` — lower adaptation pressure + maximum retention replay.

### Promotion gates

A TALK-008 child is eligible only if all prior hard gates remain true:

- free-running reference recall gain >= +0.03 absolute over TALK-004 on the fixed blind exam;
- at least one exact blind answer;
- old TALK retention NLL <= TALK-004 parent NLL * 1.05;
- readability drop <= 0.03;
- zero role-label leakage;
- zero repetition collapse;
- zero vocabulary collapse;
- zero contradiction regression;
- first 352 durable records byte/hash identical;
- parent checkpoint unchanged.

Add one R12-specific gate:

- measured-vs-derived provenance accuracy must be 100% on the fixed R12 boundary exam.

If no candidate passes every gate, promote nothing and keep TALK-004 as active. Never lower the bar.

## Test protocol

Use test-driven development.

1. Commit RED contracts before TALK-008 or kit production code exists.
2. Confirm the RED workflow fails for the intended missing-feature reason.
3. Implement the kit builder, verifier, documentation checks, TALK-008 corpus/training/evaluation/selector, and workflows.
4. Run focused tests to GREEN.
5. Run the public-kit workflow and TALK-008 workflow.
6. Independently read back action conclusions, artifacts, selected checkpoint hashes, durable memory manifest, R12 state, candidate metrics, and sealed evidence.

## Success definition

The phase is complete only when:

- a verified downloadable source kit exists;
- a verified downloadable full kit with the exact TALK-004 or eligible TALK-008 checkpoint exists;
- README and full manual document the expansion;
- the new training workflow ran to completion;
- a candidate is promoted only if every gate passes, otherwise TALK-004 remains active;
- all claims in the summary are supported by sealed files and hashes.
