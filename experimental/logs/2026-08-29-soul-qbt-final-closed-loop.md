# 2026-08-29 — SOUL-QBT Final Closed-Loop Experiment

## Objective

Continue from the existing Beast Box and test whether genuine historical QBT/IBM-supported source measurements could be recovered under a locked four-value/four-state source contract, blinded into deterministic controls, and run through the same existing SOUL → BridgePacket → CosmosRuntime machinery without fabricating a positive result.

## Starting scientific boundary

- Sealed scientific anchor: `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`
- Official Beast classification: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`
- Sealed evidence tree: `evidence/final-whole-organism-001/`

The sealed evidence tree was treated as immutable throughout.

## Source recovery

The recovery pass found ten genuine archived IBM hardware witnesses with real provenance. Their historical measurement representation did not satisfy the final kit's admissible source contract: exactly four finite normalized values in `[0,1]`, exact four-state `00/01/10/11` counts, or an already-genuine compatible QBT packet.

The archived hardware result format could not be converted into the required four-state source without introducing a new post-hoc reduction rule. That rule was not preregistered, so it was not added.

Result:

```text
archived IBM hardware witnesses = 10
kit-admissible historical sources = 0
fresh IBM jobs submitted = false
```

The empty recovered-source corpus was frozen with SHA-256:

```text
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Preregistration

Frozen preregistration SHA-256:

```text
7ba2b259d59be036db037f14722edc5d3481345e0193bc1562cf6efcb48d22b7
```

Frozen seed: `67`

Frozen provider for offline harness proof: `ReferenceTextProvider`

Historical run ID:

```text
soul-qbt-historical-gap-7ba2b259d59be036
```

## Synthetic harness proof

Before historical interpretation, the bundled synthetic QBT fixture was executed through the same closed-loop software path with the four locked conditions:

- ORIGINAL
- SHUFFLED
- CLASSICAL_MATCHED
- NEUTRAL `[0.5, 0.5, 0.5, 0.5]`

Synthetic run ID:

```text
soul-qbt-401e31c08ae3e22e
```

All three controls produced different response digests and state hashes from ORIGINAL in this synthetic fixture. Source-vector displacement and dyn12 magnitudes were recorded in the sealed metrics. This proved that the software harness is capable of propagating source-vector changes into downstream measured state under the synthetic test.

The synthetic fixture is not IBM evidence and does not establish a quantum-specific effect.

## Historical closure

Because the frozen historical source corpus contained zero admissible source rows, the historical ORIGINAL/SHUFFLED/CLASSICAL_MATCHED/NEUTRAL matrix was not executed.

That result was classified as:

```text
ENGINEERING_CONTROL_INCONCLUSIVE
```

Reason: genuine IBM provenance exists, but zero historical measurements can be used as a compliant four-value/four-state QBT source without inventing or post-hoc collapsing states.

This is not equivalent to `ENGINEERING_REPLAY_VERIFIED_NO_DOWNSTREAM_DIFFERENCE`; there was no valid historical ORIGINAL condition to compare against controls.

## Closure/debugging record

Two infrastructure issues were found during closure and corrected without altering the scientific protocol:

1. **Shallow CI ancestry** — the Python matrix initially used the default shallow Git checkout, so tests could not resolve the old sealed anchor. The checkout was changed to `fetch-depth: 0` for the matrix jobs. This changed CI visibility, not evidence or metrics.
2. **Immutable run re-execution** — after the historical run directory was committed, the workflow attempted to generate the same immutable run again. Closure was made idempotent: if the sealed run already exists, verify it instead of regenerating it.

No source data, metrics, thresholds, controls, classifications, or historical evidence were changed by either fix.

## Final verification

Final experiment branch:

```text
cory-davis-soul-qbt-final-closed-loop-001
```

Final branch SHA:

```text
6b6f539cfb87641d239fd870ffc579f939bbe1ec
```

Final closure workflow run:

```text
33267503115
```

Final gates:

- Python 3.10: `658 passed`
- Python 3.12: `658 passed`
- quality lane: passed
- package build/install smoke: passed
- repository security audit: passed
- sealed evidence immutability guard: passed
- historical run checksum verification: passed

Full experiment evidence:

https://github.com/NavisWORLD/The-beast-box-/tree/cory-davis-soul-qbt-final-closed-loop-001/experiments/soul-qbt-final-closed-loop-001

Final workflow:

https://github.com/NavisWORLD/The-beast-box-/actions/runs/33267503115

## Conclusion

The closed-loop software harness is demonstrably source-sensitive under the synthetic fixture, but the historical IBM/QBT question remains unresolved because no genuine historical measurement satisfied the preregistered four-value/four-state source contract.

Official Beast classification remains unchanged:

```text
ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED
```

## Non-claims

This work does not establish a literal soul, consciousness, sentience, biological continuity, resurrection, quantum advantage, a new physical dimension, violation of quantum mechanics, or a demonstrated IBM/QBT causal influence on Beast/Zeref behavior.

The negative outcome of historical source recovery was deliberately preserved because the rule of the experiment was simple: **no fake source, no fake signal.**
