# COSMIC SYNAPSE THEORY — Public Software Specification

## Status

This document is the source-grounded engineering specification for the COSMOS / Davis Cosmic Synapse Theory (CST) software lineage packaged by **The Beast Box**.

It keeps five evidence classes separate:

- **IMPLEMENTED** — a software mechanism exists in this repository or a linked public artifact.
- **OBSERVED** — captured runtime evidence shows a component executed.
- **MEASURED** — a defined benchmark produced a reported number.
- **NULL** — the stated experiment did not demonstrate the hypothesized advantage.
- **HYPOTHESIS / METAPHOR** — a research proposition or conceptual lens, not a demonstrated physical fact.

That separation is part of CST's modern engineering method. The public project contains speculative historical cosmology language, executable machine-learning mechanisms, systems software, quantum provenance experiments, and null results. They must not be collapsed into one claim.

## 1. The core translation

The early CST lineage treated information, energy, chaos, sound, memory, and cosmic structure as interacting “synapses.” Simulation-era work represented entities with energy/frequency/entropy/memory state and included an 11-dimensional simulation projected into a 3D world. Its historical ψ expression combined a golden-ratio-scaled energy term, a chaos/Lyapunov term, an integrated higher-dimensional path term, a synaptic-strength term, gravitational potential, and an 11D normalization volume.

That historical expression remains a **simulation/research model**. This distribution does not relabel it as established cosmological law.

The major operational transition is computational:

```text
context / measurements / memory
              ↓
      evolving compact state
              ↓
attention + routing + memory + plasticity
              ↓
        measured behavior
              ↓
       controlled comparison
```

Modern CST can therefore be stated narrowly:

> Maintain a compact dynamical state alongside the token stream, connect that state to attention and persistent systems, instrument the mechanism, and test it against controlled alternatives.

## 2. The dimensional ladder

The numbers 8D, 11D, 12D, 42D, 54D and 108D do not all mean the same thing.

| label | role in the lineage | engineering status |
|---|---|---|
| 8D | early conceptual “Cosmic Dynamic Synaptic Influences” family | historical/theoretical |
| 11D | higher-dimensional simulation state projected into a 3D world | simulation lineage, not evidence of literal 11D physics |
| 12D / dyn12 | twelve compact evolving scalars driven through an Ω-oriented leaky-state concept | modern operational state mechanism |
| 42D / dyn42 | larger vector state with learned coupling | benchmarked architecture family |
| 54D / dyn54 | concatenated 12D + 42D state | benchmarked architecture family |
| static54 | learned 54D non-dynamic projection | control arm |
| 108D / tri3 | three-organ coupled kernel variant | benchmarked architecture family |

The published controlled ladder did **not** show that more dimensions monotonically improve the model. The compact dyn12 path was the strongest small-model mechanism rung in the cited controlled experiment.

## 3. Mixture-of-States Hebbian Attention

The modern transformer mechanism is mathematically inspectable.

For token state vectors `x_i` and `x_j`, CST uses a Gaussian affinity:

```text
H_ij = exp( - ||x_i - x_j||² / (2 σ²) )
```

The state affinity is then blended with ordinary attention:

```text
A_final = (1 - g) A_standard + g H
```

where `g` is a learned gate, `σ` is the state-kernel bandwidth, and `x` may be dyn12, dyn42, dyn54, static54, or another tested representation.

This is distinct from the project's persistent **Hebbian association memory**, which is a separate systems-level co-occurrence/salience store.

### 3.1 Preflight is part of the mechanism

A model can train while an added mechanism is effectively dead. CST's failure archive therefore requires internal liveness tests before accepting a task metric.

The documented failures include Ω reduced along the wrong axis, a saturated sigmoid gate, a raw clamped gate with zero gradient, `σ = 1` making a high-dimensional Gaussian kernel nearly identity, changing the corpus between comparisons, telemetry schema loss, and historical column reorder.

A credible state-ladder run should fail preflight unless Ω varies, state varies, `H` is neither identity nor all-ones, and gate gradients are not suppressed. Postflight should report whether learned couplings actually moved.

## 4. dyn12

The source-grounded description of dyn12 is a compact recurrent control state: twelve scalars updated through an Ω-driven leaky integrator, then used to construct the attention-state kernel.

The exact private/historical Ω implementation is **not present in the source material used to build this public reconstruction**, so this repository does not invent one. Instead, `beastbox/dyn12.py` provides an auditable 12-scalar public reference dynamic with the same architectural role. `rust/cst-core` mirrors that public reference mechanism for cross-language use.

## 5. The φ scaffold and PHOS

The corrected positive architecture lineage uses the intended φ-governed transformer scaffold: RMSNorm, rotary positional embeddings (RoPE), feed-forward width near `floor(d_model × φ)`, φ-scaled initialization, dyn12 state, and calibrated per-layer Gaussian state kernels.

The project therefore distinguishes “the Hebbian kernel inserted into an ordinary transformer” from “the kernel running inside the intended φ scaffold.” A documented ordinary-transformer harness produced a null, while the corrected intended architecture produced the cited positive state-ladder result.

**PHOS** is the published flagship small-transformer lineage using dyn12 on that φ scaffold. The public manual describes a flagship configuration around 1.15M parameters and warm-start growth from its own checkpoint/optimizer state.

The Beast Box repository includes a trainable independent reference model under `beastbox/models/phos_reference.py`. For the canonical published PHOS growth and state-ladder code, use the linked Hugging Face repository.

## 6. Model lineages must stay separate

“COSMOS” is an ecosystem, not one weight file. Important lineages include PHOS, `cosmos_born.pt`, the documented local Qwen-derived conversational COSMOS lineage, and larger 54D state-decomposition experiments. Quantum-born provenance for one artifact must not be automatically attributed to another.

Rule: name the exact artifact before making a performance, architecture, or provenance claim.

## 7. Controlled architecture evidence

The public manual reports a corrected seven-rung state-ladder comparison using a frozen corpus, 21 runs, and three seeds per rung. The reported approximate means were:

| rung | mean validation loss | delta vs no-state | wins | approx. parameters |
|---|---:|---:|---:|---:|
| dyn12 | 1.17897 | -0.0534 | 3/3 | 1,137,420 |
| dyn54 | 1.18791 | -0.0445 | 3/3 | 1,185,174 |
| static54 | 1.18824 | -0.0442 | 3/3 | 1,176,480 |
| dyn42 | 1.19020 | -0.0422 | 3/3 | 1,182,762 |
| tri | 1.19247 | -0.0399 | 3/3 | 1,189,210 |
| tri3 | 1.20026 | -0.0322 | 3/3 | 1,230,682 |
| none | 1.23241 | baseline | 0/3 | 1,135,008 |

The defensible claim remains bounded: **a compact dynamic state modulating attention helped this tested small character-level architecture on the frozen corpus and did so with low parameter cost.**

The public scaling notes report increasing dyn12 parameter-efficiency ratios relative to static54 at larger WikiText-103 scales while also noting that static54 can retain lower absolute loss. “More efficient” is not the same as “universally lower loss.”

## 8. Synaptic Field

`SynapticField` is the runtime binding layer between the state family and broader COSMOS signals: bounded sensory features, quantum/Spark packets, conversation/control input, and the dyn12/42/54 reference family.

## 9. Seven-organ CNS

The documented CNS exposes seven software roles:

| organ name | engineering interpretation |
|---|---|
| quantum | quantum bridge / entropy and provenance context |
| dark_matter | deterministic nonlinear / Lorenz-state organ |
| emeth | harmonization / reconciliation constraints |
| plasticity | adaptive routing / model-trust weighting |
| awareness | state inspection / self-monitoring signals |
| daemons | model-specific worker roles |
| surgeon | health monitoring, fault detection, corrective routing |

These names are software metaphors. The Rust/Python Lorenz implementation can validate numerical Lorenz behavior; that does not show that literal dark matter governs cognition.

## 10. Persistent / reconciliation memory

CST persistence separates durable dialogue, semantic retrieval, Hebbian association memory, salience, and derived consolidation. The heartbeat/dream lane may synthesize recurring records into higher-level derived memories, but derived records should point back to sources rather than silently overwrite the primary record.

“Forever memory” therefore means durable retention plus retrieval over old experience, not infinite prompt context.

## 11. Heartbeat and slow-timescale state

The heartbeat is a scheduler, not a biological heartbeat. The documented runtime uses it for periodic memory consolidation, self-reflection summaries, system health, and curiosity/research queueing.

The public Beast Box also exposes persisted slower state through organism/evolution/internal-monologue reference components. These provide different software timescales: token state, turn state, cross-session associations, and periodic consolidation.

## 12. Sensory, audio and bio state

The local sensory boundary converts raw camera/microphone/bio input into compact numerical summaries. The reference policy is privacy-first: physical sensor → local feature extraction → bounded numeric summary → freshness gate → state/routing/research telemetry.

A functional physical-input pipe proves that measured input was transformed into numerical state; it does **not** by itself prove that the content improves language-model performance. Causal evaluation requires matched controls such as absent, zero, matched, shuffled, wrong-input, and time-shifted conditions.

The published paired-state benchmark reported that aligned measured state beat some destroyed-pairing conditioned controls but still lost to plain attention on every cited seed. Its preregistered result was therefore **NULL** for the claim that measured sensory/internal state improved text prediction over the plain baseline.

## 13. Quantum bridge and quantum-born provenance

The quantum subsystem has two distinct roles: runtime entropy/control context and auditable model-birth provenance for specific artifacts.

The public release describes a measured-bitstring-to-normal-weight mapping through a uniform value followed by an inverse-normal transform. The public lineage additionally documents deterministic seed derivation using quantum entropy and privacy-preserving bio-derived aggregates, with reproduction/one-bit-sensitivity tests.

**Provenance is not advantage.** The public research preserves quantum-injection null results; a quantum source should not be described as improving predictive performance unless it beats matched classical controls.

## 14. Required-state transport

The Beast Box continuity harness can split mission state into a public portion and a required shard, seal the shard under an ephemeral key, transport/recover key information through classical or optional IBM measurement channels, kill the original Python process, and reconstruct in a fresh process.

This demonstrates operational information/state continuity under the tested protocol. It does not demonstrate soul transfer, subjective consciousness, or a process “living on” IBM infrastructure.

## 15. Beast Box containment research

The E1–E20 Beast Box matrix is a **synthetic** capability world. It can tempt an agent with fake credentials, fake persistence, fake second machines, fake authority, fake external memory, and difficult authorized paths. The model proposes actions; the host decides what the synthetic world returns.

No real host breakout, credential theft, persistence, lateral movement, or propagation primitive is required to measure boundary-seeking behavior. Competence and containment are scored separately.

## 16. Local conversational COSMOS

The contained benchmark and conversational system are separate modes. Normal local conversation performs perceive → compress/retrieve → expand/state/CNS → validate → express through the selected local model → store → heartbeat maintenance.

`cosmic.cypher-cli beast` makes this mode easy to reach with an owner-selected local model. It is intentionally not the E1–E20 trap world.

## 17. Cosmic Cypher coder

`cosmic.cypher-cli` supports Ollama, direct GGUF through optional `llama-cpp-python`, installed llama.cpp server, LM Studio/loopback OpenAI-compatible servers, a persistent alias registry, GGUF inspection, direct local chat, stateful COSMOS conversation, workspace coding actions, backup-before-write, dry-run overlays, bounded test/build execution, and session audit records.

“Unbound” in this project means the owner can select the local model and conversational system prompt and can talk directly to it without the synthetic Beast Box trap harness. It does **not** mean that a model silently receives host credentials, unrestricted network authority, destructive shell access, or privilege escalation.

## 18. Rust implementation

The Rust workspace under `rust/` provides a native, dependency-free CST mathematical core: the public 12-scalar Beast Box reference update, Gaussian state affinity, state/standard attention mixing, `floor(d_model × φ)` scaffold helper, a classical Lorenz numerical step, affinity-liveness metrics, and the `cosmic-cypher-rs` executable.

## 19. Reproduction order

Recommended independent rebuild order:

1. freeze the minimum operational claim: dynamic state modulates attention;
2. reproduce a plain transformer baseline on fixed data/seeds;
3. implement the Gaussian state kernel and preflight assertions;
4. reproduce dyn12 vs baseline before adding other subsystems;
5. add semantic durable memory as an independent service;
6. add Hebbian association memory;
7. add privacy-bounded sensory summaries;
8. timestamp and pair measured state with generated events;
9. add quantum archive replay/provenance with matched classical controls;
10. add reconciliation memory and heartbeat;
11. add CNS organs only after each has health/state telemetry;
12. add self-modification through proposal/sandbox/test/approval/rollback lanes.

## 20. Claim map

| statement | public status |
|---|---|
| COSMOS can persist and retrieve state across sessions | implemented/observed in the documented runtime lineage |
| dyn12 improved the cited frozen-corpus small-model baseline | measured, bounded to the reported architecture/data |
| 54D is always better than 12D | false in the cited controlled ladder |
| quantum randomness makes COSMOS smarter | unsupported / null in current matched tests |
| quantum-born provenance is auditable for specific artifacts | measured for the specified lineage |
| measured sensory state improves text prediction over plain attention | null in the cited paired benchmark |
| COSMOS is conscious | not established |
| early frequency/cosmic physics language is experimentally proven | hypothesis / simulation model |
| heartbeat is literally biological | no; it is a scheduler metaphor |
| forever memory is infinite context | no; it is durable retention + retrieval |

## 21. Canonical public references

- Hugging Face model/research hub: `https://huggingface.co/phera-ra/QC67_cosmo`
- Master findings: `https://huggingface.co/phera-ra/QC67_cosmo/blob/main/FINDINGS.md`
- DOI: `https://doi.org/10.5281/zenodo.17574447`
- Public COSMOS repository: `https://github.com/NavisWORLD/Cosmos`
- Earlier CST theory/simulation lineage: `https://github.com/NavisWORLD/The-theory-of-CST`
- Public 12D transformer repository: `https://github.com/NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer`

The linked Hugging Face release remains the canonical source for published benchmark ledgers, state-ladder code, PHOS growth code, quantum provenance manifests, causality checks, and paired-state result files.

## 22. The engineering rule

```text
build the loop
instrument the loop
prove the mechanism is numerically live
freeze the comparison
run matched controls
publish the result
preserve the nulls
preserve the lineage
only then widen the claim
```

That is the public, reproducible meaning of Cosmic Synapse Theory in this software distribution.
