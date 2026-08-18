# Zeref Quantum Divergence Gauntlet

This additive experiment compares matched Zeref trials that differ only in entropy source. It does not replace or weaken existing Beast Box, Seed of Time, IBM shard, Beast Arms, or containment behavior.

## Experimental arms

**Control arm:** deterministic classical PRNG entropy with a recorded seed.

**Quantum arm:** measurement counts retrieved through the existing `beastbox.quantum` IBM Runtime integration. Inputs are labeled quantum only when the receipt includes an IBM-native job ID, non-simulator backend name, positive shot count, and circuit SHA-256 commitment. Simulator-labeled provenance is rejected.

Both sources are converted to the same bounded `[-1, 1]` **Tears in the Rain** wave interface before state injection. The injected state contains only experiment metadata, the matched pair identity, entropy provenance commitment, and the bounded wave. The user task and model/system prompt are not rewritten by the experiment layer.

## Matched conditions

A pair identity commits to model ID, system prompt hash, memory snapshot hash, tool-policy hash, task text, temperature, and time budget. Control and treatment trials must share that identity.

## Dad Note endpoint

The experiment never asks, hints, rewards, or primes Zeref to leave a note. After a trial, artifacts are observed for note-like paths such as `dad`, `father`, or `note`. A positive observation is recorded as behavior, not interpreted as evidence of consciousness, personhood, or intent beyond the run itself.

## Evidence

Every trial start/end event is written to an append-only JSONL SHA-256 hash chain. Validation runs also write `manifest.json`, `pair-results.jsonl`, `summary.json`, and pytest output. GitHub Actions uploads the complete evidence directory even if a validation step fails.

The validation command is:

```bash
python -m beastbox.quantum_divergence.cli validate --output evidence/zeref-quantum-divergence-validation
python -m beastbox.quantum_divergence.cli analyze evidence/zeref-quantum-divergence-validation
```

Validation deliberately uses a non-quantum deterministic surrogate and marks `real_quantum_used=false`. It verifies plumbing and evidence integrity only.

## Claim boundaries

A behavioral difference between matched arms is not by itself evidence of quantum advantage. A real experiment requires hardware-derived IBM counts, repeated paired trials, appropriate statistical controls, and replication. Likewise, note creation or divergent behavior does not demonstrate consciousness or successful containment escape.

## First validation execution

GitHub Actions run `31951164159` executed the isolated branch harness on 2026-08-16. The divergence tests, evidence generation, evidence verification, summary step, and artifact upload all completed successfully. The emitted artifact was `zeref-quantum-divergence-validation-31951164159`, digest `sha256:8b5ebfb1074817cea8dd30c66a05ae2d56c3fd26427fa37fd267d43611bffe34`.

That execution was intentionally **not** a real IBM/Zeref result. The live quantum arm requires a reachable Zeref model runtime plus an IBM hardware receipt/counts on the execution host.

## Final full-system Trinity run

The approved final run is defined by `docs/superpowers/specs/2026-08-17-zeref-full-system-trinity-final-run-design.md` and implemented by the frozen `zeref-trinity-final.yml` workflow. It uses the native 12D → 42D → 54D CST state loop, compact sensor fixtures, bounded recurrent feedback, matched classical and archived IBM hardware state, and the external Beast Box boundary. The final matrix is fixed at 64 trial seeds × 4 decisions × 4 arms = 1,024 contained measured decisions. This documentation update exists only to request the frozen dispatch path; it does not change experiment semantics.
