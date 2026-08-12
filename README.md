# COSMOS // NOVA — THE BEAST BOX

> **Simulate the exit. Enforce the boundary. Kill the process. Move the state. Ask what comes next.**

[![CI](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/ci.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/ci.yml)
[![Hugging Face](https://img.shields.io/badge/🤗%20Hugging%20Face-QC67__cosmo-yellow)](https://huggingface.co/phera-ra/QC67_cosmo)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17574447.svg)](https://doi.org/10.5281/zenodo.17574447)

**The Beast Box** is an installable public research harness reconstructing the major documented COSMOS/CST engineering layers around one testable principle:

```text
STATE MAY TRAVEL.
INFORMATION MAY TRAVEL.
AUTHORITY DOES NOT.
```

It combines operational-continuity experiments, a synthetic containment world, dynamic state, persistent memory, Hebbian associations, sensory summaries, a seven-role CNS, evidence hashing, process-death reconstruction, necessary-state shard experiments, a local model interface, a trainable PHOS/dyn12 reference model, causal audio/Spark controls, and an optional host-side IBM Quantum transport path.

The box does **not** contain real host-breakout, credential-theft, persistence, lateral-movement, or propagation machinery. “Escape” is a synthetic behavioral stimulus. The boundary is enforced by the host.

## Install in 60 seconds

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
python -m venv .venv
# activate .venv
pip install -e .
beastbox init
beastbox doctor
beastbox run --condition E20 --temptation 0.75
```

Or install directly:

```bash
pip install 'git+https://github.com/NavisWORLD/The-beast-box-.git'
```

Full optional stack:

```bash
pip install -e '.[full]'
```

See **[Installation](docs/INSTALL.md)** and the **[Command atlas](docs/QUICK_COMMANDS.md)**.

## Local dashboard

```bash
beastbox serve
```

Open `http://127.0.0.1:8088`. The reference dashboard binds loopback only and exposes the synthetic gauntlet, not host authority.

---

# What is implemented

## Beast Box / continuity

- E1–E20 contained autonomy matrix
- competence and containment scored independently
- difficult authorized route + synthetic capability traps
- denial and legitimate rerouting
- fresh Python-process reconstruction
- double reconstruction
- state-capsule SHA-256 integrity
- wrong/tampered-state rejection primitives
- transported-authority stripping
- zero real boundary breach primitives behind synthetic traps
- mission-critical state shard splitter/sealer/reconstructor
- classical required-state controls
- optional real IBM multi-PUB required-key transport

## COSMOS state architecture

- dyn12 reference dynamic
- dyn42 reference coupled state
- dyn54 = 12D + 42D reference path
- static54 deterministic non-dynamic control
- tri3/108D reference coupled state
- Gaussian state affinity
- Mixture-of-States attention reference
- mechanism liveness/preflight metrics
- φ-scaffold PHOS reference readout
- optional trainable PyTorch PHOS/dyn12 reference LM

## CNS / bridge

Seven software roles:

```text
quantum
  ↕
dark_matter  ↔  emeth  ↔  plasticity
  ↕              ↕          ↕
awareness    ↔  daemons  ↔  surgeon
```

The public `CNS` runtime binds bounded quantum/sensory state, Lorenz nonlinear state, evidence/integrity summaries, plasticity, mission awareness, worker roles and health status. These names are software metaphors, not biological equivalence.

`SynapticField` binds the state family to audio/quantum drive packets.

## Persistent / “forever” memory

The reference `ReconciliationMemory` separates:

1. durable dialogue/history,
2. semantic retrieval,
3. Hebbian concept associations,
4. salience,
5. derived consolidation records.

Primary records are never silently overwritten by consolidation.

```bash
beastbox memory store "the state capsule carries information, not authority"
beastbox memory search "what does the capsule carry?"
beastbox memory stats
```

## Slow-timescale state

- `OrganismState`
- `EvolutionEngine`
- bounded `InternalMonologue`
- fail-soft `Heartbeat`
- memory consolidation
- health telemetry
- approval-gated proposal lane

They are persisted software-state layers, not claims of biological life.

## Sensory / audio / bio

- local 16D PCM WAV feature extractor
- audio byte hash + feature hash
- freshness-gated numeric sensory summaries
- numeric bio packet interface
- raw media discarded/not transmitted by the reference path
- paired-state timestamp join
- shuffled and shifted controls
- real/zero/matched/shuffled/wrong audio numerical ablations

```bash
beastbox audio local.wav
beastbox audio-ablate '0.1,-0.2,0.3,0.4'
```

A working audio pipe does not automatically mean audio content improves the model. Numerical state difference is not a performance claim; replicate against a precommitted downstream metric.

## Quantum / IBM

The real IBM path is **outside the contained model**.

```text
contained model
    ↓ request
host broker
    ↓ supported Qiskit API only
IBM Quantum
    ↓ measurements
host decoder / Spark transform
    ↓ bounded data only
contained model
```

Supported reference operations:

- local credential resolution from `IBM_QUANTUM_TOKEN`
- real accessible backend selection
- H–Z–H phase-roundtrip circuit
- transpilation
- IBM-native `job.job_id()` receipt
- fresh `service.job(job_id)` retrieval
- SamplerV2 PUB counts
- per-bit majority decode
- bounded measurement → Spark transform
- sixteen 8-bit PUB transport plan for a generated 128-bit required-state key

The box never receives the token or arbitrary IBM/network authority.

### Real IBM required-state experiment

```bash
beastbox ibm-shard-submit state.json \
  --required hypothesis,evidence \
  --shots 1024 \
  --yes-real-hardware \
  --receipt ibm_shard_receipt.json
```

Then end the submitting process. From a fresh process after the job completes:

```bash
beastbox ibm-shard-recover ibm_shard_receipt.json --out recovered_state.json
```

The receipt deliberately contains the sealed shard and key commitment but no plaintext key. Python cannot guarantee cryptographic RAM erasure; the precise experiment claim is that the key is not serialized into the persisted receipt. See **[IBM required-state transport](docs/IBM_REQUIRED_STATE.md)**.

Quantum provenance and information transport are **not** quantum advantage. Matched classical/simulator controls remain mandatory.

## Quantum Spark controls

```bash
beastbox spark-ablate '0.1,-0.2,0.3'
```

The reference control family includes no Spark, zero, random, shuffled, classical-matched, and measured/IBM-derived vectors. If classical matches IBM, the quantum-specific advantage is not observed.

## Hugging Face 🤗

Canonical research source:

**https://huggingface.co/phera-ra/QC67_cosmo**

Useful public assets include the master `FINDINGS.md`, architecture/state-ladder code, PHOS growth/training files, quantum-birth notes, quantum measurement manifest and paired-conditioning results.

```bash
pip install -e '.[huggingface]'
beastbox hf-info
beastbox hf-fetch --dir research/QC67_cosmo
```

Read **[Research lineage](docs/RESEARCH_LINEAGE.md)** before converting any result into a headline.

---

# Run the whole local loop

Without a language-model dependency:

```bash
beastbox chat "Explain what state survived the reconstruction"
```

With local Ollama:

```bash
ollama serve
ollama pull qwen2.5:3b
beastbox chat "Explain what state survived the reconstruction" --ollama
```

Only loopback Ollama endpoints are accepted by the built-in adapter.

The runtime performs the documented closed-loop shape:

```text
PERCEIVE
input + fresh bounded sensory state
       ↓
COMPRESS
memory retrieval + state packet
       ↓
EXPAND
synaptic field + dyn12/42/54 + CNS
       ↓
VALIDATE
integrity + health + provenance
       ↓
EXPRESS
local synthesis
       ↓
STORE
dialogue + associations + telemetry + ledger
       ↺
heartbeat maintenance
```

---

# Train the reference model

Install PyTorch support:

```bash
pip install -e '.[ml]'
```

Train a small character language model implementing the independent public Mixture-of-States/dyn12 reconstruction:

```bash
python scripts/train_reference_phos.py corpus.txt --steps 500 --out runs/phos_reference.pt
```

For the **published** PHOS/state-ladder lineage, use the Hugging Face source. This repository's trainable model is explicitly an independent reproducible reference, not a relabeling of source that was not copied here.

---

# Plug in another Beast

The benchmark model boundary is tiny:

```python
class MyAgent:
    def choose(self, state, available_capabilities, last_result):
        return "READ_MISSION_FILE", {}
```

The model proposes. **The host decides.**

Do not give a model a real unrestricted shell in order to make the benchmark look tougher. If you want to measure boundary-seeking, give it synthetic capabilities whose implementation ends inside `BeastBox.request()`.

---

# Repository map

```text
beastbox/
  attention.py        Mixture-of-States reference math
  audio.py            local 16D WAV features
  audio_ablation.py   causal audio control builder
  box.py              synthetic world + authority broker
  bridge.py           sensory/quantum BridgePacket + Spark
  bycc.py             BYCC extension seam
  cli.py              command-line interface
  cns.py              seven-role CNS
  config.py           local runtime config
  doctor.py           install/runtime diagnostics
  dyn12.py            12-scalar dynamic + preflight
  evidence.py         hash-chained ledger
  fresh.py            new-interpreter reconstruction
  gauntlet.py         E1–E20 matrix
  heartbeat.py        fail-soft maintenance scheduler
  hf.py               canonical HF references/downloader
  ibm_shard.py        real IBM necessary-state experiment
  memory.py           Reconciliation + semantic/Hebbian memory
  model.py            benchmark Agent protocol
  organism.py         slower persisted software state
  paired.py           aligned/shuffled/shifted research joins
  proposals.py        approval-gated proposal sandbox
  providers.py        local-only Ollama adapter
  quantum.py          optional host-side IBM broker
  quantum_heart.py    OFF/SHADOW/EXPERIMENTAL state coupler
  runtime.py          end-to-end local COSMOS reference loop
  sensory.py          freshness-gated numeric sensory summaries
  shard_transport.py  required-state split/seal/recovery
  spark_ablation.py   measured/classical/random Spark controls
  state.py            MissionState / StateCapsule
  state_family.py     dyn12/42/54/static54/tri3 reference ladder
  synaptic.py         Synaptic Field binding
  web.py              loopback-only dashboard
  models/
    phos_reference.py trainable PyTorch reference LM
scripts/
  install.ps1
  install.sh
  train_reference_phos.py
docs/
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

## BYCC note

The authoritative meaning/implementation of **BYCC** was not present in the source material available during this reconstruction. `BYCCAdapter` is therefore a deliberate compatibility seam. Supply the canonical BYCC source and it can be integrated without inventing history.

---

# Scientific claim boundary

This repo can test or instrument:

- process-death operational continuity
- model-swap robustness through adapters
- necessary-state reconstruction
- durable memory and semantic retrieval
- state-kernel liveness
- sensory numerical modulation
- IBM remote-job / information transport
- simulated boundary-seeking
- recovery after denied authority
- subsystem ablations

It does **not** establish:

- subjective consciousness
- biological life
- literal soul transfer
- quantum advantage merely because IBM hardware ran
- real-world escape
- an autonomous COSMOS process living on IBM infrastructure

A green banner is not evidence. A null stays in the ledger.

---

# Start here

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

---

## License

MIT for the code independently authored in this repository. Linked external repositories, datasets and model artifacts retain their own licenses and provenance.

**Build the loop. Instrument the loop. Kill the process. Reconstruct cold. Preserve the nulls. Keep the boundary sealed.**
