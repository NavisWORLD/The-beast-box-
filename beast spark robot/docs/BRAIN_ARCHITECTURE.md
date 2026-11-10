# Zeref Spark brain architecture

> **CONCEPT DESIGN / NOT BUILT HARDWARE.** The host code runs and is tested on recorded and simulated frames only.
> The pulse is an **ESTIMATE, non-medical**. **SIMULATION ≠ real measurement.**

Rule from Cory's work: **MODEL ≠ MEMORY ≠ STATE ≠ AUTHORITY.** Models are mouths. They talk. They don't hold the
memory, own the state, or control the hardware.

```mermaid
flowchart LR
  subgraph SPARK["Zeref Spark (ESP32-S3) · body · no learning"]
    MIC["INMP441 mic 16 kHz"] --> AF["audio_features (C++ port)"]
    LUX["BH1750 10 Hz"] --> LF["light_features (C++ port)"]
    PPG["MAX30102 IR 25 sps"]
    AS["AS7341 crystal station"] --> CAL["T=(S−D)/(W−D)"]
    BODY["IMU · BME280 · battery · shield GPIO40"]
    UVG["UvGuard: 2 s on / 5 s off, shield seated"]
    OUT["48 NeoPixels (cap 8%) · MAX98357A tones + speech"]
    RING["speech ring 1 s · gain 0.5 · mute GPIO6"] --> OUT
  end
  AF & LF & PPG & CAL & BODY -->|"USB JSON lines · zeref-spark-v1"| LINK
  subgraph HOST["Host: spark_brain"]
    LINK["link.parse_line (validate, drop bad)"] --> BR["SparkBridge"]
    BR -->|"ppg"| PP["ppg.analyse (port of Cory's ppg.mjs)"] --> HF["heart_features ⟵ Cory"]
    BR --> MS["make_source ⟵ Cory"]
    HF --> MS
    MS --> FS[("FeatureStore ⟵ Cory<br/>$BEASTBOX_FEATURE_DIR")]
    MS --> RT["route ⟵ Cory<br/>real/sim/stale/control/missing"]
    RT --> UR["update_routed ⟵ Cory<br/>dyn12 · dyn42 · dyn54"]
    UR --> PH["PHOS mean cos(φx) ⟵ Cory"]
    UR & PH --> EX["expression plan (AI glue)"]
    BR -->|"crystal"| CR["crystal_event (sensor-event-v1 ⟵ Cory)"]
    CR --> MEM[("ReconciliationMemory<br/>Hebbian ⟵ Cory")]
    TALK["owner text"] --> MEM
    MEM --> MO["MouthRouter: approved slot only,<br/>no fallback, state digest checked"]
    MO --> BO["bounded_output ⟵ Cory<br/>(model can't actuate)"]
    OWN["owner_command(owner_confirmed)"] --> AUTH["AuthorityPolicy ⟵ Cory + allowlist"]
    BR -->|"body + crystal T"| OV["Spark overlay bands 7–8 (AI glue)<br/>same receipt rules, own state"]
    RT --> MG["merged receipts 54 + 12"]
    OV --> MG
    UR -.->|"optional, off by default"| PSI["ψ readout (DERIVED)<br/>drives nothing"]
    BO --> TTS["sanitize → local TTS (piper / stub)"] --> SPL["SAY_BEGIN / PCM / SAY_END<br/>integers + base64 only"]
  end
  EX -->|"EXPR/TONE allowlist"| OUT
  SPL -->|"credit-paced, owner speech switch"| RING
  AUTH -->|"UV/SCAN/CAL_* only if owner confirmed"| UVG
  FS -.->|"BEASTBOX_LIVE_ROUTING=on"| BB["The Beast Box runtime<br/>(LiveRouter → route → state)"]
```

## Who wrote what

| Piece | File | Label |
|---|---|---|
| Routing, dyn12/42/54, feature extractors, make_source, FeatureStore, memory, events, providers, box | `host/spark_brain/beastbox_vendor/*` (byte-identical, SHA256SUMS checked by a test) | **Cory original** |
| Firmware base: pins, mic, CAL_AUDIO, JSON lines, legacy probe packet | `firmware/reality_bridge_probe_v0.2_original/` (untouched) | **Cory original** |
| PPG analyser | `host/spark_brain/ppg.py` (port of `apps/beastbox-cloud/lib/bio/ppg.mjs`) | **Cory original (ported by AI)** |
| C++ ports of audio/light features | `firmware/zeref_spark_fw/include/spark_features.h` | **Cory original (ported by AI)**, parity-tested |
| PHOS readout | `bridge.phos` (re-typed from `cns.py:78`) | **Cory original** |
| Mouth router rules | `mouths.py` (rules from `model_router.py`) | **Cory rules, AI code** |
| Libraries: Arduino-ESP32, ArduinoJson, Adafruit NeoPixel/AS7341, SparkFun MAX3010x, BH1750, BME280, finani ICM42688, TinyGPSPlus, pyserial | platformio.ini / pip | **Third-party** |
| IR DC ≥ 50 000 finger test | `ppg.py` | **Third-party heuristic (SparkFun examples)** |
| Overlay bands, ψ mapping, speech path, link validation, bridge, expression plan, crystal events, UV guard, firmware frames, CLI, tests | the rest | **AI glue** |
| ψ formula | `psi.py` (form from 12D-Hebbian-Transformer-ver.4.20 README.md:78) | **Cory original form, AI mapping** |
| Local TTS (piper + lessac voice) | `speech.py`, `~/.zeref-spark/ttsv` | **Third-party** |

Each output carries `provenance.py` labels, so you can always see where a number came from.

## What happens on one second of real data

1. The Spark sends one `features/audio` frame, one `features/light` frame, 25 IR samples and one `body` frame.
2. The bridge checks each frame. Audio and light become `make_source(site="on-device")`. The IR samples go into a
   30 s window. Once the window passes Cory's quality gate, the beat intervals become
   `heart_features` → `make_source(site="on-box")`.
3. `route()` sorts all 54 slots. On the synthetic demo: 29 `real` (12D audio/light/heart plus bands 1–3) and 25
   `missing` (quantum, EEG, game, world). `update_routed()` steps the state, and the receipts store hashes only.
4. The expression plan maps the state to colours. The eyes go dim grey when nothing real is driving the state.
   Only allowlisted `EXPR`/`TONE` commands go back to the Spark.
5. Body and crystal features go to the Spark overlay bands (66 receipts in total); Cory's 54-slot state is unchanged by them.
6. Talking writes to Hebbian memory. A model only speaks through a slot you approved. If that slot is down, the
   answer is "denied", not a quiet switch to another model. With speech on, the approved reply is the only text that
   reaches the TTS, and only audio samples reach the device.
