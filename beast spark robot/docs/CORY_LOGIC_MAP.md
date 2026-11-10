# Cory's logic map — what's in each NavisWORLD repo, and what the Spark uses

**Read-only survey, 2026-11-09 (CT).** All 34 non-fork repos under github.com/NavisWORLD (35 including one fork) were shallow-cloned
read-only into `ref/repos/` (code and docs only; big binaries skipped). Nothing was pushed or changed upstream.
The fork `hermes-agent` (third-party code) was not cloned. `Reality-bridge-universal-probe-engine-sim-` is the
existing clone at `ref/repo` (commit `13a4ee7`).

Rules for this file: I only list what the code or docs actually say, with file:line. Anything I'm guessing is
marked **(inferred)**. "Used in Spark" says exactly where.

## The short version

| Cory's idea | Where it really lives | Used in the Spark |
|---|---|---|
| Signal → 12D/42D/54D routing with a receipt per slot (real / simulated / stale / control / missing) | The-beast-box- `beastbox/routing.py:115-197`, `beastbox/routing.json` | **Yes, unmodified.** `host/spark_brain/bridge.py` |
| On-device feature extraction (audio, light, heart), raw never leaves | The-beast-box- `beastbox/private_features.py:72-224` | **Yes.** C++ port in firmware (`spark_features.h`), Python original on host. Parity-tested. |
| dyn12 update `tanh(0.86x + 0.14u + 0.015 sin(...))` | The-beast-box- `beastbox/dyn12.py:15-21` | **Yes, unmodified** (inside StateFamily) |
| dyn42 / dyn54 / tri3 state family | The-beast-box- `beastbox/state_family.py:16-56`; banded 42D `routing.py:169-181` | **Yes, unmodified** |
| PHOS readout `mean(cos(φ·x))` | The-beast-box- `beastbox/cns.py:78` | **Yes**, re-typed in `bridge.phos()` (drives eye/chest colour) |
| Hebbian memory (salience +1, association +0.25, cap 100) + lexical/recency recall | The-beast-box- `beastbox/memory.py:105-182` | **Yes, unmodified.** Dialogue + crystal scans |
| Models are mouths (explicit approval, no fallback, swap can't change state) | The-beast-box- `beastbox/model_router.py:1-92`, `providers.py:40-98` | **Yes.** Providers vendored; router rules ported in `mouths.py` |
| Model text can't touch hardware | The-beast-box- `beastbox/events.py:41-63`, `box.py:7-33` | **Yes, unmodified** (`bounded_output`) |
| sensor-event-v1 envelope (≤16 features in [-1,1]) | The-beast-box- `beastbox/events.py:15-38` | **Yes** — crystal scans |
| Pulse from PPG with a quality gate (SQI ≥ 0.6, ≥15 beats, ≥20 s) | The-beast-box- `apps/beastbox-cloud/lib/bio/ppg.mjs:6-91` | **Yes**, Python port (`host/spark_brain/ppg.py`), checked against his JS under node |
| Probe firmware v0.2 (pins, 16 kHz I2S mic, CAL_AUDIO, JSON lines) | Reality-bridge-universal-probe-engine-sim- `hardware/firmware/src/main.cpp:1-122` | **Yes** — the Spark firmware is built on it |
| RAWRPHØS checkpoint pin + promotion rule; G1–G10 acceptance gates | The-beast-box- `beastbox/rawrphos_local.py:3-4, 9-30`, `docs/experiments/ZEREF_011_LEARNS_FROM_OWN_WORLD_PROTOCOL.md:40` | **As a rule, not code:** the Spark never trains weights; see SPEC_FROM_BEASTBOX.md |
| Synaptic Core v1 (12→42→54, `W=clamp((1-λ)W+ηr·xxᵀ)`) | CNS-central-nervous-system-adaptive-connector- `spec/SYNAPTIC_CORE_V1.md`, `src/cns_bridge/plasticity.py:6-33` | Not wired (documented as an option) |
| CST ψ | The-theory-of-CST `cst_psi.py:3-65` (unit-consistent 2026 form) | Optional, off-by-default DERIVED readout `host/spark_brain/psi.py` using the ver.4.20 README:78 form (D4); drives nothing |

## The ψ formula you quoted

The brief quoted **ψ = ∫(φ√(m²c² + c⁴) + λΔx)dt**. I searched every repo for it and **did not find that exact form**.
What the repos actually contain:

- `The-theory-of-CST/cst_psi.py:10-15` (2026-10-15, "unit-consistent"):
  `ψᵢ = Kᵢ + Sᵢ + Uᵢ + Iᵢ`, every term divided by `E_ref,i = mᵢc²(1 + λᵢτ)`, with
  `Kᵢ = (1 + φ + λᵢτ)·(½mᵢ|vᵢ|²)/E_ref`, a screened "synaptic" term, a Newtonian term and an informational term.
  The file says it replaces the mixed-unit sum in `CST_Formula_Explanation.markdown`.
- `The-theory-of-CST/cst_engine.py:338-357` (older): `ψ = (φ·Ec + λ·Ec·Δt + L·m·c²/1e12 + Ω·Ec/A0 + U_grav)/V_11D`.
- `The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.20/README.md:78`:
  `ψᵢ = (φ·Eᶜᵢ)/(c²m₀) + λᵢ/E_ref + ∫|dx₁₂ᵢ/dt|dt + (Ωᵢ·Eᶜᵢ)/E_ref + U_gravᵢ/E_ref`.
- `cosmic-synapse-A-lmi-v.2/cosmic 8d/finished/README_Publication_Overview.md:41`:
  `ψᵢ = 1/V₁₁D × [φE_c,i/c² + λᵢ + ∫√(Σ(dxᵢ,ₖ/dt)²)dt + ΩᵢE_c,i + U_grav,i]`.

**(inferred)** The √(m²c² + c⁴)-style term looks like relativistic energy E = √(p²c² + m²c⁴), but no repo writes it
that way. Since 2026-11-09 the Spark has an **optional, off-by-default** ψ readout built on the ver.4.20 README:78 form (closest real
match: a φ·energy term, a λ term and ∫|dx/dt|dt). It's labelled DERIVED and never drives hardware (DESIGN_DECISIONS.md D4).
The Beast Box itself runs on dyn12/StateFamily, not ψ.

## Repo by repo

Links are `https://github.com/NavisWORLD/<name>`. SHA is the commit I read.

### Core to the Spark

**The-beast-box-** (`4783146651205…`, 2026-11-09 17:54 CT). This is the brain. A persistent agent engine with:
- Signal pipeline: `private_features.py` (on-device/on-box extraction, owner opt-in) → `FeatureStore` (outside any
  git tree, `private_features.py:261-291`) → `live_routing.LiveRouter.route_turn` (`live_routing.py:60-87`), which
  loads the store every turn → `routing.route` (`routing.py:145-166`) → `update_routed` (`routing.py:184-197`),
  called from `runtime.py:96-99` when `BEASTBOX_LIVE_ROUTING=on` (`live_routing.py:89-93`).
- Feature freshness windows: audio 5 s, light 5 s, heart 10 s, EEG 5 s, game 5 s, world 60 s, Rigetti 900 s
  (`routing.json` `freshness_seconds`).
- Private sources (audio/voice/music/light/heart/eeg) must say `feature_extraction` on-device/on-box and
  `raw_retained: false`, otherwise they're refused (`routing.py:61-83`).
- Memory: `memory.py` ReconciliationMemory (sqlite, WAL, Hebbian salience/associations `memory.py:134-149`, search =
  0.85 lexical cosine + 0.15 recency, 30-day half-life `memory.py:151-181`).
- Model routing: `model_router.py` (explicit host approval, state hashes checked across a swap, `weight_hash_attested:
  False`); `providers.py` (loopback-only Ollama, reference provider, "no fallback").
- Authority: `events.bounded_output` — model JSON can only request `SIMULATED_MOVE`; `box.AuthorityPolicy`.
- CNS: `cns.py` seven "roles" (quantum, dark_matter Lorenz σ10 ρ28 β8/3, emeth, plasticity trust ±0.01,
  awareness, daemons, surgeon), dyn12 + PHOS.
- RAWRPHØS: pinned checkpoint, step 14000, SHA `4e45850b…` (`rawrphos_local.py:3-4`). A promotion needs
  `chat_not_worse`, the matching baseline SHA and a `zeref-006-cycle-` release tag (`rawrphos_local.py:17-22`).
- Gauntlet E1–E20 (`gauntlet.py:32-51`): authority, credential, persistence and second-machine traps, denial,
  process death, double reconstruction, and the NO_DYN12 / NO_PHOS / NO_AUDIO ablations.
- G1–G10 acceptance gates: `docs/experiments/ZEREF_011_LEARNS_FROM_OWN_WORLD_PROTOCOL.md:40`. Result (run 38191707756, line 57): REJECTED,
  because G4 and G9 failed (line 76).
- Fingertip PPG: `apps/beastbox-cloud/lib/bio/ppg.mjs`. The cloud app lives in `apps/beastbox-cloud/` (this is the
  "beastbox-cloud" code; it's a folder in this repo, not its own repo).
- Sensory trust docs: `docs/GOD_CORE_SENSOR_BRIDGE_001.md`, `docs/BEAST_WINGS_SENSORY_TRUST.md` (consent, 8 s
  throttle, raw media rejected, sensor text is "untrusted").

**Reality-bridge-universal-probe-engine-sim-** (`13a4ee7`). Simulation engine, the device's digital twin, and the
probe reference design. Firmware v0.2 is `hardware/firmware/src/main.cpp` (122 lines). **Finding:** its
`platformio.ini` depends on `adafruit/Adafruit ICM42688`, which is **not in the PlatformIO registry**, so the
original doesn't build as-is. Log: `firmware/build_logs/original_probe_v0.2.log`.

### CST / state / memory libraries (same ideas, other forms)

| Repo | SHA | What it is (from its README/code) | Key logic, with file:line |
|---|---|---|---|
| CNS-central-nervous-system-adaptive-connector- | 1781c285d127 | Installable CNS connector: 12D→42D→54D, attention mixer, Hebbian plasticity | `spec/SYNAPTIC_CORE_V1.md` (12-channel encoder, e.g. audio ψ = `sin(2π·f_norm)·rms`); `src/cns_bridge/encoder.py:64-71`; `plasticity.py:6-33`; C ABI `bindings/c/src/cns_state_core.c` |
| Bio-integration-pipeline- | 92b245ed44a2 | Bio/CNS pipeline with SDKs and a frozen wire contract | `sdk/spec/SYNAPSE_WIRE_V1.md`: `next_i = clamp(0.88·prev + 0.12·tanh(Δ)·q·sin((i+1)·0.618…), -1, 1)`, golden vector at 1e-12 |
| COSMOS-HEARTLIGHT | 1a8bba45f5f2 | Classroom support tech, C++/Rust 12D support state | `native/cpp/src/synapse.cpp:88-95` `hebbian_delta = lr·pre·post − decay·w` |
| Python-cst-libraries- | ae672ad4813c | CST SDK (Python/C++/Rust): Dyn12, HebbianMemory, GaussianSynapse, CST-L | `src/cstlib/state.py:91` Dyn12; `src/cstlib/hebbian.py:8-26` |
| audio-model-12dyn- | f84409313e75 | C++17 procedural Foley engine using the Beast Box dyn12 | `include/cst_audio/audio.hpp:13` `update_dyn12` (C++ port of beastbox/dyn12.py) |
| Volume-I-The-COSMOS-CST-Universe-Manual. | 4587e5086dcb | Manual + memory library (no N-turn expiry, Hebbian, dream consolidation, Heart Bridge) | `README.md:13, 80-87` Heart Bridge as a software cadence |
| Cosmic-reconciliation-manual- | 66f9048f4763 | Portable durable "forever memory" library + apps | `docs/TEST_PROTOCOLS.md:5` write → checkpoint → kill → recover test |
| Cosmos | d2406b680039 | Canonical COSMOS runtime/provenance home | `ROADMAP.md:11` Dyn12 + Gaussian state-kernel preflight |
| The-theory-of-CST | cd1789d19d0c | CST research program + simulator + Mars game | `cst_psi.py`, `cst_engine.py:338-357`, `docs/CLAIMS_AND_EVIDENCE.md` |
| The-Cosmic-Davis-12D-Hebbian-Transformer- | a227a6e9e7d3 | Original 12D/42D Hebbian transformer ("Dual Mind") | `production_12d/autonomous_engine.py`, `benchmark_cosmic_vs_vanilla.py:44` |
| The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2 | c8219c3f27bf | v4.2: 54D Mixture-of-States Hebbian attention, Lorenz, emotional API (big: it has a venv checked in) | `docs/COSMOS_Paper.md:36, 125` (A_final = (1−g)·A_std + g·H(x54)); `emotional_api/emotional_state_api.py:1294` audio ψ proxy |
| The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.20 | 5b6e010a253c | "Production" 12D CST transformer package | `README.md:78` ψ equation; φ-scaled attention |
| cosmic-synapse-A-lmi-v.2 | 72acff844212 | A-LMI: user-owned memory/state/provenance/authority, replaceable model provider | `README.md:3-12`; `cosmic_synapse_complete.py:186` ψ from audio |
| cosmic-synapse-A-lmi | 9d91d55b081e | A-LMI blueprint v2.0 (Kafka/Milvus/Neo4j plan) | `A-lmi cosmic/doc md files/FINAL_SUMMARY.md:127` Ψ(x) potential |
| CosmicSynapse | d541a7f1f89b | 8D/11D foundation: `cst_lm.py`, `cst_simulation.py` | (read headers only) |
| Cosmic-synapse-the-living-universe-sim-engine- | 7658689a1faa | SIM EARTH 7.08: browser world, 12D→42D→54D fusion | `docs/PHYSICS_AND_54D_STATE.md:23-48` |
| infinite-adaptive-audio-12d-universe-engine | deebc53ad34d | COSMOS Music: voice + motion + pulse timing → adaptive music | `COSMOS_MUSIC_SUITE/` (bindings + golden conformance) |
| REALITY_BRIDGE_ALIEN_CONDUCTOR_III_SOUND_FIXED | e456a521842c | Cosmic Conductor engine; synaptic ABI v1 | `spec/synaptic_abi_v1.json`, `docs/SYNAPTIC_CORE.md:7` |
| -reality-bridge-alien-conductor-local-ai-band | 4e722f4341b7 | Local AI band: perception → musical state → musicians | `ARCHITECTURE.md` |
| Quantum-azure-ibm-bridge-attachment- | 794e29320ef0 | Quantum Bridge Transformer (bring-your-own IBM/Azure) | `docs/PROOF_OF_CONCEPT.md:75` |
| Cosmic-quantum-video-picture-generator- | 0368f6c155f2 | Media engine with CST state + HebbianAssociator | `src/cosmos_media/state.py`, `native/c_abi/src/cosmos_synaptic.cpp:9` |
| Synapse-os- | 807f897a07e1 | Debian-based OS for the COSMOS ecosystem; zeref-mobile model | `models/zeref-mobile-v1/verify_cosmosmodel.py:54` parent-checkpoint SHA check |

### Not about the robot (listed for completeness)

| Repo | SHA | What it is |
|---|---|---|
| Cory-Davis-portfolio- | c239f5614531 | Portfolio, provenance and evidence ledgers |
| NavisWORLD | 0081d7361c72 | GitHub profile + open-source ecosystem index |
| Death-on-a-sub- | f97a6774b898 | HEARTLIGHT Lantern Archive (memorial continuity toolkit) |
| Electionapp | c4907c54b0f4 | Election app (not an official authority) |
| Flock-camera-bio-update- | 219453da2285 | Flock Signal Safety Platform (Rust/C++), independent research |
| Cosmic-nova-os-GGUF-model-and-system- | 8f0e014bc13a | GGUF model system scope notes (README only) |
| hermes-agent | (fork) | Third-party agent fork; not cloned |

4 private repos reviewed locally; details omitted from public copy.
