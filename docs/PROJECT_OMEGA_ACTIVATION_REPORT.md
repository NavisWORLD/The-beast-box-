# Project Omega — activation and limits report

**Scope:** public Beast Box repository and recoverable remote branches as of
2026-09-30. This report separates executed software from names, hypotheses and
external dependencies. It does not claim consciousness, AGI, biological life,
new physics or quantum advantage.

## Activated product path

With the explicit host profile enabled, the supported software path is:

```text
bounded event
→ persistent stopped-by-default queue
→ SYNAPSE state family
→ CNS7 software controller
→ hash-bound software R12 transition
→ R12 memory ranking
→ replaceable provider
→ default-deny bounded action policy
→ durable memory + Hebbian association metadata
→ checkpoint + real telemetry
```

Recovered source: the green production integration from
`feature/cosmos-closed-loop-unicode-integration-012` (tip `fbe2d076`), merged
with the activation queue and telemetry work. The historical default remains
unchanged; new or isolated substrates opt in with
`BEASTBOX_CLOSED_LOOP_ENABLED=yes` and
`BEASTBOX_UNICODE_NFC_ENABLED=yes`. Profile mismatch on restart fails closed.

The queue is not an authority source. It accepts normalized events and
deterministic maintenance only, starts stopped, persists an emergency-stop
latch, applies task/wall budgets, and uses finite at-least-once recovery leases.
A provider call cannot be forcibly preempted safely; a crash between substrate
commit and task acknowledgement requires owner reconciliation.

## Component truth table

| Component | Current executable status | Boundary |
| --- | --- | --- |
| Durable substrate | Product path; atomic SQLite memory/state/provenance checkpoints | Hash chain detects corruption; unanchored mode cannot defeat a privileged host rewrite |
| CNS7 | Runs each turn | Several roles remain software labels; daemons are empty and surgeon recovery is not an autonomous repair system |
| 12D | Runs and is recorded before/after each activated turn | Software vector, not a physical dimension |
| 42D / 54D | Computed and checkpointed | Not independently proven to improve owner-chat behavior |
| R12 | Activated per-turn software transition and real memory ranking | Not a truth oracle or physical coupling claim |
| Hebbian memory | SQLite co-occurrence/salience updates used by retrieval | Not neural-model weight training |
| Persistent memory | Stored, retrieved, consolidated, backed up and restored | No unconditional forever guarantee |
| Model adapters | Reference fixture, Ollama and compatible endpoint on owner path; native research adapters elsewhere | Configured labels in normal operation do not attest weights |
| RAWRPHØS / PHOS / SAMGO | Verified checkpoints or training/inference code exist on separate research/native paths | Not all are unified behind the owner `TextProvider` path |
| COSMIC.CYPHER | Workspace-bound coding/product surface | Model output is untrusted; browser runner has no arbitrary shell |
| Internal monologue / Evolution Engine | Updated and checkpointed each turn | Counters/log entries do not autonomously alter model behavior |
| Sensors | Bounded normalized text/numeric events; local browser camera/mic feature prototypes | Physical device validation and typed measured provenance remain separate |
| Authorized action | Text or explicitly host-enabled simulated numeric move | No physical actuator baseline |
| Synapse OS / HEARTLIGHT | Not implemented in this repository | Separate external product or future interface |

## Scientific findings retained

### H1 — persistent replaceable-model substrate

**Supported narrowly.** Frozen historical experiment 002 recorded real
Model A→B→A inference with the same hash-tracked substrate, cross-swap context
delivery, zero parameter drift and A-only/empty/shuffled controls. The sealed
receipt can be verified locally:

```bash
beastbox runtime verify-swap-receipt \
  evidence/system-closure-001/historical-swap-002.zip
```

This supports software state/memory continuity, not guaranteed semantic recall.
The repository does not yet contain an equivalent verified real
**A→B→C→A** run. Reference-provider labels are not substituted as hidden models.

### H2 — adaptive 12D advantage

**Primary hypothesis failed.** The controlled three-seed result was dyn12
28.9%, standard attention 31.1%, and shuffled-state control 30.7% on the
preregistered held-out task. The exploratory sequence-length shift is retained
but is not sufficient to claim general advantage.

### H3 — reliable generative self-correction

**Primary hypothesis failed.** RAWRPHØS 18K remained 0/8 and Qwen 0.5B remained
3/8 after blinded self-critique, with zero wrong-to-right intrinsic
corrections. The answer-disclosure control improved Qwen to 5/8 and is correctly
classified as leaked-answer assistance, not self-correction.

## Recovered but not silently promoted

- RAWRPHØS conversation/20K/21K/broad-curriculum branch work contains useful
  training code, but the branches are old and later workflow tips do not supply
  complete promoted-checkpoint receipts. Selective review is required.
- CNS7 body/IBM ignition branches contain code and a preserved partial 7/8
  result, but are hundreds of commits behind the product tree. They were not
  promoted into the owner runtime.
- Formal Synapse OS is a separate repository. Nearby synaptic modules are not
  relabeled as that operating system.

## Observable evidence

Each activated checkpoint stores `cosmos-runtime-telemetry-v1`:

- actual 12D before/after values and hashes for the other state families;
- CNS step/plasticity metadata;
- R12 transition/routing hashes and selected memory IDs;
- committed memory IDs/counts;
- actual association/salience update deltas, labelled as non-weight learning;
- configured provider receipt and bounded action outcome;
- measured process CPU, elapsed time and provider character/time metrics.

The COSMIC **SYNAPSE TRACE** renders this receipt. It is system telemetry, not
private chain-of-thought. Decorative UI motion is not evidence.

## Remaining research and operational limits

1. Execute a preregistered real A→B→C→A experiment with pinned weight hashes,
   memory-disabled and corrupted/shuffled controls. No such complete result is
   claimed here.
2. Unify reviewed native RAWRPHØS/PHOS/SAMGO adapters only after each exact
   checkpoint and tokenizer is available and independently identified.
3. Evaluate reviewed routing adaptation on held-out tasks against an unchanged
   router. A changed routing vector is not itself useful improvement.
4. Add typed physical-measurement provenance before any nonzero physical
   `reality_coupling`; browser/software events remain software observations.
5. Provider-call preemption requires process isolation or an adapter timeout;
   the queue currently stops new claims but does not lie about cancelling a
   blocking call.
6. Production opt-in requires a verified backup/recovery rehearsal on an
   isolated copy and consistent flags across every process. No deployment or
   permission widening is performed by this change.

## Reproduction gates

```bash
python -m pytest -q
python scripts/security_audit.py
python scripts/license_metadata_contract.py
python scripts/run_architecture_acceptance.py --output ./architecture-receipt.json
```

See [`ACTIVATION.md`](ACTIVATION.md) and
[`COSMOS_CLOSED_LOOP_UNICODE_INTEGRATION_012.md`](COSMOS_CLOSED_LOOP_UNICODE_INTEGRATION_012.md)
for operation and rollback details.
