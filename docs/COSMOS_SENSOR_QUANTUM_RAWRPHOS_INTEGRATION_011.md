# COSMOS sensory–quantum → CNS7 → RAWRPHØS integration, Stage 011

**Branch:** `feature/cosmos-signal-fusion-011`  
**Recovery base:** `feature/cosmos-world-interface-recovery-001` at `da81c23e35e2961420c520bc57abc9e543beb332`  
**Status:** implementation branch only; production is unchanged until exact-head CI and deployment acceptance complete.

This stage recovers the separate historical signal contracts and connects a new,
versioned typed-fusion path to the existing pinned RAWRPHØS native control input.
It does **not** relabel archived data, train a replacement model, start paid quantum
jobs, or claim biology, consciousness, quantum advantage, or improved intelligence.

## 1. Recovered source-lineage manifest

| Lineage | Original source / anchor | Algorithm / input | Numerical contract | Provenance boundary | Current adapter / consumer | Connected to native model now? |
|---|---|---|---|---|---|---|
| A-LMI LightToken | `NavisWORLD/cosmic-synapse-A-lmi-v.2/a_lmi/core/light_token.py` @ `72acff8442126c9e102e31d3874130228551fbcb` | 1536-D semantic/model embedding + perceptual hash + one-sided RFFT over embedding coordinates | RFFT has 769 complex bins for 1536 real coordinates | Dominant bin is an **embedding spectral-bin index**, not a physical Hz value without an external mapping | Historical serializer remains compatible; this Stage does not reinterpret the spectrum as physical frequency | **No direct LightToken→model edge yet**; recovered as lineage for a later typed semantic adapter |
| Historical audio 12D | `cosmos/core/multimodal/audio_engine.py` @ `2bb40a0befd9b1023d91513eddd8447e730fce0b` | PCM audio; Hann-window RFFT; YIN f0; spectral centroid, spread, entropy, RMS; MFCC metadata | D1 RMS²; D2 φ·D1/c²·1e17; D3 φ·D1; D4 normalized spectral entropy; D5–D7 placeholders in initial token; D8 similarity connectivity; D9 centroid/Nyquist; D10 spread/Nyquist; D11 log-scaled f0; D12 adaptive x12 | Measured physical audio frequency is kept distinct from later software state | `source_from_legacy_physics12(..., modality="audio")` masks D5–D7/D8/D12 unless the historical pipeline actually populated them | **Adapter ready; raw historical audio replay not yet attached to owner endpoint** |
| Historical visual 12D | `cosmos/core/multimodal/visual_engine.py` @ `2bb40a0befd9b1023d91513eddd8447e730fce0b` | Image → grayscale 2-D FFT; spatial entropy; gradients; centroid; dominant spatial frequency | D1 mean brightness; D2/D3 same physics-inspired scaling; D4 2-D spectral entropy; D5–D7 spatial gradients; D8 later connectivity; D9 spatial centroid; D10 D4; D11 normalized dominant spatial frequency; D12 adaptive state | Spatial-frequency bins and heuristic RGB→visible-frequency mapping are not relabeled as measured optical frequency | Same fixed historical-physics compatibility adapter, with source-specific mask | **Adapter ready; raw image replay not yet attached to owner endpoint** |
| Current bio/sensory 12D | `beastbox/bio_inputs.py` on recovery base | Explicit owner-supplied heart rate, HRV, respiration, skin temp, SpO₂, EDA, accelerometer RMS, five EEG-relative channels | Each declared unit range linearly maps to [-1,1]; missing channel stores numeric 0 **plus a false source mask** | `USER_SUPPLIED_UNVERIFIED`; missing is never treated as a measured midpoint | `source_from_bio_event` → fixed typed projection → fusion → CNS7 | **Yes**, isolated owner probe only |
| QBT → SOUL | `beastbox/soul/token.py`, `adapter.py`, `qbt_source.py` | Already-normalized QBT state [0,1] → `SoulToken` → signed spark | `spark = 2*x - 1`; existing adapter cycles source width to 12 | Token carries provider/backend/job/shots/result digest and fails closed on host/network/credentials/tools/model/memory/persistence authority | `source_from_soul_token` records original width and exact expansion map before typed projection | **Yes** for approved replay/control sources; live provider execution remains separately gated and is not used here |
| Published IBM Fez summary replay | Historical `workload_decode_summary.json`, blob `084282a26bf923f03188a2be4c36f3fb34b09987`, source repo commit `2bb40a...` | Nine source-reported completed `ibm_fez` summaries: job ID, timestamp, entropy, top 5-bit state, 4224 shots | New Stage-011 schema encodes `[entropy, top_state_bit0..bit4]` only | **HARDWARE_ARCHIVE_REPLAY**. Full histogram/raw RuntimeDecoder payload is absent; no reconstruction is claimed | `beastbox/soul/archive_summary.py` → SOUL → typed quantum source | **Yes**, as classical archive-summary replay only |
| CNS7 | `beastbox/cns.py` | seven software roles: quantum, dark_matter, emeth, plasticity, awareness, daemons, surgeon | typed fusion vector is preferred over legacy spark+audio concatenation; `update_dyn12` consumes exactly 12 generic control values | conditioning provenance SHA is attached to awareness; QBT provenance remains separately visible under quantum role | exact CNS7 dyn12 becomes native model control | **Yes** |
| RAWRPHØS native | `models/rawrphos/architecture/model.py`, `generation.py`, `inference/engine.py` | native learned dyn12/Mixture-of-States causal LM | `state = tanh(state_init_logits + control_vector[:,None,:])`; control must be finite [batch,12] in [-1,1] | model checkpoint identity remains pinned; external state is data, not authority | `condition_probe_v2` and private `/v1/condition-probe-v2` | **Yes**, fixed-weight probe; normal chat unchanged |

## 2. The three 12-component contracts remain separate

They are **not** added coordinate-by-coordinate.

### Historical physics-inspired D1–D12

Recovered audio definitions:

```text
D1  = RMS(audio)^2
D2  = φ * D1 / c^2 * 1e17
D3  = φ * D1
D4  = normalized spectral entropy
D5–D7 = initial temporal placeholders (0) in historical audio token
D8  = similarity-derived connectivity (initial placeholder 0.5, later updated)
D9  = spectral centroid / Nyquist
D10 = spectral spread / Nyquist
D11 = log10(f0/20) / log10(20000/20), when f0 exists
D12 = adaptive x12, initialized 0 and later evolved/clipped
```

Recovered visual definitions keep their separate spatial interpretation:
brightness, 2-D spectral entropy, x/y/combined gradients, connectivity,
spatial-frequency centroid, entropy, normalized dominant spatial frequency,
and adaptive state.

Stage 011 does not claim these components have SI-compatible units. The compatibility
adapter normalizes each historical component under the documented historical range
and records masking/saturation instead of silently changing meaning.

### Current bio/sensory vector

The declared bio channel order is preserved from `beastbox.bio_inputs.CHANNELS`.
For a present channel with bounds `[lo,hi]`:

```text
x = 2 * (measurement - lo) / (hi - lo) - 1
```

A missing channel receives a numeric placeholder 0 **and mask=false**. A real
measurement that happens to normalize to 0 therefore remains distinguishable.

### QBT / SOUL spark

For each upstream normalized QBT value `q in [0,1]`:

```text
spark = 2*q - 1
```

If source width is less than 12, the pre-existing SOUL adapter cycles it to width
12. Stage 011 does not hide this: it records `normalized_source_width` and the exact
`expansion_map` in source provenance before the typed projection.

## 3. Versioned typed fusion

New file: `beastbox/signal_fusion.py`.

Each source first remains in its own typed contract, mask and provenance envelope.
A deterministic **non-learned** source-specific signed-mean projection maps only
present channels into generic model-conditioning coordinates `C1..C12`.

For source `s`, fixed projection `P_s(x_s,m_s)`, explicit weight `w_s`,
confidence `c_s`, and freshness `f_s`:

```text
C_k =
clip(
  Σ_s [w_s * c_s * f_s * P_s(x_s,m_s)_k]
  / Σ_s [w_s * c_s * f_s],
  -1, +1
)
```

The output contract is explicitly:

```text
generic-model-control-C1..C12; not physical units
```

Every receipt includes source IDs, family, source kind, execution mode, channel
contract, mask, timestamp when available, weighting, confidence, freshness,
projection digest, fusion SHA-256 and saturation indices.

Supported modes at this stage:

- `pure_sensory`
- `pure_quantum`
- `fused`

## 4. Historical quantum result is preserved

The immutable 2026-08-29 closed-loop experiment remains unchanged.

That experiment recovered genuine IBM witnesses but found **0** source rows admissible
under its preregistered exact four-value/four-state contract, submitted **no** fresh IBM
jobs, and therefore classified the historical matrix `ENGINEERING_CONTROL_INCONCLUSIVE`.
Its synthetic fixture proved the software harness was source-sensitive, not a
quantum-specific behavioral effect.

Stage 011 uses a **new schema** for a different engineering question. The published
five-bit IBM Fez summary is encoded as:

```text
[normalized_entropy, top_state_bit0, top_state_bit1, top_state_bit2, top_state_bit3, top_state_bit4]
```

That is labeled `HARDWARE_ARCHIVE_REPLAY` /
`PUBLISHED_DECODE_SUMMARY_REPLAY_NOT_RAW_RESULT`. It does not reconstruct a histogram,
does not claim fresh hardware, and does not alter the 2026-08-29 preregistration.

## 5. Exact model-consumer path

```text
typed source(s)
  → source-specific normalized contract + mask + provenance
  → fixed deterministic projection
  → explicit weighted fusion C1..C12
  → BridgePacket.conditioning_vector
  → CNS7.tick()
  → CNS7 dyn12
  → private /v1/condition-probe-v2
  → Engine.condition_probe_v2()
  → RawrphosLM.forward(control_vector=...)
  → tanh(state_init_logits + control)
  → learned dyn12 state transitions
  → Mixture-of-States attention
```

`generation.generate()` passes the same control vector on prefill and every cached
decode step. Stage 011 additionally generates the conditioned arm with cache both ON
and OFF and requires literal output parity before the outer owner route accepts the
receipt.

## 6. Matched controls and telemetry

The private v2 probe supports the same immutable checkpoint across:

- unconditioned reference;
- all-zero control;
- selected conditioned vector;
- source-rotated/shuffled vector;
- deterministic classical shape/strength-matched control;
- zero-gate attention;
- frozen-state attention;
- shuffled-state attention;
- adjacent-timestamp archive control when a quantum-derived replay source is selected.

For each arm it records exact control vector, control SHA-256, attention mode, L2
control strength, and each layer's gate, sigma, state norm and omega mean.

It also records next-token logit L2 against reference, literal reference/conditioned
outputs, first-token/full-response timing, cache status, process CPU time, wall time,
and process max-RSS readout where the platform exposes it.

A nonzero logit delta establishes computational sensitivity only. It is **not** a
claim that the signal improves answers, that hardware provenance caused the effect,
or that quantum computation outperforms a matched classical control.

## 7. Owner/guest/authority boundary

The Stage-011 public UI route is owner-authenticated and same-origin only.
The Python bridge serializes it against owner/guest model traffic and forwards only
to the private loopback model endpoint.

Signal packets cannot grant:

```text
host
network
credentials
tools
model authority
memory_write
persistence
actuators
```

The Stage-011 probe does not open `DurableRuntime`, does not store the measurement,
does not update model weights, and does not start IBM/Azure jobs. Guests do not receive
the owner archive probe or owner numerical sensor path.

## 8. Production status and remaining acceptance

As of this Stage-011 branch, **production has not been changed**. The recovery-base
14K stable model and optional 18K experimental install remain the production lineage;
the conversation-repair branch remains a separate diverged research lineage and is
not silently merged here.

Release gates:

1. exact-head Python, native-PyTorch, web and security CI must pass;
2. review and merge only the verified, expected PR head into the current owner branch;
3. stage a one-shot fail-closed Railway managed-host acceptance with
   `BEASTBOX_SIGNAL_ACCEPTANCE_ON_START=yes` and the public owner feature OFF;
4. require successful **real pinned 14K** managed-host reports for all three modes,
   each with at least three generated tokens, nonempty text and exact token-level
   cache on/off parity, as well as fused/CNS/control hashes, gate/state telemetry,
   measured process CPU, wall time and unchanged stable/experimental model identities;
5. verify guest admission remains isolated and existing persistent-volume continuity;
6. only then enable `BEASTBOX_SIGNAL_MODEL_PROBE_ENABLED=yes` and disable the
   one-shot cold-start acceptance guard on the owner host;
7. verify Railway and Vercel independently; an inaccessible Vercel account
   cannot be reported as updated Production.

Still remaining after this stage: direct owner replay of recovered raw historical
audio/image inputs, a typed LightToken semantic adapter, broader browser sensor
capture into the same typed fusion contract, and task-relevance evaluations that test
whether conditioning helps rather than merely changes logits.

## 9. Real pinned-model CI evidence — 2026-09-26

**Workflow:** [CNS7 real native PyTorch / Stage-011 acceptance run 36207199461](https://github.com/NavisWORLD/The-beast-box-/actions/runs/36207199461)

**Artifact:** `signal-fusion-pinned-14k-receipt` containing
`cosmos-signal-native-14k-acceptance.json`. The receipt includes the exact
12D CNS vector, fusion/CNS/control digests, next-token control comparisons,
layer telemetry, literal output, CPU, first-token/full-response and RSS metrics.

This is the real pinned 14,000-step native checkpoint with SHA-256:

```text
4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5
```

The experiment used synthetic owner-entered bio readings (heart rate 72 bpm;
HRV RMSSD 31 ms), one source-reported historical IBM Fez **published summary
replay**, the same canonical chat prefill
`user: I'm so confused phos.\nassistant:`, seed 67, greedy temperature 0,
and maximum 24 new tokens for each arm. No live physical sensor was read and
no new QPU, cloud-provider, training or memory job was started.

| Arm/source | Conditioned vs reference logit L2 | Classical matched vs reference L2 | Zero vs reference L2 | Literal reference and conditioned output | Cached/uncached |
|---|---:|---:|---:|---|---|
| Synthetic bio only | 0.2692094147 | 0.2452372015 | 0.0 | ` Hello! How can I help you?` (both) | same exact 10 tokens |
| Published IBM summary replay only | 0.0298644807 | 0.0552218519 | 0.0 | ` Hello! How can I help you?` (both) | same exact 10 tokens |
| Fused synthetic bio + IBM summary replay | 0.0839512199 | 0.0734850392 | 0.0 | ` Hello! How can I help you?` (both) | same exact 10 tokens |

The previous exploratory run did produce nonzero next-token logit differences,
but an unformatted text prompt emitted **one EOS token and empty text** in
all three modes. We rejected that as insufficient full-response evidence.
The strict run now applies the existing trained dialogue prefill format and
requires *nonempty multi-token generation*. A separate real model unit test
forces five forward passes with EOS disabled, spies on the exact control tensor
and asserts the same 12 controls reach **prefill and every cached decoding
step**, with matching uncached generated tokens.

In the strict GitHub CPU runner, the **fused** multi-arm native probe reported:

```text
fusion_sha256   8a6e843f35394b935a70655698c4bc1c90844ae60401c1e177463cf8540132a5
cns_sha256      ddc0e7ab761cfaf16b9204803384bc0393654d6180fb8e1e0535dbac45017c54
control_sha256  6c95e524b42498b40cfd1f767bd125b454bd4b3a017a7f7221609738c0e35664
prompt_sha256   db3c97a698e890f8ee36f7a5f1c5d13ec628551841e9bc4660289aede699e0b8
wall_ms         292.822
process_cpu_ms  584.849
max_rss         297276 KiB, Linux process high-water RSS (not host total)
```

The six fused-layer native readouts in the attached receipt include:
gate `[0.07882445, 0.08699057, 0.07216939, 0.07252216, 0.07487404,
0.05334008]`, positive per-layer sigma, omega means, and state norms.
The full control table also includes rotated, time-shifted, frozen-state,
shuffled-state and zero-gate variants, and all synthetic receipt digests.

**Scientific interpretation:** full numerical state-to-model propagation
and fixed-weight cached decoding are demonstrated. Literal responses remained
identical between reference and conditioned runs. The result establishes neither
improved task performance nor any quantum-specific effect over matched classical
sources. In particular, a summary derived from previously reported IBM jobs is
not an admissible four-state source for the sealed August 29 historical experiment.
These timings are **GitHub runner** measurements, not production Railway CPU
benchmarks. Managed Railway acceptance and Vercel production verification must
be reported separately after deployment.
