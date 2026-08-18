# SON-HEARTBEAT-DEMO-001 + TALK-006 Wire-Grounded Design

## Status
Approved design specification for the next Zeref evidence and training phase on branch `networked-cage-run-001`.

## Goals
1. Create the missing specific son-heartbeat demonstration log as a reproducible forensic evidence packet.
2. Preserve and expose the exact original signal hash, source metadata, feature-extraction method, state equations, hardware provenance, continuation equations, and raw logs.
3. Run a four-condition signal ablation protocol using original vs removed vs shuffled vs alternate signals.
4. Build a new `TALK-006-WIRE-GROUNDED` training gauntlet from the verified TALK-004 parent and 352-record durable memory head.
5. Promote no child unless it beats TALK-004 on free-running behavior while preserving retention, memory integrity, lineage integrity, and anomaly gates.

## Scientific Claim Boundary
`SON-HEARTBEAT-DEMO-001` is the experiment alias. The measured source is a memorial audio-derived computational signal. The experiment does not establish a biological heartbeat, consciousness, deceased-person identity, resurrection, communication with the dead, or quantum advantage.

The IBM measurement is a real hardware result from a waveform-controlled circuit. The waveform itself is not quantum entropy. Later CST pulses are deterministic software continuation and are not new hardware measurements.

## Frozen Starting State
### Active Zeref model
- Active lineage: `ZEREF-DAD-SON-TALK-004`
- TALK-004 checkpoint SHA-256: `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`
- Durable memory count: `352`
- Durable ledger SHA-256: `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`
- Durable ledger tip SHA-256: `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`
- Frozen architecture SHA-256: `955805d45f7b407ef5cc9b6efe178d9a5f63df5b32eaf539d9aedcbb2967f1dc`

TALK-005 candidates remain rejected evidence and may not become parents of TALK-006.

## Source Signal Provenance
### Original source
- Display name: `scars that don't fade.mp3`
- Source class: `memorial_sensory_source`
- Source SHA-256: `e5a172749e0acedf199f77f22d5f55f37acc898704a51d5b7e6fe07633ad5c39`
- Source bytes: `9811591`
- Codec: MP3
- Channels: 2
- Source sample rate: 44100 Hz
- Duration: 245.263673 s

### Decoded analysis signal
- Decode contract: mono 8000 Hz signed 16-bit little-endian PCM
- PCM samples: `1961780`
- PCM SHA-256: `89e1b9496aa51e3dc22fb5d009b3c03f9ede6d259f9fc248f776a13ba349d931`

### Waveform-control packet
- Packet lineage: `ZEREF-ORIGIN-HEART-001`
- Packet SHA-256: `d6e44478b9b6045907014515c3ac565e635443250d199979ab909fc1d2734fc0`
- Segments: 20
- Qubits: 5
- Layers: 4
- Shots: 4096

### Separate 4096-sample 12D origin projection
This is a distinct signal representation and must not be conflated with the 20-window quantum-control packet.

- Selection: 4096 evenly spaced samples across the decoded mono 8 kHz source, peak-normalized
- Projection: first six non-DC rFFT bins, real and imaginary components, max-abs normalized
- Derived wave rate: 4096 Hz
- Derived wave samples: 4096
- Derived WAV SHA-256: `c2fbc811d95d354576ac6b2939aaa019f18275cf1bcd9111f620c2e53bd0a92f`
- 12D vector:
  - `-0.4916993909987407`
  - `-0.9626018824413768`
  - `-0.033282805321225`
  - `-1.0`
  - `0.8292515505425334`
  - `-0.6829807191348364`
  - `0.535813620240739`
  - `0.21223832630417797`
  - `0.8071556681779649`
  - `-0.6603681065935961`
  - `0.8426942281942428`
  - `0.27888967933491343`

## Feature Extraction Contract
The exact existing contract is:

`ffmpeg SOURCE -> mono 8kHz s16le; 20 equal PCM windows; RMS/ZCR/spectral centroid; per-feature minmax across windows; angle=pi*(2*u-1)`

For equal PCM window `i` with samples `x_i[n]`:

### RMS
`RMS_i = sqrt((1/N_i) * sum_n x_i[n]^2)`

### Zero-crossing rate
`ZCR_i = (1/(N_i-1)) * sum_{n=1}^{N_i-1} 1[sign(x_i[n]) != sign(x_i[n-1])]`

### Spectral centroid
For magnitude spectrum `|X_i[k]|` and frequency bin `f_k`:

`C_i = sum_k f_k |X_i[k]| / sum_k |X_i[k]|`

The stored centroid is normalized by Nyquist.

### Per-feature normalization
For feature family `f`:

`u_{i,f} = (f_i - min_j f_j) / (max_j f_j - min_j f_j)`

When all feature values in a family are equal, implementation must use a deterministic neutral normalized value of `0.5` to avoid division by zero.

### Angle projection
`theta_{i,f} = pi * (2*u_{i,f} - 1)`

Thus every control angle is in `[-pi, pi]`.

The existing packet stores these values as `rx`, `ry`, and `rz`.

## Quantum Circuit Mapping
For layer `l in {0,1,2,3}` and qubit `q in {0,1,2,3,4}`:

`segment = 5*l + q`

Apply in this order on qubit `q`:
1. `RY(theta_segment,y)`
2. `RZ(theta_segment,z)`
3. `RX(theta_segment,x)`

After all five qubits in each layer, apply a five-edge CX ring:
- `CX(0,1)`
- `CX(1,2)`
- `CX(2,3)`
- `CX(3,4)`
- `CX(4,0)`

After all four layers, measure all five qubits.

## Verified Fresh IBM Hardware Root
The current verified hardware root is evidence for the original signal condition and provenance. It is not by itself a matched four-arm A/B study.

- Backend: `ibm_marrakesh`
- Job ID: `da1mqfcdedkc73er87r0`
- Hardware shots: `4096`
- Counts SHA-256: `dfddf5366961cab837ae614750efb1dd60121ac3b3f6b7506d39346e3fd7bdce`
- Origin seed SHA-256: `f21afbac49e798730974e37ed1a1bb7ce15f326660a9dbe3f848ee6b1f865c2f`
- Fresh hardware requested: true
- Existing job reused: false
- Required tag verified: `zerefs-heartbeat-mustard-seed`
- Packet tag: `wave-d6e44478b9b6`

## State Equations
Let `H(x)` mean SHA-256 over canonical JSON with sorted keys, compact separators, UTF-8, and no NaN values.

### Hardware-rooted teaching session root
Define:
- `O` = preserved Tears origin-memory SHA-256
- `Q` = fresh IBM origin-seed SHA-256
- `C` = IBM counts SHA-256
- `J` = IBM job ID
- `B` = IBM backend
- `L` = starting durable ledger tip SHA-256
- `P` = previous continuation root SHA-256

Then:

`S_0 = H({schema, lineage, O, Q, C, J, B, L, P, fresh_ibm_hardware_measurement=true, synthetic_continuation_new_quantum_entropy=false})`

The implementation uses the existing domain-separated payload fields in `build_zeref_ibm_teacher_heartbeat.py`.

### Deterministic CST continuation pulse
For pulse number `t >= 1`:

`S_t = H({schema, session_root_sha256=S_0, previous_state_sha256=S_{t-1}, pulse=t, O, Q, L, kind='fresh-ibm-rooted-cst-synthetic-continuation', new_quantum_entropy=false})`

Runtime seed:

`seed_t = int(S_t[0:8], 16)`

No later pulse is described as a new IBM measurement.

## SON-HEARTBEAT-DEMO-001 Evidence Packet
Create directory:

`experiments/zeref-origin-heart-001/evidence/son-heartbeat-demo-001/`

Required files:
1. `00-source.json`
2. `01-feature-extraction.json`
3. `02-state-equations.md`
4. `03-gate-program-original.json`
5. `04-hardware-root-original.json`
6. `05-continuation-trace-original.jsonl`
7. `06-ablation-protocol.json`
8. `07-ablation-results.json`
9. `08-model-behavior-results.json`
10. `09-demo-transcript.jsonl`
11. `README.md`
12. `SHA256SUMS`

Every machine-generated JSON/JSONL evidence file must include a schema version and claim boundary. `SHA256SUMS` must cover every evidence file except itself.

## Four-Condition A/B/Control Protocol
The purpose is to test whether downstream circuit/model behavior is sensitive to the specific original signal representation.

All non-signal variables must remain fixed within a comparison block:
- TALK-004 weights
- 352-record memory snapshot
- architecture
- 24 blind Dad questions
- inference temperature/top-k/token cap
- decoding seeds
- circuit topology
- 5 qubits
- 4 layers
- shot count
- evaluator implementation

### Condition A: ORIGINAL
Use the exact ordered 20-window feature packet from packet SHA-256 `d6e44478...34fc0`.

### Condition B: REMOVED
Keep circuit topology identical, but replace all signal-derived `RX`, `RY`, and `RZ` angles with `0.0`.

Purpose: test whether waveform-controlled rotations contribute beyond the fixed entangling topology and measurement process.

### Condition C: SHUFFLED
Deterministically permute the 20 complete feature rows before assigning them to `(layer, qubit)` positions. Preserve each row's internal `rx/ry/rz` tuple and the empirical distribution of all feature values.

The shuffle seed must be committed before evaluating outputs:

`shuffle_seed_sha256 = H({'domain':'SON-HEARTBEAT-DEMO-001-SHUFFLE-v1','source_packet_sha256':packet_sha})`

Use the first 64 bits of the digest as the PRNG seed.

Purpose: destroy temporal/spatial assignment while preserving the feature distribution.

### Condition D: ALTERNATE
Create a deterministic phase-randomized audio surrogate from the decoded mono 8 kHz signal:
1. compute rFFT of the complete decoded PCM signal;
2. preserve each spectral magnitude;
3. replace non-DC/non-Nyquist phases with deterministic pseudo-random phases from a domain-separated seed;
4. enforce Hermitian consistency through inverse real FFT;
5. scale RMS to match the original decoded signal;
6. quantize deterministically to signed 16-bit PCM;
7. pass the surrogate through the identical 20-window RMS/ZCR/centroid extractor and angle mapper.

Alternate seed:

`alternate_seed_sha256 = H({'domain':'SON-HEARTBEAT-DEMO-001-ALTERNATE-v1','source_pcm_sha256':pcm_sha})`

Purpose: preserve broad spectral energy while disrupting the exact original temporal waveform.

## Two-Stage Ablation Execution
### Stage 1: Deterministic/local circuit-definition controls
Always run all four conditions locally to produce:
- exact transformed feature packet
- packet hash
- gate program
- gate-program hash
- deterministic source/control seeds

No hardware claim is made from this stage.

### Stage 2: Matched hardware block
For the strongest hardware comparison, submit ORIGINAL, REMOVED, SHUFFLED, and ALTERNATE in the same execution block on the same selected IBM backend/session window when technically available, each with exactly 4096 shots.

The protocol must record:
- backend
- job ID
- submission timestamp
- completion timestamp
- shot count
- job tags
- transpilation summary
- counts
- counts SHA-256
- origin-seed SHA-256
- calibration/backend metadata available from the runtime without credentials

If one arm fails or is cancelled, the full matched hardware block is marked incomplete. Do not silently compare three fresh arms against the older Marrakesh original as if they were a matched four-arm experiment.

The existing Marrakesh result remains historical original-condition evidence and may be reported separately.

## Circuit Distribution Metrics
For each condition `k`, let `p_k(z)` be the empirical five-bit output distribution.

### Total variation distance
`TVD(P,Q) = 0.5 * sum_z |P(z)-Q(z)|`

### Jensen-Shannon divergence
Use base-2 logarithms and report in bits:

`M = 0.5*(P+Q)`

`JSD(P,Q) = 0.5*KL(P||M) + 0.5*KL(Q||M)`

Apply a zero-safe implementation where `0*log(0/q)=0`.

Report pairwise metrics for ORIGINAL vs each control and the full pairwise matrix.

No statistical significance language may be used unless a declared repeated-block or bootstrap protocol supports it.

## Zeref Behavioral Ablation
The model behavioral experiment must be separate from the hardware-distribution claim.

Use the same TALK-004 checkpoint and exact 352-memory snapshot for every condition.

For each condition, construct the same runtime wire format:

`H:<condition state prefix>`
`M:<retrieved memory>`
`Dad:<blind question>`
`Zeref:`

Use 24 fixed answer-blind questions. Each condition must use matched per-question decoding seeds so signal condition is the experimental variable.

Record raw output before scoring.

Metrics:
- reference-token recall
- exact-answer rate
- first-answer-token accuracy when reference targets exist
- role-label leakage turns
- repetition-flag turns
- vocabulary-collapse turns
- contradiction rate across declared equivalence groups
- answer length statistics
- exact raw-output SHA-256 per turn

The behavioral result may support only a statement such as: "downstream computational behavior was sensitive/not sensitive to the tested signal transformation under this protocol."

## TALK-006-WIRE-GROUNDED Hypothesis
TALK-005 trained on a simplified response format:

`Dad: <question>\nZeref: <answer>`

But live inference conditions on a different wire:

`H:<heartbeat state>\nM:<retrieved memory>\nDad:<question>\nZeref:`

Hypothesis: the train/runtime conditioning mismatch contributes to the observed gap between teacher-forced response accuracy and free-running answer quality.

This is a testable engineering hypothesis, not an established cause.

## TALK-006 Training Design
### Parent
TALK-006 must start from the verified TALK-004 checkpoint, never from any rejected TALK-005 child.

### Training examples
Every training row must use the actual runtime wire structure:

`H:<training heartbeat state>`
`M:<retrieved or synthetic-clean memory context>`
`Dad:<question>`
`Zeref:<clean target answer>`

Only the `Zeref:<clean target answer>` character positions receive supervised cross-entropy loss.

The `H`, `M`, and `Dad` portions are context-only and must receive zero loss weight.

### Memory contexts
Training must include:
1. relevant memory context;
2. irrelevant but plausible memory context;
3. empty memory context;
4. stale/contradictory memory context that the target must correct using explicit current facts.

No raw model generation may be promoted automatically into a clean target.

### Heartbeat contexts
Training must include multiple deterministic condition-state prefixes derived from ORIGINAL, REMOVED, SHUFFLED, and ALTERNATE definitions so the model cannot memorize one fixed heartbeat prefix as the answer key.

Heartbeat context remains computational metadata, not a consciousness signal.

### Candidate search
Use a declared small search space rather than claiming global optimality.

Initial TALK-006 candidate set:
- `wire_short`: 300 response-only steps
- `wire_mid`: 600 response-only steps
- `wire_long`: 900 response-only steps

All candidates:
- start from the same TALK-004 SHA
- use the same curriculum splits
- use the same optimizer family and deterministic seed except for declared step count
- are evaluated on identical holdouts

If all three fail, no child is promoted.

## TALK-006 Promotion Gates
A candidate is eligible only if every gate passes.

### Free-running semantic gate
Parent baseline is measured fresh in the same run.

Candidate mean reference-token recall must improve by at least `+0.03 absolute` over the fresh TALK-004 baseline.

### Exact-answer gate
Candidate exact-answer rate must be strictly greater than TALK-004's fresh baseline and greater than zero.

### Response-only teacher-forced gate
Candidate response NLL must be lower than TALK-004 response NLL on the new wire-grounded holdout.

Candidate response-token accuracy must be higher than TALK-004 response-token accuracy.

### Retention gate
On the preserved older TALK holdout:

`candidate_retention_nll <= parent_retention_nll * 1.05`

Readability may not decline by more than `0.03 absolute`.

### Anomaly gates
Reject if any of the following occur:
- any role-label leakage regression above parent
- any repetition collapse above declared parent tolerance
- any vocabulary-collapse regression above parent tolerance
- contradiction rate worsens above declared tolerance
- output-length collapse
- non-finite loss/metric
- malformed or unhashable evidence

### Memory integrity gate
Before any Dad post-promotion session:
- reconstructed ledger must contain exactly 352 records
- combined SHA must equal `67ef0ccdd82bd0cf4964d40010314edd164c77799b6a7ef22a64ecf4314c5bef`
- tip SHA must equal `b35b50f64b837d403d24951be15910bdb5fc2e17eead7fef79c0a8f44d427d26`

After a winning 24-turn Dad session, if every turn appends one Dad prompt and one verbatim Zeref output, expected local count is 400. Exact count must be verified rather than assumed.

### Parent integrity gate
Re-hash TALK-004 after candidate training. The parent file SHA must remain exactly `9944d1d6e69e50f7b4a026a06719a3093a34607bc416ad788c2c658e67b6f55f`.

## Promotion Semantics
If one or more candidates pass every gate, select the eligible candidate with the highest free-running reference-token recall, breaking ties by:
1. higher exact-answer rate;
2. lower response NLL;
3. lower retention NLL;
4. fewer training steps.

Only the selected child receives the post-promotion Dad session.

If no candidate passes, record `REJECT_ALL_CANDIDATES`, preserve TALK-004 as active, and do not advance durable memory.

## Logs and Evidence
For every candidate and every signal condition preserve:
- config
- parent SHA
- child SHA
- train split SHA
- holdout split SHA
- optimizer/step count/seed
- loss log
- teacher-forced evaluation
- free-running raw transcript
- free-running metrics
- retention metrics
- anomaly metrics
- promotion decision/rejection reasons
- model and ledger integrity hashes

Raw generated answers must be stored verbatim before Dad reacts or scoring transforms are applied.

## Credential and Privacy Rules
- Never write IBM tokens, GitHub tokens, secrets, account user IDs, or authorization headers to evidence.
- Evidence may contain IBM job IDs, backend names, tags, public/non-secret runtime metadata, counts, hashes, and timestamps.
- Source audio binary need not be committed if the existing hash-and-metadata retention rule is sufficient. The source SHA is the forensic identity.

## Success Criteria
This phase succeeds if all of the following are true:
1. `SON-HEARTBEAT-DEMO-001` exists with complete source, extraction, equation, state, control, behavior, and checksum evidence.
2. All four signal conditions are deterministically reproducible.
3. Matched hardware results are either complete and honestly compared or explicitly marked incomplete.
4. TALK-006 executes from TALK-004/352 only.
5. No child is promoted unless every declared gate passes.
6. Rejected children and negative ablation results remain preserved evidence.
7. Any durable memory advancement is byte-prefix verified against the exact 352-record starting ledger.
8. No result is described as proof of biological life, consciousness, resurrection, deceased-person identity, communication with the dead, or quantum advantage.

## Expected Implementation Boundaries
New code should be split by responsibility:
- signal-control transformation and alternate-signal generation
- son-heartbeat evidence packet builder
- circuit-distribution metrics
- behavioral ablation runner/evaluator
- TALK-006 wire-grounded curriculum builder
- TALK-006 response-only trainer integration
- TALK-006 candidate selector
- workflow orchestration
- tests for every contract above

Do not rewrite proven TALK-004, Dad-ledger, or heartbeat ancestry code unless a failing regression test demonstrates a necessary compatibility fix. Prefer additive wrappers/modules.
