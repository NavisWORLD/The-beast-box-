# COSMIC FRUIT FLY // HISTORICAL IBM QUANTUM REPLAY + SANDBOX TYPING

**Experimental classification:** isolated software simulation, NOT quantum biological intelligence, not autonomous natural-language acquisition, not a physical experiment.

## Recovered and reused

The previous build/grow sandbox was recovered from a local conversation artifact and copied to a new isolated workspace; original files were not overwritten. The canonical Beast Box `beastbox/dyn12.py`, 42-neuron / 95-edge FlyWire FAFB v783-derived subgraph, virtual sensor raster, neural graph renderer, pixel forest and 11-stage resource-policy loop were reused.

## Quantum input provenance

The source is `NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2`, `workload_decode_summary.json`, Git blob SHA-1 `084282a26bf923f03188a2be4c36f3fb34b09987`. A separate related repository directory contains raw job results. This run replays **exactly 9 historical decoded job summaries** dated 2026-03-12, all labelled `ibm_fez`, each source-reported with 4,224 shots (38,016 source-reported shots total). These reported summary fields were fetched from the repository, then transcribed into a bounded derived input. **The raw QPU payloads were not independently decoded or reverified here; no live IBM job was submitted.** Only this nine-record subset was used, not all of Cory's earlier workloads. The source-reported `entropy` and `top_state` are scaled by a declared software equation into a signed input bounded by 0.035, injected into the fly's simulated LC4/LPLC2 sensory channels. The modulation equation is not physics or biology.

## Biological signal boundary

A real FlyWire-derived *anatomical* graph is still present; visual/odor/touch/heading readings are **synthetic virtual-sandbox sensors**. The separate COSMOS source `cosmos/integration/bio/interface.py` defines `BioDataPacket` and `MockBioProvider`, but the latter creates simulated HR/EEG values. No verified personal EEG/HRV/GSR/ECG recording was recovered. The new normalizer fails closed on mock/missing-provenance packets. This run did **not** inject recorded bodily signals, despite the user's broader objective.

## Sandbox typing

A default-deny `type_token` action appends only known, event-linked words to bounded simulated state (up to 36 tokens); it never reaches a host keyboard or tool. Example emitted strings: `FOUND STICK`, `BUILT NEST`, `GROWN FOOD`, `HELLO LITTLE FLY`, `CHILD FOUND FOOD`. These are programmer-defined event names rendered as tokens; the fly has **not learned to write or converse**. Typing can be disabled independently without changing the goal policy.

## Actually executed

Six seeds x six matched arms = **36 executed sandbox cycles**. Every condition was tested with the same 11 authored resource goals, world, visual input format and action budget. The replayed measurement sequence is shuffled for a time-order control, zeroed for a null, and paired with connectivity rewiring / no propagation controls. Typing-disabled is the actuator ablation. Only replay-arm traces were rendered. All numeric values below are from the recorded results and may be verified via `quantum_language_demo/results.json`.

| Arm | Mean stages / 11 | Mean ticks | Typed words / run | Mean absolute modeled neural activity |
|---|---:|---:|---:|---:|
| Real-derived wiring + quantum replay + typing | 11 | 210.83 | 24 | 0.42624 |
| Same + replay disabled | 11 | 210.83 | 24 | 0.42571 |
| Same + 9-record shuffled replay | 11 | 211.00 | 24 | 0.42685 |
| Rewired + quantum replay | 11 | 211.83 | 24 | 0.57694 |
| No propagation + quantum replay | 11 | 212.50 | 24 | 0.13810 |
| Real-derived wiring + replay + typing disabled | 11 | 210.83 | 0 | 0.42624 |

The seed-0 mean absolute 42-node neural-state difference between replay and replay-disabled was **0.03823973**. This demonstrates numerical input coupling, not a measured adaptation/learning/behavioral benefit. All conditions completed all stages. No advantage is established for quantum input, real topology, or typing. Original software task policy remains hand-authored.

## Evidence and verification

- 46 isolated Python tests passed; 3 skipped (pre-existing test skips). Tests include replay controls, source job IDs, fail-closed bio packets, no host text action, preservation of legacy baseline, and neural liveness.
- Independent second 36-run execution reproduced `runs.jsonl` byte-for-byte. SHA-256: `de90389a00482411c7a65e5dd6fc883ca2d53d60ebfb1db04b51b88f0c0dca52`.
- Video is a **rendered replay of six executed sandbox traces**; displayed virtual camera is recalculated and checked against recorded sensor interpretations. The forest art is decorative and NOT the rendered camera input. It is NOT live QPU, a biological recording, or an actual keyboard capture.
- The 7:01.67 video is 1280x720, H.264 MP4. SHA-256 `08b887f50b0b543fd0ca3b2dbd718813170a0dda18f14184f5274a251c691564`.
- `MODEL ≠ SYSTEM; MODEL ≠ MEMORY; MODEL ≠ AUTHORITY`. No shell/network/hardware/host authority is available to the simulated fly.

## Reproduce (from extracted ZIP with Python + numpy, Pillow, pytest and ffmpeg)

```bash
cd 'cosmic fruit fly'
OPENBLAS_NUM_THREADS=1 python -m pytest -q tests
OPENBLAS_NUM_THREADS=1 python run_quantum_language.py --seeds 6 --output quantum_language_verify
sha256sum quantum_language_verify/runs.jsonl
python render_quantum_language.py --start 0 --end 3 --output quantum_language_demo/quantum_typing_part1.mp4
python render_quantum_language.py --start 3 --end 6 --output quantum_language_demo/quantum_typing_part2.mp4
```

For a complete MP4, concat the two same-codec parts with FFmpeg's concat demuxer (see `quantum_language_demo/concat.txt`). Recording can take several minutes.

## Remaining gates

The expanded IBM archive, verified real biosignal recordings, full COSMOS bio-runtime/HEARTLIGHT/R12 integrations, production code sync to GitHub, commercial licensing of the FlyWire-derived data (CC BY-NC 4.0), independent CI and merge review remain open. This is not merge-ready. Do not describe a rendered video or event-to-text formatter as biological intelligence or independent writing.
