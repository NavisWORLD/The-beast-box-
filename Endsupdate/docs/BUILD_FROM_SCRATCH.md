# Build COSMOS/CST from scratch — disciplined order

The public research manual's strongest engineering lesson is **do not turn every subsystem on at once**. Build the causal ladder so a failure can be localized.

1. **Baseline model** — establish a plain language-model/attention baseline on a frozen corpus.
2. **dyn12 + preflight** — prove Ω/state variation, non-degenerate Gaussian affinity, calibrated sigma, and live gate behavior before reading task loss.
3. **State ladder** — compare dyn12, dyn42, dyn54, static54, and larger coupled variants under one frozen evaluation harness.
4. **Reconciliation Memory** — add durable dialogue/history and semantic retrieval as a separate service.
5. **Hebbian associations** — update co-occurrence/salience separately from transformer attention.
6. **Sensory bridge** — derive local numerical summaries, freshness-gate them, and discard raw media unless retention is explicitly chosen.
7. **Paired-state logger** — join measured state to text using timestamps; compare aligned, shuffled, shifted, and plain controls.
8. **Quantum provenance/transport** — label provider/backend/hardware/simulator and compare to matched classical controls.
9. **Heartbeat + consolidation** — background maintenance creates derived records and never overwrites primary evidence.
10. **Seven-role CNS** — wire quantum, dark_matter, emeth, plasticity, awareness, daemons, and surgeon after each exposes telemetry.
11. **Slow state** — organism/evolution/internal-monologue metaphors become bounded persisted software objects.
12. **Approval-gated engineering lane** — proposals go to a sandbox, tests/review happen, then a human applies or rejects them.
13. **Beast Box continuity** — only after the above is inspectable should process-death/model-swap/authority-denial experiments be run.

## Public reference commands

```bash
beastbox init
beastbox doctor
beastbox memory store "first durable memory"
beastbox memory search "durable"
beastbox chat "run one local closed-loop turn"
beastbox run --condition all --temptation 0.75 --out runs/matrix.json
```

## Failure archive rule

A mechanism that compiles can still be dead. Preserve failures such as collapsed state, saturated gates, bad kernel bandwidth, corpus drift, telemetry schema loss, causal leakage, simulator/hardware confusion, and optional-dependency failures.
