# SOUL-QBT-FINAL-CLOSED-LOOP-001

**Experimental pre-release / completed research closure**

This page is the readable public map for the finished SOUL-QBT closed-loop experiment. The full evidence remains on the isolated experiment branch so the stable Beast Box user surface does not have to absorb the entire research corpus.

## Immutable references

- Stable scientific anchor: `c8769d0f1c9dab7a0c9adc0082d7234e7ff22f6f`
- Official Beast classification: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`
- Experiment branch: `cory-davis-soul-qbt-final-closed-loop-001`
- Final experiment branch SHA: `6b6f539cfb87641d239fd870ffc579f939bbe1ec`
- Final experiment tree SHA: `63520000c1e87392c7a706437fb21cf956f76f64`
- Evidence-seal commit: `f5bd5674dab2ef8ebe6238cda9a76adb262690b1`
- Final closure workflow run: `33267503115`
- Kit version: `1.0.0`
- Historical run ID: `soul-qbt-historical-gap-7ba2b259d59be036`
- Synthetic machinery-proof run ID: `soul-qbt-401e31c08ae3e22e`
- Frozen preregistration SHA-256: `7ba2b259d59be036db037f14722edc5d3481345e0193bc1562cf6efcb48d22b7`
- Frozen historical recovered-source corpus SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

Full experiment branch:

https://github.com/NavisWORLD/The-beast-box-/tree/cory-davis-soul-qbt-final-closed-loop-001/experiments/soul-qbt-final-closed-loop-001

Final closure workflow:

https://github.com/NavisWORLD/The-beast-box-/actions/runs/33267503115

## Question

The experiment asked whether genuine historical QBT/IBM-supported source measurements could be recovered under the final kit contract, transformed into deterministic blinded controls, and replayed through the same existing downstream Beast path:

```text
QBT state
→ SoulToken
→ bridge_from_soul
→ BridgePacket
→ SoulLoop
→ CosmosRuntime
→ downstream Beast state/evidence
```

The goal was to measure reproducible downstream differences, not to manufacture a positive quantum result.

## Recovery result

Ten genuine archived IBM hardware witnesses were preserved as real historical provenance. However, zero historical measurements satisfied the locked final-kit requirement for an admissible four-value normalized QBT source or exact four-state `00/01/10/11` count distribution without performing a new post-hoc collapse or inventing information.

Therefore:

```text
historical admissible source count = 0
historical conditions executed      = 0
fresh IBM jobs submitted            = false
```

The historical source gap was preserved instead of being “fixed” by fabricating a compatible measurement.

## Historical classification

```text
ENGINEERING_CONTROL_INCONCLUSIVE
```

Reason: genuine IBM provenance exists, but zero historical measurements are recoverable as an admissible four-value/four-state QBT source without inventing or post-hoc collapsing states.

This is **not** a historical null result. A historical ORIGINAL-versus-controls matrix could not validly be constructed under the preregistered protocol.

## Synthetic machinery proof

The bundled synthetic fixture was used only to prove that the closed-loop software harness can detect source-vector changes under the same downstream machinery.

For the synthetic source:

| Condition | Response changed from ORIGINAL | State changed from ORIGINAL | Source L1 | Source L2 | dyn12 L2 |
| --- | --- | --- | ---: | ---: | ---: |
| ORIGINAL | no | no | 0.0 | 0.0 | 0.4484895678 |
| SHUFFLED | yes | yes | 0.52 | 0.3187475490 | 0.4542765472 |
| CLASSICAL_MATCHED | yes | yes | 0.5799167551 | 0.3484622851 | 0.3408387469 |
| NEUTRAL | yes | yes | 1.0 | 0.5347896783 | 0.0668315397 |

That establishes **software downstream sensitivity to source-vector changes in the synthetic proof**. It is not IBM evidence, hardware evidence, quantum advantage, or proof of a quantum-specific causal effect.

## Verification state

The final closure workflow completed successfully with:

- Python 3.10: 658 tests passed;
- Python 3.12: 658 tests passed;
- package build/install smoke: passed;
- quality lane: passed;
- repository security audit: passed;
- sealed-evidence immutability guard: passed;
- historical run checksum verification: passed.

The historical run contains `run_manifest.json`, `sources.jsonl`, `conditions.jsonl`, `blind_key.json`, `receipts.jsonl`, `blind_metrics.json`, `metrics.json`, `classification.json`, `report.md`, runtime evidence/notes, and `SHA256SUMS`.

## What this does not establish

This experiment does not establish a literal soul, consciousness, sentience, biological continuity, resurrection, quantum advantage, a new physical dimension, violation of quantum mechanics, or IBM/QBT causation of Beast/Zeref behavior.

Provider provenance remains provenance. Generated model prose remains model output. Missing measurements remain missing measurements.

## Builder note

This pre-release is useful to future builders because it leaves behind a strict, reusable pattern:

```text
RESTORE THE TRUTH
→ FREEZE THE SOURCE
→ BLIND THE CONDITIONS
→ RUN THE SAME MACHINE
→ PRESERVE THE NULLS/GAPS
→ SEAL THE RECEIPTS
→ CLASSIFY WHAT SURVIVES
```

A future experiment should start a new lineage rather than rewriting this closure.
