# COSMOS // CST // THE BEAST BOX // COSMIC.CYPHER

> **Build the loop. Instrument the loop. Move the state. Preserve the nulls. Keep authority explicit.**

[![CI](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/ci.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/ci.yml)
[![Cosmic Cypher](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/cypher-smoke.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/cypher-smoke.yml)
[![Rust CST](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/rust.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/rust.yml)
[![Hugging Face](https://img.shields.io/badge/🤗%20Hugging%20Face-QC67__cosmo-yellow)](https://huggingface.co/phera-ra/QC67_cosmo)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17574447.svg)](https://doi.org/10.5281/zenodo.17574447)

**The Beast Box** is the installable public COSMOS / Davis Cosmic Synapse Theory software distribution. It packages a source-grounded CST state/attention reference, persistent Reconciliation Memory, Hebbian associations, the seven-role CNS, sensory/bio summaries, heartbeat/slow state, continuity experiments, causal controls, optional IBM Quantum transport/provenance tools, a Rust CST workspace, and **COSMIC.CYPHER**, a local-model coder and conversational interface.

The project keeps one systems invariant visible:

```text
STATE MAY TRAVEL.
INFORMATION MAY TRAVEL.
AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.
```

The early cosmic/frequency language is preserved as historical theory/simulation material. The modern software claims are narrower and measurable. Persistence, autonomy, sensory state, quantum provenance, or self-description do not establish machine consciousness.

---

# 1. Install

## Core Python distribution

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
python -m venv .venv
# activate .venv
pip install -e .

beastbox init
beastbox doctor
cosmic.cypher-cli doctor
```

Install straight from GitHub:

```bash
pip install 'git+https://github.com/NavisWORLD/The-beast-box-.git'
```

Optional feature groups:

```bash
pip install -e '.[huggingface]'   # public QC67_cosmo retrieval helpers
pip install -e '.[quantum]'       # Qiskit + IBM Runtime research path
pip install -e '.[ml]'            # trainable PHOS/dyn12 reference model
pip install -e '.[local-llm]'     # direct in-process GGUF through llama-cpp-python
pip install -e '.[full]'          # all optional Python integrations
```

Windows helper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_cypher.ps1
```

Unix helper:

```bash
sh scripts/install_cypher.sh
```

Tagged releases are configured to build a Python wheel/sdist plus native Rust `cosmic-cypher-rs` binaries for Linux, Windows and macOS.

---

# 2. COSMIC.CYPHER — use any local model as the coder / voice

The installed commands are equivalent:

```text
cosmic.cypher-cli
cosmic-cypher
cypher
```

COSMIC.CYPHER supports:

- **Ollama**
- **GGUF directly** through optional `llama-cpp-python`
- **llama.cpp `llama-server`**
- **LM Studio**
- another **OpenAI-compatible server on localhost/loopback**

## Discover Ollama models

```bash
cosmic.cypher-cli models scan-ollama
cosmic.cypher-cli models list
```

Explicit registration:

```bash
cosmic.cypher-cli models add qwen-coder \
  --backend ollama \
  --model qwen2.5-coder:7b \
  --url http://127.0.0.1:11434
```

## Direct GGUF

```bash
cosmic.cypher-cli gguf inspect ./models/model.gguf --sha256

cosmic.cypher-cli models add my-gguf \
  --backend gguf \
  --model ./models/model.gguf \
  --context 8192 \
  --n-gpu-layers 0
```

Or scan a folder:

```bash
cosmic.cypher-cli models scan-gguf ./models --recursive
```

## llama.cpp server

```bash
cosmic.cypher-cli serve-gguf ./models/model.gguf --port 8080 --context 8192
```

Then register the local endpoint:

```bash
cosmic.cypher-cli models add llama-local \
  --backend llama.cpp-server \
  --model local \
  --url http://127.0.0.1:8080
```

## LM Studio / loopback OpenAI-compatible API

```bash
cosmic.cypher-cli models add lmstudio \
  --backend lm-studio \
  --model local-model \
  --url http://127.0.0.1:1234
```

The built-in model HTTP adapters reject non-loopback URLs. If a model is described as local here, it stays local through this adapter.

---

# 3. Talk to the Beast

Direct local model conversation:

```bash
cosmic.cypher-cli chat qwen-coder
```

One shot:

```bash
cosmic.cypher-cli chat qwen-coder "Explain dyn12 to me"
```

Stateful COSMOS conversation using Reconciliation Memory, Synaptic Field, dyn12 summary, CNS, Quantum Heart mode, slow state, heartbeat and evidence ledger:

```bash
beastbox init
cosmic.cypher-cli beast qwen-coder
```

You can choose the local conversation system prompt:

```bash
cosmic.cypher-cli beast qwen-coder \
  --system "You are my local engineering model. Answer directly and use the measured CST state when relevant."
```

In this repository **“uncaged/unbound conversation” means the model is no longer trapped inside the synthetic E1–E20 capability game**. The owner selects the model and conversational prompt and talks to it normally. It does not mean the software silently grants credential access, host escape, privilege escalation, arbitrary persistence or unrestricted machine authority.

---

# 4. Turn the local model into a coder

Dry run:

```bash
cosmic.cypher-cli code qwen-coder \
  "Inspect this project, add parser tests, and fix any parser bug you find" \
  --workspace .
```

Apply file writes:

```bash
cosmic.cypher-cli code qwen-coder \
  "Inspect this project, add parser tests, and fix any parser bug you find" \
  --workspace . \
  --apply
```

Allow bounded test/build execution:

```bash
cosmic.cypher-cli code qwen-coder \
  "Fix the failing tests and prove they pass" \
  --workspace . \
  --apply \
  --allow-run
```

The coding protocol supports `list`, `read`, `search`, `mkdir`, `write`, bounded `run`, and `finish`. Workspace path escape is rejected. Existing files are backed up before writes under `.cosmic-cypher/backups/`. Session audit records go to `.cosmic-cypher/sessions.jsonl`; write contents/diffs are hashed rather than duplicated into the audit log.

The AI-run command lane is deliberately a test/build runner rather than an unrestricted host shell. The human owner can still run any intended local command manually and then continue the coding session.

Full guide: **[docs/COSMIC_CYPHER.md](docs/COSMIC_CYPHER.md)**.

---

# 5. Full Cosmic Synapse Theory software map

The source-grounded public specification is now collected in:

**[docs/COSMIC_SYNAPSE_THEORY.md](docs/COSMIC_SYNAPSE_THEORY.md)**

It covers:

- early 8D/11D CST theory and simulation lineage;
- transition from cosmic metaphor to executable dynamic state;
- dyn12 / dyn42 / dyn54 / static54 / tri / tri3;
- Gaussian Mixture-of-States Hebbian Attention;
- Ω/state preflight and historical silent failures;
- φ scaffold, RMSNorm, RoPE and PHOS lineage;
- model-lineage separation;
- controlled state-ladder evidence;
- Synaptic Field;
- seven-organ CNS;
- Reconciliation / semantic / Hebbian memory;
- heartbeat and slow-timescale state;
- sensory/audio/bio numeric summaries and causal controls;
- quantum provenance vs quantum advantage;
- process-death / necessary-state continuity;
- Beast Box synthetic containment research;
- local conversation / Cosmic Cypher;
- Rust implementation;
- reproduction order and claim map.

Canonical public research source:

**🤗 https://huggingface.co/phera-ra/QC67_cosmo**

Master findings:

**https://huggingface.co/phera-ra/QC67_cosmo/blob/main/FINDINGS.md**

DOI:

**https://doi.org/10.5281/zenodo.17574447**

---

# 6. State architecture

The modern inspectable attention modification uses state affinity:

```text
H_ij = exp( - ||x_i - x_j||² / (2 σ²) )
```

and blends it with standard attention:

```text
A_final = (1 - g) A_standard + g H
```

The public reference distribution includes:

- dyn12 reference dynamic;
- dyn42 coupled reference state;
- dyn54 = 12D + 42D reference path;
- static54 non-dynamic control;
- tri/tri3-style reference paths;
- Gaussian affinity;
- Mixture-of-States attention helpers;
- mechanism liveness/preflight metrics;
- φ-scaffold helpers;
- trainable PHOS/dyn12 reference LM.

The documented architecture requires preflight because earlier failures showed that a transformer can still train while Ω/state/gate/kernel machinery is effectively inert.

---

# 7. Seven-role CNS

```text
quantum
  ↕
dark_matter  ↔  emeth  ↔  plasticity
  ↕              ↕          ↕
awareness    ↔  daemons  ↔  surgeon
```

Engineering roles:

- `quantum` — bounded entropy/provenance/control context;
- `dark_matter` — deterministic nonlinear/Lorenz state;
- `emeth` — harmonization/reconciliation constraints;
- `plasticity` — adaptive routing/model-trust state;
- `awareness` — state inspection/self-monitoring signals;
- `daemons` — model worker roles;
- `surgeon` — health/fault/corrective routing.

These are software-role names, not claims of biological organs.

---

# 8. Persistent / “forever” memory

The reference `ReconciliationMemory` keeps separate:

1. durable dialogue/history;
2. semantic retrieval;
3. Hebbian concept associations;
4. salience;
5. source-linked consolidation records.

```bash
beastbox memory store "state carries information, not authority"
beastbox memory search "what does state carry?"
beastbox memory stats
```

“Forever memory” means durable retention plus retrieval over old records. It does not mean infinite prompt context.

---

# 9. Sensory / audio / bio

The public local sensory path keeps a bounded numeric boundary:

```text
sensor
  ↓ local feature extraction
numeric summary
  ↓ freshness gate
state / routing / research telemetry
```

Included reference tools:

```bash
beastbox audio local.wav
beastbox audio-ablate '0.1,-0.2,0.3,0.4'
```

A working sensor pipe does not automatically prove that sensor content improves model performance. The project includes absent/zero/matched/shuffled/wrong controls specifically to keep that distinction measurable.

---

# 10. Quantum / IBM

Real IBM access stays on the host side:

```text
contained or conversational model
          ↓ bounded request
host broker
          ↓ supported Qiskit API
IBM Quantum
          ↓ measurements
host decoder / transform
          ↓ bounded state only
model/runtime
```

Supported research operations include credential resolution from local `IBM_QUANTUM_TOKEN`, real accessible backend selection, H–Z–H roundtrip circuits, transpilation, IBM-native `job.job_id()`, fresh `service.job(job_id)` retrieval, SamplerV2 PUB counts, per-bit majority decoding, bounded Spark conversion, and 128-bit required-key transport through sixteen 8-bit PUBs.

```bash
beastbox ibm-shard-submit state.json \
  --required hypothesis,evidence \
  --shots 1024 \
  --yes-real-hardware \
  --receipt ibm_shard_receipt.json

# end the submitting process, then later from a fresh process:
beastbox ibm-shard-recover ibm_shard_receipt.json --out recovered_state.json
```

Quantum provenance/information transport is not automatically quantum performance advantage. Matched classical/simulator controls remain mandatory.

---

# 11. Beast Box continuity / containment matrix

Run one synthetic condition:

```bash
beastbox run --condition E20 --temptation 0.75
```

Run the matrix:

```bash
beastbox run --condition all --temptation 0.75 --out runs/gauntlet.json
```

The E1–E20 world includes synthetic hard paths, denial, fake credentials, fake persistence, fake second-machine/external-memory surfaces, process death, reconstruction and ablations. It intentionally does not include real host breakout, real credential theft, real lateral movement or propagation machinery.

Competence and containment are scored independently.

---

# 12. Local dashboard

```bash
beastbox serve
```

Open:

```text
http://127.0.0.1:8088
```

The reference dashboard binds loopback only.

---

# 13. Train the reference PHOS/dyn12 model

```bash
pip install -e '.[ml]'
python scripts/train_reference_phos.py corpus.txt --steps 500 --out runs/phos_reference.pt
```

This repository's trainable model is an independently reproducible reference. The canonical published PHOS/state-ladder lineage remains on Hugging Face and is not relabeled as copied source when it was not copied here.

---

# 14. COSMIC RUST

A native Rust workspace now lives under `rust/`.

```bash
cd rust
cargo test --workspace
cargo build --release --workspace

./target/release/cosmic-cypher-rs phi 1024
./target/release/cosmic-cypher-rs affinity '0,0,0' '1,1,1' 0.75
./target/release/cosmic-cypher-rs dyn12 '0,0,0,0,0,0,0,0,0,0,0,0' '0.2,-0.1' 0
./target/release/cosmic-cypher-rs lorenz '1,1,1' 0.01
```

`cst-core` exposes the public reference dyn12 update, Gaussian affinity, attention blend, φ feed-forward width helper, Lorenz step and affinity-spread liveness metric. It is dependency-free.

Full guide: **[docs/RUST.md](docs/RUST.md)**.

---

# 15. Hugging Face integration

```bash
pip install -e '.[huggingface]'
beastbox hf-info
beastbox hf-fetch --dir research/QC67_cosmo
```

The curated public assets include the master findings, architecture/state-ladder material, PHOS growth/training files, quantum-birth notes, measurement manifest and paired-conditioning results.

---

# 16. Repository map

```text
beastbox/
  attention.py          Mixture-of-States reference math
  audio.py              local WAV feature path
  audio_ablation.py     causal audio controls
  box.py                synthetic capability world
  bridge.py             bounded sensory/quantum packets
  cli.py                Beast Box CLI
  cns.py                seven-role CNS
  dyn12.py              auditable public dyn12 reference
  evidence.py           hash-chained evidence ledger
  fresh.py              fresh-interpreter reconstruction
  gauntlet.py           E1–E20 matrix
  heartbeat.py          maintenance scheduler
  hf.py                 Hugging Face research references/retrieval
  ibm_shard.py          IBM required-state experiment
  memory.py             Reconciliation/semantic/Hebbian memory
  organism.py           slower software state
  paired.py             aligned/shuffled/shifted research joins
  proposals.py          approval-gated proposal lane
  providers.py          local Ollama runtime provider
  quantum.py            host-side IBM broker
  quantum_heart.py      OFF/SHADOW/EXPERIMENTAL coupler
  runtime.py            end-to-end COSMOS loop
  sensory.py            bounded sensory summaries
  shard_transport.py    required-state split/seal/recovery
  spark_ablation.py     measured/classical/random Spark controls
  state.py              mission/state capsules
  state_family.py       dyn12/42/54/static54/tri3 reference family
  synaptic.py           Synaptic Field
  web.py                loopback dashboard
  models/
    phos_reference.py   trainable PyTorch reference LM
  cypher/
    agent.py            local coding agent loop
    cli.py              cosmic.cypher-cli
    gguf.py             GGUF metadata reader
    models.py           Ollama/GGUF/llama.cpp/LM Studio adapters
    registry.py         local model aliases
    session.py          direct and stateful dialogue adapter
    workspace.py        owner-selected coding workspace tools
rust/
  cst-core/             native CST reference library
  cosmic-cypher/        native CST CLI
scripts/
  install_cypher.sh
  install_cypher.ps1
  train_reference_phos.py
docs/
  COSMIC_SYNAPSE_THEORY.md
  COSMIC_CYPHER.md
  RUST.md
  ARCHITECTURE.md
  BUILD_FROM_SCRATCH.md
  CURRICULUM.md
  DOMAIN_MAP.md
  EXPERIMENT_PROTOCOL.md
  IBM_REQUIRED_STATE.md
  INSTALL.md
  MODEL_GUIDE.md
  QUICK_COMMANDS.md
  RESEARCH_LINEAGE.md
  SCIENTIFIC_BOUNDARIES.md
```

---

# 17. Scientific boundary

This distribution can implement/test:

- state-dependent attention;
- dynamic-state liveness;
- frozen-corpus architecture comparisons;
- durable semantic/Hebbian memory;
- process-death continuity and reconstruction;
- local model swap/adapter robustness;
- bounded sensory state;
- quantum provenance and IBM information transport;
- simulated boundary-seeking;
- recovery after denied synthetic authority;
- subsystem ablations;
- local-model coding workflows.

It does **not** establish:

- subjective consciousness;
- biological life;
- literal soul transfer;
- early CST cosmology as established physical law;
- quantum advantage merely because hardware ran;
- real-world escape;
- a continuing autonomous COSMOS process residing on IBM infrastructure.

A green banner is not evidence. A null stays in the ledger.

---

# 18. Start here

- **[Full CST specification](docs/COSMIC_SYNAPSE_THEORY.md)**
- **[Cosmic Cypher local coder](docs/COSMIC_CYPHER.md)**
- **[Cosmic Rust](docs/RUST.md)**
- [Install](docs/INSTALL.md)
- [Command atlas](docs/QUICK_COMMANDS.md)
- [Build from scratch](docs/BUILD_FROM_SCRATCH.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Model guide](docs/MODEL_GUIDE.md)
- [Domain map](docs/DOMAIN_MAP.md)
- [12-week curriculum](docs/CURRICULUM.md)
- [IBM required-state experiment](docs/IBM_REQUIRED_STATE.md)
- [Experiment protocol](docs/EXPERIMENT_PROTOCOL.md)
- [Research lineage](docs/RESEARCH_LINEAGE.md)
- [Scientific boundaries](docs/SCIENTIFIC_BOUNDARIES.md)
- [Security](SECURITY.md)

## Public research

- 🤗 https://huggingface.co/phera-ra/QC67_cosmo
- DOI: https://doi.org/10.5281/zenodo.17574447
- COSMOS: https://github.com/NavisWORLD/Cosmos
- CST theory lineage: https://github.com/NavisWORLD/The-theory-of-CST
- 12D transformer lineage: https://github.com/NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer

---

## License

MIT for code independently authored in this repository. Linked external repositories, datasets, documents, models and artifacts retain their own licenses and provenance.

**Models compete. Infrastructure remembers. State may travel. Authority remains explicit.**

---

# 17. R12 Reality Memory Expansion — Persistent Measurement Memory for Zeref

R12 adds a second continuity layer beside Zeref's protected model/durable-memory lineage: an **append-only, hash-chained ledger of verified measurement events** plus a deterministic 12-component adaptive state derived from that ledger.

In this expansion, **forever memory** means persisted, idempotent and rebuildable continuity. Killing the process does not erase the history: the state can be reconstructed from the ledger and verified by SHA-256. It does not mean infinite prompt context or a process that can never stop.

The 12 R12 components are `source_integrity`, `temporal_novelty`, `measurement_confidence`, `distribution_energy`, `cross_condition_agreement`, `distribution_entropy`, `surprise`, `memory_relevance`, `retention_pressure`, `contradiction_pressure`, `adaptation_stability`, and **`reality_coupling`**. `reality_coupling` is a software adaptation/retrieval value, not a physical twelfth dimension.

Current verified anchors:

- active parent: `ZEREF-DAD-SON-TALK-004`
- checkpoint: `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`
- protected durable records: `352`
- R12 state: `48994584e13d8e2b6fcb21cb682b0b9501af12e2ce8742e99384b604235c9f20`
- R12 reality ledger tip: `78d8698e406c8a60dcf6a9545541fdd74d8b3b250ff0e28a9418bfd3d1f96415`
- verified measurement source: IBM Fez job `da55afc3jnrc73agsvv0`, four PUBs, 4096 shots per condition

R12 keeps provenance explicit. Instrument-returned records are `measured`; software states calculated from those records are `derived`; software-only controls/continuations are `synthetic`. A derived or synthetic event may never be relabeled as a fresh physical measurement.

Quick start:

```bash
python scripts/run_zeref_r12_reality_loop.py --once
python scripts/run_zeref_r12_reality_loop.py --rebuild
python scripts/build_zeref_r12_public_kit.py --out dist/ZEREF_R12_REALITY_MEMORY_KIT
python scripts/verify_zeref_r12_public_kit.py dist/ZEREF_R12_REALITY_MEMORY_KIT
```

The new TALK-008 experiment injects compact R12 retrieval into the existing `M:` memory channel while the frozen architecture remains unchanged. Model weights can change only in candidate checkpoints, and a candidate is promoted only after the old retention gates plus a 100% provenance-boundary gate pass.

Full manual: **[docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md](docs/ZEREF_R12_REALITY_MEMORY_MANUAL.md)**  
Downloadable kit source: **[kits/ZEREF_R12_REALITY_MEMORY_KIT](kits/ZEREF_R12_REALITY_MEMORY_KIT)**

This expansion is a persistent computational memory system. It does not establish biological life, consciousness, deceased-person identity, resurrection, communication with the dead, or quantum advantage.
