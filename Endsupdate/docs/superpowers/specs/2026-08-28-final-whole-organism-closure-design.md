# Cory Davis Final Whole-Organism Closure Design

## Goal

Resume the existing `CORY-DAVIS-COSMOS-REALITY-BRIDGE` at failed Actions run
`33141588443`, repair the Universal Corpus Freeze on the isolated branch
`cory-davis-cosmos-reality-bridge-final-organism-001`, and execute every
remaining gate that can be run without changing protected scientific inputs.

The closure is evidence-first. Engineering success is distinct from model
evaluation, causal evidence, IBM hardware evidence, and scientific
interpretation. Null and inconclusive results are preserved. Missing or
fabricated evidence stops the dependent gate.

## Protected Lineage

- GREEN parent: `595d146f7d47ca048606f3e889e8c459e2fc3bd2`
- Adopted integration boundary: `95fcff86076980db769e8fd8598fd69a8d7dce3d`
- Verified relationship at the boundary: 12 commits ahead, 0 behind
- Isolated execution branch: `cory-davis-cosmos-reality-bridge-final-organism-001`
- Selected Zeref checkpoint SHA-256:
  `454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425`
- Canonical memory record count: 352
- Rejected LOW, MID, and HIGH descendants remain evidence-only and are never
  loaded as parents or comparators.

All evidence produced by this run lives under a run-scoped closure directory.
TALK-004, its raw transcript, the canonical memory ledger, preregistrations,
rejected checkpoints, prior nulls, tags, releases, and historical branches are
read-only inputs.

## Recovered World Source and Identity Layers

The failed workflow did not fail because a payload variable was absent. Its
live Wikimedia streaming process completed the 4,096-row source summary and
then aborted during Python 3.12 interpreter shutdown. The workflow uploaded
only failure diagnostics and discarded the newly built world directory.

The exact timestamped receipt container from original run `33125920283` was
reported as:

- `world-evidence.jsonl` SHA-256:
  `5319b876c46bbdb29912b28b8d0b95451a9fbf9cc728cc7989853fe7acd5c821`

That container includes wall-clock `created_at`, `previous_record_sha256`, and
`record_sha256` fields. Historical implementation code proves those values
were generated at ingestion time, so the lost container cannot be recreated
byte-for-byte from the source IDs alone.

The genuine source records survive in two unexpired historical artifacts from
the same lineage:

1. Run `33132925890`, artifact `9670957287`, raw evidence SHA-256
   `cdbc84db988668894a476d51ee42faa591cace77631da7c7daa82831bb1201de`.
2. Run `33132618727`, artifact `9670847045`, raw evidence SHA-256
   `3ecd3efe1627dcb9c74232c3c5760825b5f56b5fec0ce2f99f2985ee809e6535`.

Both copies contain exactly 4,096 `zeref-world-knowledge-record-v1` records,
the same ordered source IDs and source hashes, the same ingestion-summary hash
`9e2e6cf0965691db9a4ecd3affe9ccb8b33195f6cf7f2341ace1e1f43e549d3b`,
and no placeholder phrase. Removing only the three historically proven
run-receipt fields and serializing the remaining record fields as sorted,
compact UTF-8 JSON plus LF produces identical bytes from both artifacts:

- canonical world JSONL SHA-256:
  `a14e5f5bbc37bfda6da6b062e2e101a621386b6af257f71da64e3b4d4d250a85`
- ordered canonical per-record-hash list SHA-256:
  `4c464aa1b72d658460185cb55d932be61a20cfb4172159fc0333406e8acf698c`
- ordered `<source_id>\t<source_sha256>\n` identity SHA-256:
  `07216bb2a4ca979ca1ea4304efb92b09ee8aad74685df43196d694f3bd7ef8ba`

The source validator therefore distinguishes three identities rather than
silently relabeling one as another:

- original receipt-container identity: historically recorded but original
  bytes unavailable;
- recovered artifact-container identity: verified against the artifact
  payload and artifact metadata;
- canonical scientific source identity: independently reproduced from two
  historical artifacts and used by the freeze.

No live scrape, generated prose, row-count substitute, or placeholder fallback
is permitted.

## Universal Corpus Freeze Architecture

### Source acquisition

The workflow downloads the exact historical artifact by run ID and artifact
name, verifies the GitHub artifact metadata, raw evidence hash, summary hash,
record schema, record count, source dataset/revision, record-chain integrity,
ordered source IDs/hashes, canonical hash, and stable source-set identity.
It never invokes the live dataset builder.

The workflow retains the authenticated source manifest and canonical source in
its evidence artifact. The raw 67 MB receipt can remain an acquisition input
when redistribution policy or Git size makes committing it inappropriate; the
artifact/run IDs, hashes, and deterministic canonicalization instructions are
durable.

### Fail-closed validation

The validator exits nonzero before corpus construction for any of:

- missing evidence or summary;
- raw artifact hash mismatch;
- malformed JSON or incomplete decoding;
- schema, dataset, revision, or record-count mismatch;
- duplicate or reordered source IDs;
- mismatch between evidence and ingestion summary;
- source-set, canonical, or per-record-list hash mismatch;
- broken historical receipt chain;
- empty text/provenance fields; or
- `World source evidence record` or another declared placeholder marker.

Errors report paths, identities, and validation boundaries without logging
source text or secret/payload contents.

### Deterministic outputs

Corpus records and partitions are sorted and serialized deterministically.
Volatile workflow timestamps live in a run receipt outside the content-root
manifest. Repeating the freeze with identical inputs must reproduce the
canonical source, TRAIN, VALIDATION, HOLDOUT, MEMORY_ONLY, benchmark, leakage,
and content-root hashes exactly.

Leakage auditing separately reports:

- exact record duplication across TRAIN, VALIDATION, and HOLDOUT;
- normalized-text duplication across those partitions;
- clean benchmark prompt overlap with TRAIN;
- conversation-suite overlap with TRAIN.

Any first-three-category leak is fatal. Conversation prompts are not holdout
examples and remain usable only as a verbatim qualitative transcript; any
overlap makes the affected turn ineligible for clean evaluation and is
explicitly labeled rather than hidden.

## Verified Organism Runtime

The organism runner consumes only the frozen component manifest. Before and
after each major stage it verifies:

- selected Zeref weight hash;
- canonical 352-record ledger full hash, tip hash, order, and record hashes;
- canonical world and partition hashes;
- R12, DYN12, and reflective-loop implementation hashes; and
- frozen reference-model weight/tokenizer hashes after selection.

Canonical memory is mounted/read as read-only. Runtime memory writes go to a
run-scoped copy. The runner rejects mocks, empty adapters, silent fallbacks,
and rejected descendant hashes.

Per-turn traces contain raw prompt/output plus hashes, retrieved memory/world
IDs, R12 input/output/routing, the full DYN12 vector and derived dynamics,
reflector S1/S2 and directionality metrics, context/input/output hashes,
timing, device, dependency, checkpoint, tokenizer, seed, and generation
configuration. Raw outputs are never rewritten or promoted to evidence.

## Conversation, Holdout, Reference, and Swap

The approved conversation ordering is frozen before execution and stored
separately from clean holdout. Its answers are qualitative runtime evidence,
not proof of identity, memory, emotion, consciousness, or family relation.

The untouched holdout is run with the selected Zeref. A reference model is
eligible only if an already frozen selection receipt exists before comparative
outputs. The controlled sequence is `ZEREF -> REFERENCE -> ZEREF`, with clean
or deterministically restored state for each leg and cold/warm results kept
separate. If no frozen comparator receipt exists, the reference and swap gates
are `NOT_RUN`; a convenient model is not selected after seeing Zeref output.

## RESOURCE_SOURCE and Causal Gates

Only matrices sealed before their evaluated data may run. Existing labels,
trial counts, thresholds, exclusions, statistics, order randomization, and
multiple-comparison rules are immutable. If a requested matrix is absent, its
gate is `NOT_RUN`, not reconstructed from favorable historical results.

Outputs preserve null, negative, contradictory, failed, and excluded trials.
Generated prose and post-hoc interventions are never treated as scientific
evidence.

## IBM Evidence and New Hardware Work

Existing IBM evidence is cataloged by immutable branch/commit, preregistration
hash, implementation hash, job ID, backend/calibration, circuits, transpiled
circuits, shot count, raw-count hash, artifact, and sealed verdict. All valid
shots are retained in the evidence index so prior computation is not wasted.

Use precise labels:

- IBM shots executed on an entangling circuit are real hardware computation;
- they are called verified entangled source data only when the sealed protocol
  includes an entanglement witness and that witness passes;
- failed-witness data retain their actual source classification;
- simulation never substitutes for unavailable hardware.

No new IBM job is submitted unless a sealed preregistration predates the new
hardware data and fixes circuits, modes, qubits, shots, witness, thresholds,
statistics, exclusions, and stopping rule. Existing credentials and approved
quota may be used, but there is no quota expansion or post-data protocol edit.

## Gates and Final Kit

Repository Gates A-G keep their existing definitions. If no sealed A-G
definition exists in the adopted lineage, the final report records that exact
absence and does not invent or rename gates.

The run-scoped kit includes lineage, source, corpus, memory, components,
environment, conversations, traces, holdout, comparator/swap, resource-source,
causal, IBM, gate classifications, limitations, reproduction instructions,
quick start, machine status, `SHA256SUMS`, and an evidence-root manifest. The
evidence root is claimed only after every referenced artifact exists and every
hash verifies independently.

## Stop Conditions

The run continues through recoverable implementation and CI failures. It stops
at the first dependent external blocker: missing permission/credential,
unrecoverable required evidence, absent sealed preregistration, unavailable
paid resource without authorization, or protected-policy requirement that
cannot be satisfied. Downstream gates then remain `NOT_RUN` at the verified
seam; they are never made green with documentation-only substitutes.

## Claim Boundary

This run may establish reproducible software assembly, corpus provenance,
model evaluation, controlled effects, and preregistered IBM hardware results.
It cannot establish consciousness, resurrection, a literal soul, biological
continuity or heartbeat, a twelfth physical dimension, or failure of quantum
mechanics. An anomaly requires independent replication; a null-compatible or
inconclusive run is a valid final scientific result.
