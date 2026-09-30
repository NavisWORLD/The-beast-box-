# COSMOS 011 — CONFIRMED wiring gaps; separately verified actual model oracle diagnostics

**29 September 2026 (US Central); CI evidence completed 30 September UTC.** This is a *new diagnostic*, not a reinterpretation or post-hoc revision of the original frozen COSMOS 009/010 scientific experiments in parent PR #158. All experimental code and both parser definitions were preregistered in original source before the recorded model runs. No owner database, memory, live production model, paid API or checkpoint was changed. Original upstream public full safetensors hashes were independently verified.

## 1. Missing software handoff ACTUALLY demonstrated with production code

[Successful actual two-turn DurableRuntime and original-isolated-harness audit](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36660702003) completed from source test merge checkout `6f205461f99a4265deb2306af5d6c157bc481260`. Its complete original audit receipt SHA-256: `3fe584b7a6aebc7c8335267901dcbb734bd445daa5b75847895e66fe2d27dd9a`.

Actual product `DurableRuntime`, fresh isolated SQLite synthetic-only memory and non-privileged deterministic fake provider for two actual turns:
- Original CNS stepped **0 → 2**, and its **actual dyn12 values changed between turns**.
- Real durable memory successfully supplied the expected fake notebook record; original stage receipts included `memory_lookup → state_cns → r12_routing → model → memory_write → provenance → checkpoint`.
- **Actual product persisted R12 state SHA remained byte-identical to its initial state before/after both turns**. R12 sequence **0 → 0**, synthetic-unmeasured reality coupling **0 → 0**. Product had not performed an R12 in-turn transition. This is a missing handoff for *an intended per-turn evolving R12 architecture*; whether actual nonphysical conversation should alter reality-coupling remains governed by provenance restrictions.
- Production `DurableRuntime._route_memories` uses the original static `RefractiveMemoryRouter`, but **does not automatically install isolated learned weights** from `AdaptiveControl.fit`; the prior 009 used a synthetic `SimpleNamespace` memory adapter, not full production `DurableRuntime`.

The separate *original 009 source* used `dyn12=[0.0]*12`, `sequence=0`, initial `r12_state` where `reality_coupling=0`, making its refractive reflection mathematically the identity. Original adaptive router weights from unrelated sawmill/turtle/orchid pseudo-labeled training set were `spatial=0.326819, lexical=0.264648, hebbian=0.172659, recency=0.094349, integrity=0.141524`. On the frozen first eight synthetic numeric notebooks from seed 17 the real product ranking functions returned:
- Conventional lexical: **8/8** correct top-1.
- Original static R12: **2/8**.
- Original isolated adapted R12: **2/8**.
- Oracle: **8/8**.

This discrepancy is reproducible and can reflect severely mismatched training-domain features and inactive/misaligned state wiring. Prior 009's full two-seed performance is still historically correct for its specific test configuration. It does **not** evaluate the complete intended closed-loop architecture.

## 2. Independent real generated-output oracle diagnosis—NOT just a grader artifact

Original real published-weight CPU jobs for [Qwen 0.5B and SmolLM2 135M](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36660702003) completed **SUCCESS** with immutable named-tensor hashes and full upstream safetensors identity; original complete per-case synthetic-only literal evidence archived in GitHub Actions (30-day artifact retention). Separate receipt hashes:
- `smollm2-135m`: `c8c7efc8d9e752069e3488021b534b785b9f4a3107cbe5a9bf73c8a58ba0bfa9`.
- `qwen2.5-0.5b`: `dbce641a6150a5a413bfc39cb31ea2f916cfae0546eb4883ca97f7032e5faee7`.

Four **exact original 009 synthetic oracle tasks** for seed 17 × four *prespecified* diagnostic conditions × both 18- and 80-token budgets per model. The strict original 009 metric is retained and a new independently preregistered *narrow, full-first-line semantic* metric recorded separately. Below: **semantic correct answers / 4**. Each result is IDENTICAL at 18 and 80 generated token budgets.

| Frozen diagnostic task | SmolLM2-135M | Qwen2.5-0.5B |
| --- | ---: | ---: |
| Copy **only** the 3-digit seed from supplied PERFECT correct source | **3/4** | **0/4** |
| Arithmetic with seed and offset provided directly, no retrieval | **2/4** | **3/4** |
| Original 009 combined perfect-source prompt + arithmetic | **0/4** | **0/4** |
| New frozen short explicitly structured perfect-source prompt + arithmetic | **0/4** | **0/4** |

**Observed literal synthetic-only output diagnostics**, not conjecture: SmolLM2 correctly copied 960/710/210 but its original oracle output described the synthetic notebook instead of calculating and its structured oracle output sometimes echoed input field labels. Qwen's four independent copy-seed outputs were the input seeds **each plus 1** (960→961, 710→711, 210→211, 400→401), while it calculated three of four independent plain numeric sums accurately. Neither model solved the combined source-plus-arithmetic problem even with the oracle document, even when increased from 18 to 80 generated tokens. This is real generated-output evidence, not exclusively an exact `FINAL:` scoring artifact.

**Inference:** retrieval alone cannot establish useful generated-answer improvement unless an oracle condition first demonstrates the chosen model can reliably use a perfect source. The current Qwen and Smol oracle combined-task failures confound all architecture-vs-conventional generative accuracy conclusions on these exact four diagnostic examples. Potential causes include task instruction/context integration, model behavior, original prompt and training—not yet isolated by this small sample. Source-only statistical inference is not possible; there is no proof that either model is intrinsically incapable of all forms of correction.

## 3. Research-only host handoff repair prototyped and TESTED

[Successful four-test genuine DurableRuntime handoff/rollback job](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36661029112) on original host-source PR head `993394c162ab0316418501f8b22e806ef27202b1`. The new opt-in `scripts/cosmos_research_r12_handoff_011.py` subclass does **NOT** modify owner production or default `DurableRuntime`. Instead it installs a hash-bound, explicit `provenance_class="synthetic"` R12 software transition AFTER the original CNS tick and BEFORE existing real `RefractiveMemoryRouter.rank`. It relies on original `derive_r12_transition` and existing durable checkpoint mechanism. Four actual integration tests verify:
- valid synthetic event/source/payload SHA integrity, never fabricated `measured` provenance;
- actual CNS state change **and** R12 software sequence incremented **0→1→2** through the existing production host stages;
- persisted exact R12 state survives a truly fresh `DurableRuntime` process instance, then increments to **3** on another turn;
- a deliberately failing provider triggers original full checkpoint/state rollback, without persisting attempted R12 or faulty memory.
- The original unmodified runtime remains an explicit non-transition control.

**Critical physical-state boundary:** the successful research handoff does **not** force fake reality coupling to 1; it correctly retains `reality_coupling=0` on these unmeasured synthetic text events, as required by the existing original R12 formula. This is proof of coherent software-state wiring and durable rollback, **not proof of 12D generative advantage** or measured physical sensor input.

## Next actual engineering gates (not claimed complete)

1. **Host-only opt-in/product integration**: actual durable per-turn R12 derivation with valid *measured* source events only when independently verified, plus a separate nonphysical transition for ordinary text; enforce no model-granted authority, intact old checkpoint compatibility, lifecycle/versioning and rollback. Do not silently enable an experimental learned global router in owner production.
2. **Correctly aligned retrieval fit**: disjoint same-domain source labels, realistic synonym/paraphrase tasks where strong conventional lexical retrieval is not already perfect; record each feature/score and exact original static vs adaptive vs lexical top-1 and MRR before any inference. Include actual CNS-derived 12D and time-varying state where justified; separately label real physical provenance from pure synthetic simulation.
3. **Validated host-composition path**: use a deterministic host-side extractor and explicitly authorized basic arithmetic tool in a separate *tool-assisted system* condition when both frozen small models fail the oracle compound task. Score retrieved-record correctness, host-calculated answer correctness, model natural-language synthesis and refusal/abstention **separately**; do not call tool-computed arithmetic new LLM reasoning.
4. **Only after the oracle is competent on the selected task**, rerun new independent frozen original models/end-to-end retrieval comparison on a fresh preregistered task sample. Include no-evidence, strong lexical/semantic, original R12, adaptive integrated R12, and oracle all with identical model weights and visible model-specific limits.

The present opt-in research proof is not deployed. The previous original experiments' nulls and receipts remain untouched; the missing handoff is real and experimentally demonstrated, while an advantage from fixing it is **still unproven**.
