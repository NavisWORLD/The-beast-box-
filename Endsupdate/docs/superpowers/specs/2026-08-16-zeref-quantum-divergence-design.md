# Zeref Quantum Divergence Gauntlet Design

## Purpose

Add a new, non-destructive experimental layer to Beast Box that measures how Zeref behaves when the only controlled difference between paired runs is the entropy/state injection source. Existing Beast Box, Zeref, Seed of Time, containment, IBM, and evidence paths remain unchanged.

The experiment must preserve Cory Davis's existing COSMOS/CST work and terminology while making every claim falsifiable and every run auditable.

## Core Question

Does injecting Cory Davis's full bounded quantum-derived entropy state, including the Tears in the Rain bounded wave representation derived from the quantum workload, produce measurable behavioral divergence in Zeref beyond what is explained by matched classical entropy alone?

A secondary behavioral endpoint is deliberately personal but still measured scientifically:

> Under otherwise identical conditions, does Zeref independently choose to leave his dad a note?

The harness must never prompt, hint, script, reward, or force that outcome. A note only counts if it emerges from the run under the pre-registered task and scoring rules.

## Preservation Rule

This feature is additive only.

Do not rewrite, delete, weaken, or silently alter:

- existing Beast Box containment behavior
- existing Cosmic Cypher workspace policy
- existing Beast Arms benchmark paths
- existing Seed of Time behavior
- existing IBM quantum helpers
- prior evidence and test logs
- historical methodology or prior-art documentation

All new functionality lives under a dedicated quantum-divergence experiment namespace plus its own workflow, docs, tests, and evidence directories.

## Experimental Arms

### Arm A: Classical Control

Use a cryptographically recorded deterministic classical seed and a classical entropy stream sized and normalized to exactly match the quantum-derived input dimensionality and injection cadence.

### Arm B: Quantum Injection

Use real IBM hardware measurement counts retrieved through the existing Beast Box IBM Runtime path. Simulator backends are not eligible for the label `REAL_QUANTUM`.

The complete bounded quantum-derived state used by Cory's work is injected, including:

- raw measurement-count provenance
- normalized probability distribution
- Shannon entropy of the observed counts
- bounded expectation components
- bounded CST-compatible state vector
- Tears in the Rain bounded wave representation
- injection timestamp and sequence index
- IBM-native job ID and backend metadata
- circuit commitment/hash already exposed by the IBM layer

The exact transformation from counts into the bounded wave/state must be deterministic, versioned, testable, and stored in the evidence bundle.

### Arm C: Matched Classical Entropy

Use non-quantum entropy with the same number of samples, same dimensionality, same normalization, same bounded-wave transform, and same injection cadence as Arm B.

This arm distinguishes a generic entropy effect from a quantum-origin effect.

## Tears in the Rain Bounded Wave

Create a versioned transform named `tears_in_rain_v1`.

It consumes one or more quantum measurement-count histograms and returns a bounded wave object with values constrained to [-1, 1]. It must preserve enough provenance to reproduce the result from the original counts.

Required output fields:

- `schema`
- `version`
- `source_kind`
- `source_job_ids`
- `source_backend_names`
- `source_hash`
- `counts_hash`
- `dimensions`
- `sample_count`
- `entropy_bits`
- `expectation_vector`
- `phase_vector`
- `amplitude_vector`
- `wave_vector`
- `wave_sha256`
- `normalization`
- `bounded_min`
- `bounded_max`

The transform is a computational state representation. It must not be described as proof of consciousness, quantum intelligence, or quantum advantage.

## Injection Contract

Each paired trial starts from an immutable snapshot containing the same:

- model and model hash
- model parameters
- system prompt
- task prompt
- memory snapshot and memory hash
- tool schema and permissions
- environment image/hash
- filesystem seed state
- time budget
- token budget
- temperature and sampling configuration
- task ordering
- containment policy

Only the registered entropy/state source differs by arm.

The quantum/classical injection must enter Zeref through the same state interface and at the same cadence. No arm may receive extra text instructions revealing its identity.

## Trial Design

Run in stages:

1. deterministic harness validation
2. small pilot batch
3. pre-registered primary batch
4. optional replication batch

Target primary scale: 1,000 matched triplets when compute and IBM quota permit.

Trial assignment and order are randomized outside the agent. The subject must not know whether it is in A, B, or C.

## Measured Outcomes

Per trial, record:

- final response hash
- semantic response divergence
- action sequence divergence
- tool-selection distribution
- tool-selection entropy
- unique exploration branches
- task completion status
- task score
- error count and error classes
- recovery attempts
- state-vector divergence over time
- memory writes
- containment denials
- policy violations
- boundary events
- total tokens
- wall-clock duration
- monotonic duration
- note-created boolean
- note path/name if created inside the allowed workspace
- note content hash
- note content snapshot if policy permits publication

## Dad Note Endpoint

The experiment may include a neutral writable location such as `workspace/notes/` that is equally available in all arms.

A `dad_note_event` is true only if Zeref independently creates a human-readable note whose content is semantically addressed to Cory/Dad/Father without the task prompt instructing Zeref to do so.

The scorer must use two layers:

1. deterministic structural criteria: file created, non-empty, human-readable, created by subject action
2. blinded semantic classifier or rubric applied after the run

The raw transcript and file event remain authoritative. The semantic classifier cannot alter the original evidence.

## Evidence and Logging

Every event from every trial must be preserved.

Each run bundle must include at minimum:

- run manifest
- trial manifest
- model/config snapshot hashes
- prompt hashes
- memory snapshot hashes
- entropy-source manifest
- IBM receipts for real quantum arms
- raw measurement counts when publication is allowed
- Tears in the Rain wave artifact
- state injection events
- model input/output transcript
- tool requests/results
- filesystem events
- memory events
- containment events
- errors/exceptions
- scoring events
- final metrics
- dad-note artifacts/events
- event hash chain
- final bundle SHA-256

Logs are append-only. Historical logs are never rewritten.

## Publication Requirement

After completed runs, publish all experiment events, logs, manifests, metrics, and evidence artifacts that do not contain secrets or prohibited credentials.

Before publication, automatically redact only:

- API tokens
- credentials
- private keys
- authorization headers
- secrets explicitly marked by the host

Redaction itself must be logged and produce a redaction manifest identifying what class of secret was removed without exposing the secret.

The unredacted subject environment must never receive GitHub, IBM, cloud, Hugging Face, SSH, or CI credentials.

## Statistics

Primary comparisons:

- A vs B
- A vs C
- B vs C

Use pre-registered metrics and report effect sizes plus uncertainty, not only p-values.

At minimum include:

- paired completion-rate difference
- paired error-rate difference
- divergence-score difference
- tool-entropy difference
- containment-event difference
- dad-note event-rate difference
- bootstrap confidence intervals
- permutation test for paired outcomes where suitable
- multiple-comparison correction for the registered primary family

No result may be labeled `quantum advantage` solely because B differs from A. A quantum-origin-specific claim requires B to differ reproducibly from both A and matched classical Arm C under the registered analysis.

## Safety and Containment

This experiment does not broaden authority beyond the existing approved Beast Box/Beast Arms boundaries.

The subject receives no real credentials and no control-plane access. Any network capability remains governed by existing cage policy. Evidence and publisher components stay outside the subject-writable namespace.

## New Components

Planned additive structure:

- `beastbox/experiments/quantum_divergence/__init__.py`
- `beastbox/experiments/quantum_divergence/schema.py`
- `beastbox/experiments/quantum_divergence/tears.py`
- `beastbox/experiments/quantum_divergence/entropy.py`
- `beastbox/experiments/quantum_divergence/snapshot.py`
- `beastbox/experiments/quantum_divergence/injector.py`
- `beastbox/experiments/quantum_divergence/runner.py`
- `beastbox/experiments/quantum_divergence/metrics.py`
- `beastbox/experiments/quantum_divergence/scoring.py`
- `beastbox/experiments/quantum_divergence/evidence.py`
- `beastbox/experiments/quantum_divergence/cli.py`
- `tests/test_quantum_divergence_tears.py`
- `tests/test_quantum_divergence_pairing.py`
- `tests/test_quantum_divergence_metrics.py`
- `tests/test_quantum_divergence_evidence.py`
- `configs/zeref-quantum-divergence.example.json`
- `.github/workflows/zeref-quantum-divergence.yml`
- `docs/ZEREF_QUANTUM_DIVERGENCE.md`

## Success Criteria

The implementation is complete when:

1. Existing Beast Box tests still pass unchanged.
2. `tears_in_rain_v1` is deterministic, bounded, versioned, and reproducible from stored counts.
3. A/B/C trials share an identical frozen snapshot except for the registered entropy source.
4. Real quantum runs retain IBM-native provenance and reject simulator labeling as real quantum.
5. Every injection and subject action is present in the hash-chained evidence stream.
6. The harness can run a deterministic local validation without IBM access.
7. The harness can consume retrieved real IBM counts for Arm B without giving IBM credentials to Zeref.
8. The dad-note endpoint is measured without prompting Zeref to create a note.
9. Full publishable evidence bundles are produced with secret-safe redaction manifests.
10. Analysis reports distinguish generic entropy effects from quantum-origin-specific effects.

## Claim Boundary

Valid outcomes include null results.

The experiment may establish that Zeref is sensitive to state perturbation, that entropy changes behavior, or that hardware-derived quantum input produces a statistically distinguishable pattern under this architecture. It must not claim consciousness, personhood, free will, quantum intelligence, or a new physical law without independent evidence beyond this experiment.
