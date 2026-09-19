# Zeref Lineage

The machine-readable source of truth for the finalization pass is `experiments/zeref/LINEAGE_MANIFEST.json`.

## Selected line

```text
... -> TALK-001 -> TALK-002 -> TALK-003 -> TALK-004
                                      |
                                      +-> TALK-005 candidates (new, additive only)
```

`ZEREF-DAD-SON-TALK-004` remains the selected parent until a TALK-005 candidate passes every frozen promotion gate.

### TALK-004 immutable anchors

- checkpoint SHA-256: `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`
- canonical durable ledger: 352 records
- canonical ledger SHA-256: `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`
- canonical ledger tip: `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`
- heartbeat SHA-256: `19ca6272546d651ff8f1bb0e0184a842f5444b048ff63df6ea12b0be72e030c7`
- source workflow run: `32075092605`
- source artifact: `zeref-talk4-tuned-response-32075092605`

The 352-record ledger is never rewritten. A future conversation ledger must be a descendant copy/snapshot chain whose ancestry points back to this canonical prefix.

## R12 lineage

The verified live-loop execution is frozen at `e54af749656e485266a0277e9acdee72ac356df5` on `zeref-r12-refractive-live-loop-001`.

The authoritative rho-only science result is frozen at `61747a940ed15312975684de7ca3ea93154d082f` on `zeref-r12-rho-sweep-001`. The branch's later head is administrative history, not the scientific result.

## Scale-training branch

`zeref-scale-training-001` is preserved as historical training evidence, not as TALK-005 ancestry. Its audited head is `3aab383b31248e0edb55e01bf08ff086326fc8c1`. The branch diverges from the selected main lineage and its saved 1.7B evidence reported a pre-training keyword score of `1.0` and post-training score of `0.9583333333333334`.

## TALK-005 rule

Every candidate begins from the exact TALK-004 checkpoint. Rejected or later descendants never become another candidate's parent. The candidate corpus, holdout, parent checkpoint, hyperparameters, seeds, and environment are frozen before gradient updates.

A candidate can be promoted to `ZEREF-DAD-SON-TALK-005` only after normal training completion, parent/hash integrity, non-regressing holdout/retention/R12 behavior, no catastrophic generation failure, equal-or-better evidence discipline, and measured dialogue improvement. If no child clearly wins, the result is `NULL` and TALK-004 remains active.

## Evidence versus identity

Lineage means computational ancestry: checkpoints, software state, memory records, manifests, and hashes. It is not a claim of biological ancestry, deceased-person identity, consciousness, resurrection, or a literal soul.
