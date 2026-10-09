# Beast Awakens research inventory

Initial audit: 2026-10-08 at `aab168e607e5b9a896ead547bfeb88ffc499ccff` (PR #235). Reconciliation: 2026-10-09 on current main `4bc54300559bb2afa122df948e3bc49e45c962f1`, preserving PRs #236–238 and extending their one `beast.behavior` core. This inventory describes code and retained evidence. It does not claim a new model run, live hardware verification, owner-host installation, or independent scientific replication.

## Evidence boundaries

- **Implemented:** an inspected source path performs the stated operation.
- **Retained measurement:** a committed machine receipt or archive was inspected; hashes below were recomputed during this audit.
- **Reported measurement:** a results document identifies a historical run, but its remote full artifact was not downloaded or independently rerun in this audit.
- **Hypothesis or metaphor:** a proposed causal explanation or a descriptive name, not a measured property of a living or conscious system.

The current browser companion, Python DurableRuntime, native transformer architecture, and historical model-swap harness are related projects with different execution boundaries. They must not be presented as one automatically connected running organism.

## CST and Genesis: what exists

| Artifact | Actual operation | Boundary |
| --- | --- | --- |
| `docs/COSMIC_SYNAPSE_THEORY.md`, `docs/RESEARCH_LINEAGE.md` | Document the compact dynamical state / Gaussian attention hypothesis and corrected research lineage. | The imported historical state-ladder numbers are reported lineage, not a fresh result from this audit. They do not override controlled 006's null result. |
| `beastbox/dyn12.py`, `beastbox/state_family.py` | Public deterministic dyn12 recurrence, Gaussian affinity and state-liveness checks; coupled 42D state, 54D concatenation and larger comparative state families. | Public reference implementation, not a byte-equivalent reconstruction of a private historical Ω implementation. |
| `beastbox/models/phos_reference.py` | Independent PyTorch reconstruction of state-modulated causal attention. | Its LayerNorm, learned position embeddings and default 4× FFN differ from the native PHOS-derived model. |
| `models/rawrphos/architecture/model.py` | Native model: 192D width, four heads/layers, 4,096-token vocabulary, RMSNorm, RoPE, phi-scaled FFN, learned 12D state, Gaussian mix gate/sigma and prefix-correct cache. Standard, zero-gate, frozen-state and shuffled-state modes are available. | Attention state evolves during inference; this is not automatic model-weight training. A native checkpoint must separately be provisioned and verified. |
| `rust/cst-core/src/lib.rs` | Dependency-free public dyn12/Gaussian/attention mixture, phi width, Lorenz and affinity helpers. | This Rust crate is not loaded by the Next.js public rooms. |
| `beastbox/cns.py` | Software role orchestration and bounded state/provenance updates. | “Quantum”, “dark matter”, “awareness” and related role names are software labels, not measurements of physics, consciousness or biology. |
| `apps/beastbox-cloud/lib/creature-profile.ts`, `lib/creature-model.ts`, `lib/creature-glb.ts`, `lib/companion-roaming.ts` | Seeded fictional game traits, procedural appearance, GLB and bounded roaming. Appearance and game-stat random streams are separated. | Classical seeded game behavior. See `docs/COSMIC_GENESIS_SEEDED_CREATURES_20261002.md` and `docs/COSMIC_GENESIS_V2_3D_AND_ROAMING.md`. It does not create model authority or scientific measurements of intelligence. |
| `apps/beastbox-cloud/public/spark/{genome,qbeast,identity,runs}.mjs` | Deterministic genome/identity mapping and replay from recorded or simulator seed inputs; QBEAST integrity records and unsigned local growth remain distinct. | Recorded IBM counts are retained seed provenance. Simulator inputs must be labeled simulator inputs. Neither implies a fresh live-QPU call. |
| `beastbox/descendant/stage.py:create_genesis_manifest`, `scripts/create_d001_genesis.py`, `scripts/freeze_zeref_genesis.py` | Bind parent GGUF, canonical trainable reconstruction and reconstruction-proof hashes for descendant staging. | `historical_raw_parameters_recovered:false`, `historical_optimizer_continuity:false`, and `quantum_source_inherited_from_prime:"unknown_from_prime_artifact"` are explicit limitations. |
| `beastbox/heartbeat_seed.py` | Construct a waveform-derived five-qubit, four-layer, 4,096-shot program and validate an explicitly supplied hardware job/counts receipt. | The waveform is not claimed to supply quantum entropy. This function does not itself submit a live job or establish cognition. |
| `single_file/COSMIC_SEED_OF_TIME.py`, `docs/SEED_OF_TIME.md` | Owner CLI: local model chat, SQLite history, explicit owner WAV provenance and training-dataset export. | Separate owner workflow. A new prompt or export does not fine-tune model weights; the public browser does not receive the private heartbeat WAV. |

## Persistent Substrate A → B → A

The strongest retained historical continuity artifact is `evidence/system-closure-001/historical-swap-002.zip`, described by `docs/PERSISTENT_SUBSTRATE_MODEL_SWAP_002_FINAL_REPORT.md` and `docs/EVIDENCE_INDEX.md`. Its result schema is `persistent-substrate-model-swap-002-result-v1`, classification `COMPLETED_DESCRIPTIVE_MEASUREMENT`, and all nine structural gates are true.

| Item | Retained value |
| --- | --- |
| Historical source / run | `bd4108ac2f245262a25fd80463e84d9279eeead2` / Actions `33914200592` |
| ZIP SHA-256 | `1ebdf098a542e44eaf54ad9e8fefe3c74fafaeb8c280c41a1369dd58f810fd2d` |
| Internal `result.json` SHA-256 | `0bc2daf23b82d82992412b60c0b03c0cbf520a7e20f1bbb8ded5957c59d26fab` |
| A checkpoint | `zeref-pinned-active-checkpoint`; file SHA `454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425` |
| A0 / A2 loaded parameter SHA | Both `edf6501633ff26948a73815690e2f184c3e4025414c3ac2d64fbfec203307f7a` |
| B checkpoint | `HuggingFaceTB/SmolLM2-135M` revision `4e53f736cbb20a9a0f56b4c4bf378d9f306ff915` |
| Ledger / state continuity | 352 → 353 → 354 ledger records; 0 → 1 → 2 state steps/events; the same primary substrate object graph and identities |
| Verified delivered memory preference deltas | B1 `-0.13729238510131836`; A2 `+0.45259730021158884` |
| Controls | A-only schedule, genuinely empty-memory control (zero records), shuffled retrieval. All six A0 → A2 scoring restoration errors were zero. |

The requested alternate B revision `816ebadd0c024779e6657fdcfc1ab02bb9a7c473` returned 404; the historical reproduction explicitly records the available different revision. Memory was verified in the model inputs. This is evidence of software continuity and model-input delivery under frozen parameters, not proof of consciousness, biological life, human remembering, general semantic recall or quantum advantage.

Operational sources remain in `beastbox/persistent_substrate/` (`substrate.py`, `substrate_v2.py`, `runner.py`, `paired_runner.py`, `ledger.py`, `ledger_v2.py`, `real_models.py`, `models.py`, `prompts.py`, `protocol.py`, `evidence.py`, `metrics.py`, `offline.py`) and `scripts/run_persistent_substrate_model_swap_002.py`, `scripts/run_persistent_substrate_model_swap_002_frozen.py`, `scripts/run_persistent_substrate_offline_swap.py`. The historical archive is an evidence receipt, not a provider that the public UI can activate.

## Three different meanings of Hebbian learning

| Implementation | What changes | What uses that change |
| --- | --- | --- |
| `beastbox/memory.py:ReconciliationMemory` | SQLite token-pair associations (+0.25, capped at 100), salience and source-linked memory records; up to 32 unique tokens per update. | `beastbox/refractive_memory.py` uses association strength among five retrieval components. Consolidation creates thematic indexes without calling a model. |
| `beastbox/adaptive_control.py` | Bounded convex weights over existing spatial, lexical, Hebbian, recency and integrity retrieval components. | In-memory ranking changes from reviewed synthetic feedback. No model weights, owner authority or original memory text are rewritten. |
| `apps/beastbox-cloud/lib/companion/learn.mjs` | A real bounded 16×16 numeric matrix, hashed text features, vocabulary counts and next-word co-occurrences. | At the initial audit, replies read only word counts. The HF integration now reads a bounded association graph and the existing matrix for local replies and matching behavior scores. Browser responses remain pattern replies, not native CST attention or LLM training. |
| Native RAWRPHØS state attention | Learned model parameters set a recurrent inference state and attention affinity. | Attention computation consumes that state. Weight updates occur only in separate explicit training experiments. |

An in-memory source check in this audit started with matrix sum zero, observed `quiet star` twice, and measured matrix sum `0.9`, two observation steps and `next.quiet.star === 2`. At that initial baseline, zeroing the entire matrix left the same pattern reply unchanged. This explains the missing read path; the new controlled assay is published separately in [HF integration](BEAST_AWAKENS_HF_INTEGRATION.md). This is a mechanistic code check, not a learning-quality benchmark. Browser tokenization is ASCII based; it should not inherit broader Unicode behavior documented for other Python paths.

The browser's `session.mjs`, `adventure.mjs:rememberExchange` and `pet-dragon.mjs:noteModelActivity` preserve this distinction: local pattern updates / unsigned local game growth are not model-weight training. `swapBrain` changes a provider selection while checking the same Beast identity, XP, bond and observation steps; it does not regenerate a QBEAST genesis record.

## Actual experiments and unfavorable outcomes

| Experiment and exact artifact | Actual result | Scope and limitation |
| --- | --- | --- |
| `docs/experiments/COSMOS_LEARNING_CHALLENGE_001_RESULTS.md`; `cosmos-learning-challenge-001-receipt.json`; `scripts/cosmos_learning_challenge.py` | Correct-feedback MRR: within corpus `0.820833 → 0.885417` (+0.064584); separate transfer corpus `0.730655 → 0.816667` (+0.086012). Shifted wrong-feedback controls `0.389256` and `0.371696`. Empty memory produced zero candidates. | Actual Python AdaptiveControl/R12. Eight train plus eight transfer cases; five orderings of the same fixtures. Only two orderings adjusted weights, one correction each. Synthetic review flags are not human review. SQLite close/reopen is same-process evidence, not learned-weight recovery in a fresh interpreter. |
| `docs/experiments/COSMOS_SUBSTRATE_ACTIVATION_007_RESULTS.md`; `cosmos-substrate-activation-007-receipt.json`; `beastbox/activation.py` | Real DurableRuntime signals update dyn12 (L∞ delta `0.15616086681583677`), 42D/54D state, memory and associations. First-turn associations `0 → 501`, weight sum `0 → 127.75`; same identity and stored-fact retrieval after reopen, corrupt checkpoint rejected. **Frozen/adaptive held-out MRR both `0.8666666666666666`; delta 0; promotion failed.** | Provider A → B → C → A are reference fixture labels, not four verified models. Generative self-correction and actual model swap explicitly `NOT_EXECUTED_NO_VERIFIED_LANGUAGE_MODEL/CHECKPOINT`. Fixture autonomy objective failed; unparseable requests preserved. Zero external model prompts. |
| `docs/experiments/COSMOS_DYN12_CONTROLLED_006_RESULTS.md`; `cosmos-dyn12-controlled-006-summary.json`; `scripts/cosmos_dyn12_controlled_006.py` | Three seeds, separately trained native dyn12/standard/shuffled arms, 120 AdamW updates. Held-out accuracy `28.9063% / 31.1198% / 30.7292%`. The ≥+0.03 advantage over both controls in every seed **failed**. | Dyn12's exploratory four-binding shift accuracy `27.8646%` vs `22.1354% / 22.6563%` does not reverse the primary null. Losses `1.817846 / 1.826720 / 1.814122`. Small synthetic task; active parameters/FLOPs unequal; no production weight promotion. |
| `docs/experiments/COSMOS_SELF_CORRECTION_005_RESULTS.md`; `cosmos-self-correction-005-native18k-receipt.json`, `cosmos-self-correction-005-qwen0.5b-receipt.json` in the same directory | Native18K baseline / own review `0/8`; Qwen0.5B `3/8` unchanged. Neither model fixed an initially wrong case. Gold-assisted Qwen `5/8` is assisted correction, not self-correction. | Frozen real generators, eight synthetic problems and a 40-token cap. Novel transfer remained native `0/8`, Qwen `3/8`. Candidate gate failed. |
| `docs/experiments/BEASTBOX_ZERO_API_LOCAL_001_RESULTS.md`; `scripts/zero_api_experiment.py` | Actual DurableRuntime continuity with deterministic reference providers: six turns, 13 memories, `85.053 ms` wall, `79.092 ms` CPU, `28,572 KiB` peak RSS; no Python network/subprocess attempts. | Reference labels share one implementation; not a real-model experiment. Resource figures exclude unmeasured electricity / owner hardware. |
| `docs/experiments/BEASTBOX_ZERO_API_REAL_MODELS_002_RESULTS.md`; `scripts/zero_api_real_models_002.py`; run `36627512612` | Real frozen SmolLM2-135M-Instruct → Qwen2.5-0.5B-Instruct → SmolLM2. All 12 infrastructure gates passed, `23.34 s` wall, `40.39 s` CPU, `3,899,559,936` bytes peak memory. | Returning A did not generate the B memory keyword; R12 initially failed to select the B record and explicit recent-dialogue routing delivered it. Strict model-agent task failed. Linux namespace-scoped isolation and zero paid inference calls, not whole-host zero cost. Historical full artifact not downloaded here. |
| `docs/experiments/BEASTBOX_ZERO_API_ORIGINAL_NATIVE_003_RESULTS.md`; `scripts/zero_api_native_003.py`; run `36628787963` | Actual frozen native14K → SmolLM2 → native14K, 12/12 infrastructure checks, `15.913 s` wall / `27.706 s` CPU / `1,180,061,696` bytes peak memory. Memory delivered; free-generation recall failed. | Native 384-token window and lossy host prompt compaction. Model returned prose instead of strict task JSON; task failed. Separate from the public-model success below. Full historical artifact not downloaded here. |
| **Different 002:** `docs/experiments/BEASTBOX_ZERO_API_REAL_002_RESULTS.md`; `scripts/zero_api_real_models.py`; `lab/zero_api_real/` | Initial run `36627646099` used literal action examples. Stricter run `36628356524` failed on nested arguments. Prospectively revised exact flat-or-nested schema in run `36628867378` passed 11 structural gates and one Qwen-selected sum/write task (`7+11+6=24`). | V2: `21.566 s` wall, `37.720 s` CPU, `3,520,568 KiB` peak RSS, `98,304` bytes SQLite. One tiny constrained synthetic task, not generalized autonomy. SmolLM2 return recall still failed. Docker `--network none`; before/after provisioning and artifact transfer used network. Full historical artifact not downloaded here. |
| `docs/SEMANTIC_REAL_EVAL_RESULTS_001.md`; `SEMANTIC_REAL_EVAL_002_REPEAT_RECEIPT.json` | Pinned MiniLM on 24 positive-enriched SciFact queries. At 500 rows hybrid MRR fell `0.633333 → 0.598611` while recall rose; at 5,000 rows MRR `0.431944 → 0.440972`, recall `0.451389 → 0.694444`. Repeated reported values match to six decimals. | Cold 5,000-row embedding `138,330.19 / 183,649.71 ms`; warm scoring `108.10 / 112.71 ms`. Weak zero-dyn12/no-Hebbian control, small selected benchmark; not native training or general-intelligence evidence. |

### Recomputed retained artifact hashes

| Artifact | SHA-256 |
| --- | --- |
| `docs/experiments/cosmos-learning-challenge-001-receipt.json` | `0928b2333dc191d47857b252871acff3b4fff82065983e567772cb5b530db591` |
| `docs/experiments/cosmos-substrate-activation-007-receipt.json` | `91bcb3d28a6d8c25d4fbb2e061e6158108c8c1984c91b59864a17c83ef5dbc96` |
| `docs/experiments/cosmos-dyn12-controlled-006-summary.json` | `e64b5ae3819e09993016848d7849e19c5e195fa8e143b5dde61b4a5e74f08f57` |

Learning challenge fixture hash is `35e83ed28819f4382f4ad53efa62e5e5ebeb0e98e217962f8bcba4ab65fc8499`. No new expensive training, external model downloads or historical GitHub artifact fetches were performed for this inventory. Reported remote artifacts have historical retention limits; availability today was not verified.

## Hardware/quantum receipt stays negative

`evidence/final-whole-organism-001/release/FINAL_STATUS.json` records engineering isolation and historical IBM evidence verification, but **no fresh IBM execution**, **no causal intervention**, **no verified Zeref consumption**, **no new job IDs**, and `positive_quantum_or_physical_claim_allowed:false`. Classification: `ENGINEERING_ISOLATION_VERIFIED_CAUSAL_RESOURCE_SOURCE_NOT_ESTABLISHED`. This archive cannot be turned into a positive quantum advantage or physical-life claim, nor does it establish a universal negative outside its tested scope.

## Actual providers and the public boundary

| Path | Actual authority / behavior |
| --- | --- |
| `beastbox/rawrphos_local.py` | Default status can be `AVAILABLE_NOT_INSTALLED`. Actual native14K readiness requires checkpoint sidecar/step/hash attestation; expected checkpoint SHA `4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5`. No live host readiness was probed in this audit. |
| `beastbox/guest_local.py`, `apps/beastbox-cloud/app/api/guest/route.ts` | Stateless native14K guest path, bounded text and quota identity. Server verifies native model/step, no owner memory/tools/provider-key sharing. Public JSON only carries provider and message; no owner COSMOS runtime access. Unconfigured/unverified hosts fail explicitly. |
| `apps/beastbox-cloud/lib/companion/brain.mjs` | Verifies guest response provider/model/step/stateless boundary before treating its text as model output. A pattern answer is a different source. |
| `apps/beastbox-cloud/app/api/spark/chat/route.ts`, owner `/workspace` | Gated owner bridge and temporary owner context. Credentials and workstation options remain behind existing authorization. They are not public provider choices. |
| `beastbox/providers.py`, `beastbox/model_router.py` | Explicit owner local Ollama/native/reference/compatible provider adapters. Owner swap revokes prior grants and checks stable runtime identity, checkpoint sequence, memory and state. Python routing is not automatically executed by browser `swapBrain`. |
| `apps/beastbox-cloud/components/substrate-signals.tsx` | Existing owner Studio renders actual compatible substrate signal receipts; absent data is not replaced with invented metrics. This is a useful existing read-only receipt surface. |

## Recommended additive Lab integration

1. Keep the published historical Lab results. Add an inventory index with “retained receipt”, “reported historical run”, “browser-local pattern” and “not executed” labels. Link primary files above and show negative gates alongside successes.
2. Expose the selected canonical Beast's local ID, current runtime action, local pattern observation count and unsigned growth as **browser-local state**. Do not label its game metrics as measured artificial life, native CST training or owner runtime signals.
3. Reuse the actual 007 / challenge / 006 retained receipts for read-only research cards. Show frozen/adaptive/wrong-feedback controls and artifact hashes. The five challenge permutations are not five independent worlds.
4. Keep replay/scoring of public fixture receipts separate from new experiment execution. Existing Python runners are operational owner experiments; a browser port or authenticated runner adapter would be a distinct implementation with its own resource and authority boundary. Do not wire a fabricated “run experiment” button to historical numbers.
5. Let Brain Bay swap the existing unsigned provider selection while retaining one Beast/session. Default to the real deterministic on-device pattern path; guest only on explicit send; optional fixed-loopback Ollama only after explicit selection and send. A failed provider should be visibly unavailable and any pattern fallback named as pattern fallback.
6. Preserve all owner gates, checkpoint attestations and frozen history. A future useful scientific gate would preregister held-out outcomes and costs before execution, preserve failed controls, and collect actual model/receipt provenance. No current browser animation supplies those missing scientific outcomes.

## Reconciliation and Hugging Face connection

The unpublished early visual draft is retained in local checkpoint `0abd2c9a`; its competing runtime was not published. Current main already supplied the God Core, native framebuffer observations and Safari gesture fixes. This branch extends those implementations, keeps the same cartridge/player and recovers compatible public rooms and device journey work. [Pinned HF audit and fresh assay](BEAST_AWAKENS_HF_INTEGRATION.md) separates what was connected from what remains a separate native research workflow.
