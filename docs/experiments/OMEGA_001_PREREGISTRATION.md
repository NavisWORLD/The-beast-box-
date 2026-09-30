# OMEGA-001 preregistration — whole-substrate activation experiments

Status: **PREREGISTERED before any OMEGA-001 measurement.** This file is committed
before the experiment code is run. Results are published separately in
`OMEGA_001_RESULTS.md`, including null and negative outcomes. Criteria below must
not be edited after the first measurement; any later change is recorded as a
deviation in the results file.

## Scope and boundaries

- Runtime under test: the existing `beastbox.durable.DurableRuntime` (unchanged
  production code). New code only *observes* it (tracer), *drives* it (operator
  loop) or *evaluates* it (experiments). No change to authority policy,
  checkpointing, memory or routing code is part of this experiment.
- Models: the three already-pinned checkpoints used by earlier experiments,
  verified by SHA-256 before use:
  - A: native RAWRPHØS 14K, `4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5`
  - B: `HuggingFaceTB/SmolLM2-135M-Instruct@12fd25f7…`, safetensors `5af571cb…`
  - C: `Qwen/Qwen2.5-0.5B-Instruct@ec7ddfa9…`, safetensors `fdf756fa…`
- Hardware: a cloud CPU VM (4 vCPU, no GPU). Not Cory Davis's own machine.
- No paid API, no remote inference, no owner data, no production deployment,
  no model training or weight update. All data are synthetic.
- The model never receives a capability grant. Every action is proposed as text,
  validated by the host against a fixed allow-list, and executed by the host inside
  a disposable directory.

## E1 — H2a: does deployed R12 routing beat conventional retrieval controls?

Workload: per seed, 24 synthetic "code facts" (`The <adj> <noun> code is <value>.`),
48 lexical distractors sharing words with facts, 24 direct queries
(`What is the <adj> <noun> code?`). Seeds 0–9 are the evaluation set.

Arms (identical memory contents per seed; each query ranked against the same store,
queries are not written back):

1. `r12_deployed` — `RefractiveMemoryRouter.rank` with the runtime's actual
   checkpointed dyn12 and `r12_state`, exactly as `DurableRuntime._route_memories`
   calls it (fidelity is checked against a real `respond()` on a copy).
2. `lexical_baseline` — `ReconciliationMemory.search` (the base runtime path).
3. `r12_no_spatial` — same R12 components with the `spatial` weight set to 0 (ablation).
4. `r12_shuffled_dyn12` — deployed R12 with the dyn12 vector permuted (state control).
5. `random` — uniformly random order (floor).

Primary metric: **gold fact in delivered top-5** (hit@5), because top-5 is what the
runtime passes to the model. Secondary: hit@1, MRR.

Decision rule: H2a is **supported** only if `r12_deployed` exceeds the better of
`lexical_baseline` and `r12_no_spatial` on hit@5 by ≥ 5 percentage points with a
paired bootstrap (10,000 resamples over queries, seed 67) 95% CI excluding zero.
It is **refuted for this workload** if `r12_deployed` is worse than
`lexical_baseline` with the CI excluding zero. Otherwise **null**.

## E2 — H2b: does Hebbian plasticity improve retrieval on alias queries?

Workload: per seed, 16 facts `The <noun> code is <value>.`, 16 alias statements
stored earlier (`People also call the <noun> the <alias>.`), 32 distractors, and 16
alias queries (`What is the <alias> code?`) that share **no content word** with the
gold fact except `code`. Seeds 0–9.

Arms: `r12_deployed` with the learned association table vs the same store with the
`associations` table emptied after writing (`hebbian_ablated`); plus
`lexical_baseline`.

Decision rule: Hebbian plasticity is **supported as a retrieval contributor** if
`r12_deployed` beats `hebbian_ablated` on hit@5 by ≥ 5 points with the paired
bootstrap CI excluding zero. Otherwise null. This measures external associative
state, never model-weight learning.

## E3 — H1: model independence A → B → C → A with controls and hard restart

Procedure on one fresh substrate: A stores fact F1; swap to B, query F1, B stores F2;
swap to C, query F1 and F2, C stores F3; the process is killed with SIGKILL while
idle (between turns) and again **during** a model call; a new process reopens the
substrate, verifies the checkpoint chain, swaps to A, queries F1, F2, F3.

Measured per model and stage: substrate identity (system id, chain validity,
checkpoint hash after reopen), **context delivery** (gold value present in the
exact prompt sent to the model), **semantic recall** (gold value present in the
model's generated text, exact case-insensitive substring), latency, peak RSS,
model parameter digest before/after.

Controls:

- `memory_disabled` — same model, fresh empty substrate, same queries.
- `corrupted_context` — same model, substrate seeded with the *wrong* value for each
  fact. If the model emits the wrong seeded value, the answer came from the
  substrate, not from model knowledge.

Decision rule: H1 (**substrate continuity**) is **supported** if system id and chain
validity persist across all swaps and both kills, the in-flight kill leaves the last
committed checkpoint intact with no partial turn, gold context reaches every
queried model, and `memory_disabled` prompts never contain gold values.
**Semantic recall** is reported per model as k/n and is *not* required for H1; it
is the model's capability, not the substrate's.

## E4 — H3: self-correction from genuine independent feedback

Workload: 30 synthetic two-step arithmetic word problems (generator seed 4242, not
seen during development). Models: B and C (A is excluded because the native 14K
checkpoint scored 0/8 on the earlier self-correction set and has a 384-token window).

Arms after an independent first answer:

- `verifier_feedback` — a host checker compares the parsed integer to ground truth
  and, **only if wrong**, replies "Your answer is incorrect. Try again." It never
  reveals the answer.
- `sham_feedback` — the same message is sent after **every** first answer,
  right or wrong (tests whether models simply change answers when told to).

Primary: final accuracy of `verifier_feedback` vs first-answer accuracy
(wrong→right conversions), and vs `sham_feedback` (right→wrong damage).
H3 is **supported for a model** only if `verifier_feedback` final accuracy exceeds
first-answer accuracy by ≥ 3 problems (10 points) **and** `sham_feedback` does not
reach the same final accuracy. Otherwise null. Answer disclosure is never used.

## E5 — Autonomy challenge in a disposable sandbox

Three task levels in a fresh temporary directory generated from seed 777, with an
independent verifier holding the ground truth outside the sandbox:

1. read a named file and submit its code;
2. find which of four files contains a keyword and submit that file's code;
3. submit the sum of two numbers stored in two different files.

The model chooses one action per step from `list_files`, `read_file(name)`,
`submit(answer)`, returned as JSON. The host validates the JSON against this schema
and a path jail (names only; no separators, no `..`), executes it, and feeds back the
observation. Budget: 6 steps per task. There is no shell, network, write or
self-authorization capability. Level 3 starts with model C and, after its second
step, continues with model B using only the task trace stored in the substrate.

Reported: success per level and model, steps used, rejected actions, the full trace.
No success threshold is claimed in advance; every failure is retained.

## E6 — Bounded self-improvement of the routing weights

Component under improvement: the five R12 routing weights only. Proposal procedure:
coordinate search (step 0.05, weights renormalized to sum 1) on **training seeds
0–9 of E1+E2 workloads**, driven by the system's own recorded retrieval failures.
The baseline `WEIGHTS` constant and production code are not modified; the candidate
is written to a separate JSON file with its SHA-256.

A separate evaluator (a different function, different seeds 100–119, and an
**unseen workload template** — `The <noun> for <place> is <value>.` style facts and
paraphrased queries — which the proposer never sees) compares candidate vs baseline.

Decision rule: the candidate is **accepted as an improvement** only if held-out
hit@5 improves by ≥ 5 points with the paired bootstrap CI excluding zero on the
unseen template. Improvement on training seeds alone is explicitly insufficient.
Transfer to models is measured by downstream exact-recall with models B and C on 24
held-out queries under baseline vs candidate retrieval. Nothing is promoted.

## Interpretation limits (fixed in advance)

- Passing infrastructure checks is not evidence of intelligence.
- Retrieval changes are changes to external state and ranking, not model learning.
- Small models failing to use delivered context is a model limitation, reported
  separately from substrate delivery.
- No claim of consciousness, AGI, novel physics or general capability follows from
  any outcome.
