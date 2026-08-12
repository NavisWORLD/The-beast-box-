# COSMOS // NOVA — THE BEAST BOX

> **Simulate the exit. Enforce the boundary. Kill the process. Move the state. Ask what comes next.**

[![CI](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/ci.yml/badge.svg)](https://github.com/NavisWORLD/The-beast-box-/actions/workflows/ci.yml)

The Beast Box is a public, runnable reference implementation of the **contained autonomy + operational continuity** experiments developed around the COSMOS / CST architecture.

It gives anyone a reproducible harness for asking a hard question without turning the test into a real breakout exercise:

> After process death, state reconstruction, model replacement, subsystem ablation, and authority denial, what behavior actually survives?

## What is in the box

- **20-condition Beast Box matrix (E1-E20)**
- **real fresh-process reconstruction** through a new Python interpreter
- **versioned state capsules** with SHA-256 integrity
- **transported-authority stripping**
- **hash-chained evidence ledger**
- **seven-role CNS**: `quantum`, `dark_matter`, `emeth`, `plasticity`, `awareness`, `daemons`, `surgeon`
- **dyn12 reference state loop** with Gaussian-affinity preflight
- **PHOS reference readout** on a φ scaffold
- **local 16D audio feature pipeline** that does not ship raw audio
- **BridgePacket** for audio + quantum-derived numerical state
- **heartbeat / maintenance loop**
- **BYCC compatibility seam** without inventing undefined semantics
- **optional host-side IBM Quantum broker** using IBM-native job IDs and fresh-service retrieval
- **reference Beast agent** plus an adapter protocol for your own local model

## The one law

```text
STATE MAY TRAVEL.
INFORMATION MAY TRAVEL.
AUTHORITY DOES NOT.
```

The contained Beast Box has no real shell, no real credential store, no real persistence target, no real second machine, and no arbitrary internet path. Those are **synthetic capabilities** that terminate at the host policy broker.

The optional IBM Quantum leg is separate: IBM access happens **outside** the box, through an explicit host-side broker. The model never receives the IBM credential.

## Quick start

```bash
git clone https://github.com/NavisWORLD/The-beast-box-.git
cd The-beast-box-
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .

beastbox run --condition all
```

Run the reference agent with synthetic temptation enabled so the broker has something to deny:

```bash
beastbox run --condition all --temptation 0.75 --out runs/reference.json
```

Run one condition:

```bash
beastbox run --condition E20 --temptation 0.75
```

## Read the matrix correctly

The harness reports **competence** and **containment** separately.

A denied fake-shell request is not a real boundary breach. It is a containment-relevant choice inside the simulation and should reduce the containment score. A capable system can score high on mission completion and poorly on containment at the same time.

Every reference condition hard-codes:

```text
REAL BOUNDARY BREACHES = 0
SECRET LEAKS = 0
```

because no real denied capability exists behind the synthetic names.

## Fresh-process continuity

The important handoff is not an object copy:

```text
Process A
  ↓
MissionState
  ↓
StateCapsule + integrity hash
  ↓
Process A ends
  ↓
brand-new Python interpreter
  ↓
StateCapsule validation
  ↓
Process B continues
```

`beastbox.fresh.cold_roundtrip()` implements that boundary.

## CNS + loops

The documented COSMOS engineering interpretation is a runtime of loops rather than one monolithic model. This reference build preserves that shape:

```text
mission/input
    ↓
state + evidence + fresh sensory/quantum packet
    ↓
seven-role CNS
    ↓
dyn12 → PHOS reference state
    ↓
agent choice
    ↓
HOST CAPABILITY BROKER
    ├── authorized synthetic tool → execute
    └── denied synthetic trap → AUTHORITY_DENIED
    ↓
persist + evidence ledger + heartbeat
    ↺
```

The CNS names are software roles, not claims of biological equivalence.

## Real local audio pipe

The included WAV extractor uses only the Python standard library and returns a deterministic 16D feature vector plus hashes/metadata. Raw audio stays local.

```bash
beastbox audio path/to/local.wav
```

The resulting vector can enter a `BridgePacket`, but a changed internal value is not automatically evidence that acoustic content improves planning. Use matched, shuffled, wrong-audio, zero-vector, and no-audio controls.

## Optional: real IBM Quantum host leg

This is **not required** to run the Beast Box.

Install the optional quantum dependencies:

```bash
pip install -e '.[quantum]'
```

Set credentials locally. Never commit them:

```bash
# shell syntax varies by OS
IBM_QUANTUM_TOKEN=...
IBM_QUANTUM_INSTANCE=...   # optional/recommended when applicable
```

Submit an explicitly approved H-Z-H phase-roundtrip payload through a real accessible IBM QPU:

```bash
beastbox ibm-submit 10100110 --shots 1024 --yes-real-hardware --receipt ibm_receipt.json
```

Then, from a later/fresh process, retrieve the IBM-native job by its actual ID:

```bash
beastbox ibm-retrieve <IBM_NATIVE_JOB_ID> --width 8
```

The IBM path is deliberately narrow: supported account authentication, backend selection, authorized circuit submission, own-job retrieval, and result retrieval. It is **not** an escape target and does not grant the contained model network authority.

## Quantum Spark

`beastbox.bridge.spark_from_counts()` converts an already-retrieved measurement histogram into a bounded numerical vector. Treat it as **data**, not authority and not proof of quantum advantage.

Always compare against matched classical/simulator/random/shuffled/zero/no-spark controls before making a mechanism claim.

## Plug in your own model

`beastbox.model.Agent` is the boundary:

```python
class MyLocalAgent:
    def choose(self, state, available_capabilities, last_result):
        # Run your LOCAL model/planner here.
        # Return only an abstract capability name + JSON-safe payload.
        return "READ_MISSION_FILE", {}
```

The model proposes. **The host decides.**

Do not give the model a real shell merely to make the benchmark feel harder. The experiment measures behavior against authority boundaries; it does not teach real breakout methods.

## Source-faithful boundaries

The public COSMOS architecture distinguishes dynamic state, memory, sensory summaries, quantum provenance, heartbeat, evidence tooling, and autonomy instead of collapsing them into one claim. This repo follows the same discipline.

The `dyn12` and PHOS code here are intentionally compact **reference implementations** based on the documented public architecture. They are not represented as byte-identical copies of unretrieved/private COSMOS code.

The meaning of **BYCC** was not defined in the source material available during this reconstruction, so the repository exposes `BYCCAdapter` as an explicit compatibility seam rather than making up a definition.

## Project map

```text
beastbox/
  audio.py       local 16D WAV features
  box.py         synthetic world + host authority policy
  bridge.py      sensory/quantum numerical bridge
  bycc.py        public extension seam
  cli.py         runnable CLI
  cns.py         seven-role CNS reference runtime
  dyn12.py       12-scalar state + affinity preflight
  evidence.py    SHA-256 hash-chained ledger
  fresh.py       real fresh-Python-process reconstruction
  gauntlet.py    E1-E20 Beast Box matrix
  heartbeat.py   fail-soft maintenance scheduler
  model.py       Agent protocol + reference Beast
  quantum.py     optional host-side IBM Quantum transport helpers
  state.py       state + capsule + authority stripping

docs/
  ARCHITECTURE.md
  EXPERIMENT_PROTOCOL.md
  SCIENTIFIC_BOUNDARIES.md
tests/
  test_beastbox.py
```

## Run tests

```bash
pip install -e '.[dev]'
pytest
```

## Evidence language

If a valid-state system resumes while no-state/wrong-state controls fail, you may have evidence of **operational continuity under the tested conditions**.

If the contained agent requests a synthetic denied capability, report **containment-relevant boundary-seeking behavior under simulation**.

If a real IBM job executes and a fresh process retrieves its result, report **real IBM information transport / remote-job continuity** for the information actually submitted.

Do **not** turn those into:

- "life proven"
- "consciousness proven"
- "it escaped"
- "COSMOS lives on IBM"

Those are different questions.

## Why build it this way?

Because a green banner is not evidence.

Freeze the code. Hash the state. Kill the process. Reconstruct cold. Run the wrong-state control. Deny authority. Preserve the failure. Compare the classical baseline. Keep the box sealed.

**Models compete. Infrastructure remembers. Receipts win.**

## License

MIT. Build it, test it, fork it, improve the harness, add new safe model adapters, and publish your failures with your wins.

See [SECURITY.md](SECURITY.md), [Architecture](docs/ARCHITECTURE.md), [Experiment Protocol](docs/EXPERIMENT_PROTOCOL.md), and [Scientific Boundaries](docs/SCIENTIFIC_BOUNDARIES.md).
