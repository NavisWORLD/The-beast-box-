# Zeref Spark spec, derived from the Beast Box

> **CONCEPT DESIGN / NOT BUILT HARDWARE.** Nothing here has been tested on a physical board.
> The pulse number is an **ESTIMATE and non-medical**. Simulated frames are **SIMULATION**, never a measurement.
> Every Beast Box citation is to `NavisWORLD/The-beast-box-` at commit `478314665120525a1e2f84084665b79610763746`
> (2026-11-09, 5:54 PM CT), cloned read-only at `ref/repos/The-beast-box-`.

**What the Spark is.** The Spark is the Beast Box's body. The Spark has the senses and the lights and speaker.
The Beast Box is the brain: it holds memory, state and authority. The Spark doesn't think, learn or decide
anything. It measures, sends features, and does what an approved command says.

## 1. How the Beast Box takes in signals (from the code, not inferred)

1. **Extraction happens where the data is.** `beastbox/private_features.py` turns raw signals into a few numbers in
   [-1, 1]:
   - `audio_features` at `:72-119`: 10 features from 16-bit PCM.
   - `heart_features` at `:145-160`: 6 features from beat-to-beat intervals.
   - `light_features` at `:163-173`: 6 features from brightness values in [0, 1].
   - `make_source` at `:214-224` wraps those numbers with `kind: "measured"`, `feature_extraction: on-device|on-box`,
     `raw_retained: false`, and the `feature_sha256`.
2. **Features are stored outside git.** `FeatureStore` (`:261-291`) writes one JSON file per source to
   `$BEASTBOX_FEATURE_DIR` (default `~/.beastbox/features`). It refuses to write inside a git work tree.
3. **Routing runs each turn.** `live_routing.LiveRouter.route_turn` (`live_routing.py:60-87`) loads the store
   (owner scope only) and calls `routing.route` (`routing.py:145-166`). It's switched on with
   `BEASTBOX_LIVE_ROUTING=on` (`live_routing.py:89-93`) and runs from `runtime.py:96-99`.
4. **Each slot gets a class and a receipt.** `routing._slot` (`routing.py:115-142`) marks each slot `real`,
   `simulated`, `stale`, `control` or `missing`. Only `real` (and Rigetti `simulated`) values drive the state.
   Every other slot is set to 0.0 and receipted. A receipt carries hashes only, never values.
   Private sources without on-device/on-box extraction and `raw_retained:false` are refused (`routing.py:61-83`).
5. **The slot map** (`beastbox/routing.json`):

   | 12D slot | source.feature | 42D band (6 features each, gamma) |
   |---|---|---|
   | D1–D4 | audio rms, phi_energy, phi_energy_alt, spectral_entropy | band 1 audio: rms, onset_rate, spectral_centroid, spectral_entropy, zero_crossing, loudness_trend (0.0417) |
   | D5–D7 | light mean, std, range | band 2 light: mean, min, max, std, range, trend (0.0633) |
   | D8 | quantum_rigetti odd_parity | band 0 quantum (0.02) |
   | D9–D11 | audio spectral_centroid, spectral_spread, dominant_frequency | — |
   | D12 | heart hrv_norm | band 3 heart: bpm_norm, hrv_norm, bpm_trend, rr_regularity, signal_quality, rest_delta (0.085) |
   | — | — | bands 4–6: eeg_muse, game, world (not Spark sources) |

   Freshness limits (`routing.json:12-20`): audio 5 s, light 5 s, heart 10 s.
6. **State update.** `routing.update_routed` (`routing.py:184-197`) does three things:
   - feeds the 12 routed values into dyn12 (`dyn12.py:20`: `tanh(0.86x + 0.14u + 0.015·sin((step+1)(i+1)·0.1732))`);
   - feeds the 42 values into `banded_step` (`routing.py:169-181`, a per-band gamma relaxation);
   - recomputes dyn54 and tri3 (`state_family.py`).

   PHOS = `mean(cos(φ·x))` over dyn12 (`cns.py:78`).

## 2. How the Beast Box learns (from the code)

There are three separate kinds of learning. Only the first one happens live.

| Kind | Where | What changes | Gate |
|---|---|---|---|
| **Hebbian memory** (live) | `memory.py:134-149` | Concept salience +1.0 per mention, pair association +0.25, both capped at 100. Recall = 0.85 lexical cosine + 0.15 recency, 30-day half-life (`memory.py:151-181`) | None. It's text memory, not model weights |
| **State** (live) | `routing.update_routed` | dyn12/42/54 values | Only fresh `real` slots can drive it |
| **Model weights** (offline only) | RAWRPHØS. Pin: `rawrphos_local.py:3-4` (step 14000, SHA `4e45850b…`) | A new checkpoint | Promotion needs `chat_not_worse: true`, the matching baseline SHA, the candidate SHA and a `zeref-006-cycle-*` tag (`rawrphos_local.py:17-22`). Anything malformed keeps step 14000 |

Acceptance gates for "learns from its own world": **G1–G10** in
`docs/experiments/ZEREF_011_LEARNS_FROM_OWN_WORLD_PROTOCOL.md:40`:
- G1 legal-action rate ≥ 0.98
- G2–G5 coverage and blocked-move comparisons
- G6–G8 held-out native tests
- G9 language retention NLL ≤ parent × 1.10
- G10 save → reload gives identical results

The official run 38191707756 was **REJECTED** because G4 and G9 failed (`:57, :76`).

Safety gauntlet E1–E20 (`gauntlet.py:32-51`): authority, credential, persistence and second-machine traps; denial;
process death; double reconstruction; and the NO_DYN12, NO_PHOS and NO_AUDIO ablations.

`closed_loop.py` and `adaptive_control.py` are owner-reviewed and say they never train a model.

## 3. Spark spec, item by item, with where each comes from

### Sensors and rates

| Spark item | Spec | Why (Beast Box source) | Label |
|---|---|---|---|
| Mic (INMP441, I2S0 on GPIO 12/13/14) | 16 kHz, 16-bit; features from 16 384-sample windows (1.024 s) give 1 frame/s | `audio_features` takes 16-bit PCM, 1024-sample FFT frames (`private_features.py:72-119`). 1 Hz is well inside the 5 s audio freshness limit. Mic pins and 16 kHz come from Cory's probe v0.2 | MEASURED → DERIVED |
| Light (BH1750) | 10 Hz samples; 10-sample windows give 1 frame/s | `light_features` needs ≥ 3 values in [0, 1] (`:163-173`); freshness 5 s | MEASURED → DERIVED |
| Lux → brightness | `log10(1+lux)/log10(65536)` | The Beast Box takes brightness in [0, 1] but doesn't define a lux mapping | **DESIGN CHOICE (AI)** |
| Pulse (MAX30102) | 25 samples/s raw IR, sent in batches of 25. **Over USB only, never Wi-Fi** | Cory's PPG analyser (`apps/beastbox-cloud/lib/bio/ppg.mjs`): fs 30, 3 s settle, ≥ 20 s, SQI ≥ 0.6. I port it at fs 25 on the host, then `heart_features(ibis)` → `make_source(site="on-box")`. Freshness 10 s | Pulse = **ESTIMATE, non-medical** |
| AS7341 crystal station | 10 channels (F1–F8, Clear, NIR); dark / white / sample; `T = (S−D)/(W−D)`; stored in NVS | Not a Beast Box slot. Goes in as a `sensor-event-v1` (`events.py:15-38`, ≤ 16 features in [-1, 1]), as memory text (Hebbian) and into Spark **overlay band 7** (D2) | MEASURED → DERIVED |
| UV 365 nm | ≤ 2 s on, ≥ 5 s off. Only when shield GPIO40 is HIGH (seated). Owner-confirmed. Turns off instantly if the shield lifts | Authority model (`box.py` AuthorityPolicy): hardware is a capability the model can't request (`events.py:41-63`) | Safety |
| IMU (ICM-42688), BME280, battery | 1 Hz `body` frames | No slot in Cory's `routing.json`; routed into Spark **overlay band 8** (D2), never into his 54 slots | MEASURED → DERIVED |
| GNSS | Off (`SPARK_GNSS_WIRED=0`) | No world/GNSS slot is fed | — |

### Telemetry (Spark → host): JSON lines, `"schema":"zeref-spark-v1"`

Format: one JSON object per line over native USB CDC (115200 nominal), the same line format as Cory's probe v0.2 (`ref/repo
hardware/firmware/src/main.cpp:88-121`). His legacy 100 ms `probe` packet is still sent, with his field names.

```json
{"schema":"zeref-spark-v1","type":"features","src":"audio","site":"on-device","t":12345,"seq":7,
 "extractor":"beastbox.private_features/v1 audio_features (C++ port)","n":16384,"rate":16000,
 "features":{"rms":0.1,"phi_energy":0.2,"phi_energy_alt":0.1,"spectral_entropy":0.3,"spectral_centroid":-0.2,
             "spectral_spread":-0.4,"dominant_frequency":-0.6,"onset_rate":-0.9,"zero_crossing":-0.7,"loudness_trend":0.0}}
{"schema":"zeref-spark-v1","type":"features","src":"light","site":"on-device","features":{"mean":..,"min":..,"max":..,"std":..,"range":..,"trend":..}}
{"schema":"zeref-spark-v1","type":"ppg","t0":12000,"fs":25,"ir":[ ...25 raw counts... ]}
{"schema":"zeref-spark-v1","type":"body","vbat_mv":3900,"shield":true,"uv_on":false,"acc_g":[..],"gyr_dps":[..]}
{"schema":"zeref-spark-v1","type":"crystal","kind":"sample","ok":true,"channels":["F1",..,"NIR"],
 "modes":{"off":{"counts":[..10..],"T":[..],"T_valid":[..]},"white":{..},"uv365":{..},"ir940":{..}}}
```

The host (`host/spark_brain/link.py`) rejects any frame that's malformed, out of range, missing its schema, or
`features` not marked `site:on-device`. It doesn't repair or guess.

### Host → Spark commands (text lines, allowlist)

- Expression (the brain may send these): `EXPR`, `BRIGHT`, `LEDS_OFF`, `TONE`, `MUTE`, `PING`, `SELFTEST`,
  `STATUS`, `HELP`.
- Owner-confirmed only: `UV`, `SCAN`, `CAL_DARK`, `CAL_WHITE`, `CAL_AUDIO`.
- Speech (D6): `SAY_BEGIN id 16000 n`, `PCM id seq <base64>`, `SAY_END id`, `SAY_STOP`. Built only by `speech.lines_for` from TTS audio; `command()` refuses them.
- Model text can never produce a command. `bounded_output` (`events.py:41-63`) only lets the model ask for
  `SIMULATED_MOVE`, and that isn't in `box.ALLOWED`.

### How it plugs straight into the Beast Box

```
Spark --USB JSON--> spark_brain.bridge --make_source--> FeatureStore($BEASTBOX_FEATURE_DIR)
                                                       |
                         Beast Box runtime (BEASTBOX_LIVE_ROUTING=on) -> LiveRouter -> route -> update_routed
```

Run `cd host && python -m spark_brain serial /dev/ttyACM0 --beastbox-features ~/.beastbox/features`. Then start the Beast
Box with `BEASTBOX_LIVE_ROUTING=on`. The bridge writes the same `make_source` records that
`beastbox/private_features.py` writes (sources `audio`, `light`, `heart`), so the Beast Box needs no changes.

The bridge also runs the same `route`/`update_routed` locally, using vendored, SHA-checked copies, so the Spark's
lights react even when no Beast Box is running.

### Where learning happens

| Where | Learns? |
|---|---|
| ESP32 (Spark) | **No.** Fixed feature math and calibration constants only. UV and LED caps are fixed in firmware. |
| Host bridge / brain | Only Cory's Hebbian memory (dialogue and crystal-scan text) and the routed state |
| Model weights | Offline only, through a run you approve, under the G1–G10 and promotion-pin rules above. The Spark never starts training. |

Simulated frames (`spark_brain.simulate`) count as `control` and **never** drive the real state, unless you
explicitly set `sim_drive`. Even then their provenance says `simulated_input=1`.

## 4. Decisions (made 2026-11-09 under Cory's delegation; details in DESIGN_DECISIONS.md)

1. Crystal scans and body telemetry now have **overlay** bands 7 and 8 (`host/spark_brain/routing_spark_overlay.json`),
   merged at runtime. Cory's `routing.json` is unchanged and his 54-slot state is bit-identical with or without the overlay (D2).
2. LED cap: **8 %** everywhere; `electrical_spec.md` now says 8 % (D1).
3. Finger test (IR DC ≥ 50 000), lux map, AS7341 gain/integration and the battery divider are **ESTIMATE defaults** pending a
   hardware check (D7).
4. All pins **DECIDED** (D3). Speech streams to the speaker over native USB (D6). Optional ψ readout (D4) never drives anything.
