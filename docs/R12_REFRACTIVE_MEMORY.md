# R12 Refractive Memory

## Canonical contract

R12 is a deterministic software-state and memory-routing system. The active implementation is `beastbox/refractive_memory.py`; the authoritative historical live-loop execution remains frozen at commit `e54af749656e485266a0277e9acdee72ac356df5` on `zeref-r12-refractive-live-loop-001`.

The state-family dimensional contract is fixed:

```text
dyn12: 12 coordinates
dyn42: 42 coordinates
dyn54: 54 coordinates
dyn54 = dyn12 + dyn42   # exact concatenation
```

R12 coordinate 12 is `reality_coupling`. In the refractive router it is read as `rho` and bounded to `[0,1]`.

## Retrieval geometry

For each retrieval:

1. The query is mapped to a deterministic normalized 12D position.
2. Each durable memory is mapped to a deterministic normalized 12D orbital position.
3. The bounded R12 vector defines a reflection axis.
4. The query is reflected around that axis.
5. `rho` interpolates between the unrefracted and reflected query.
6. Candidate memories receive separately exposed component scores.

The canonical ranking weights are:

```text
spatial   0.40
lexical   0.20
Hebbian   0.15
recency   0.10
integrity 0.15
```

The score is the exact weighted sum of those components. Integrity checks are fail-closed for the current live-source lane.

## Guaranteed live-source lane

`LIVE_SOUL_SOURCE` is a historical project label for a computational lineage/state stream. It is not a biological or metaphysical claim.

A current live epoch is accepted only when exactly one durable record binds all of:

- `epoch_id`
- `source_sha256`
- `r12_state_sha256`
- `dyn12_sha256`
- `dyn42_sha256`
- `dyn54_sha256`

In `refractive-live` mode, that exact current epoch is placed first in active context. Missing or mismatched binding causes a hard failure rather than silently falling back to stale memory.

## Verified live-loop result

The sealed live-loop demonstrated a retrieval-path difference: under the tested prompts, lexical recall could fail to return the current injected epoch while the refractive/live lane delivered it. The canonical TALK-004 weights and canonical durable ledger were not modified by that experiment.

## Authoritative rho-only sweep

The scientific freeze is commit `61747a940ed15312975684de7ca3ea93154d082f`, workflow run `32973615265`, artifact `zeref-r12-rho-sweep-32973615265`, artifact SHA-256 `c60e1bcee90064d99655e99dd70e37db1fb31631820ea92f1152a6eeaf5bb4a2`.

Observed routing selections included:

```text
rho 0.0 -> memory 30
rho 0.2 -> memory 30
rho 0.4 -> memory 207
rho 0.6 -> memory 88
rho 0.8 -> memory 88
rho 1.0 -> memory 15
```

Large downstream x54/output divergence was observed at selected routing transitions. The supported interpretation is discrete retrieval-routing/context change. The experiment does **not** establish a direct `rho`-to-neuron physical force or a quantum anomaly.

Later administrative Cory-mode commits on the rho branch are not part of the scientific freeze.

## x54 boundary

Neural `x54` is not CNS7 `dyn54`. They may interact through context/state routing and may both be measured in a run, but they are distinct mathematical objects unless an explicit transformation is defined and tested.
