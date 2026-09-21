# Cosmic Fruit Fly — sensor-rich virtual sandbox v2 (2026-09-19)

**Status:** New locally executed, isolated experimental upgrade. Earlier synthetic, movement and associative-learning evidence is preserved unchanged. This is a **rendered replay of executed software**, not footage of an animal or empirical proof of biological intelligence. The forest artwork is decorative concept art; the fly's sensor pixels come from the separate, executable scene-geometry raster in `sandbox_sensors.py`. Decorated background trees/rivers are not colliders or real physical sensors; the three circled obstacles and virtual arena bounds are.

## Source and mechanisms

- Data: `data/real_flywire_subset.json`, 42 neurons and 95 directed weighted edges, extracted/aggregated from the third-party `DenisSergeevitch/desktop-fly` FlyWire FAFB v783 circuit; **biased, nonrepresentative subset**, not a full brain or ventral nerve cord. Source URL: https://github.com/DenisSergeevitch/desktop-fly/blob/master/data/circuit.json ; upstream circuit Git blob `10a7d0726571881e77e93e33bd7a23d900025e49`. See `REAL_MOVING_DEMO_REPORT.md` for provenance and selection. Source-derived FlyWire data license: **CC BY-NC 4.0, noncommercial**; do not assume commercial Beast Box distribution rights.
- `sandbox_sensors.py`: 96×64 RGB **simulated** egocentric camera raster; station-marker detection based on actual pixels in that raster, ±57° FOV, limited visual range and segment/circle occlusion; two non-reward-bearing station odors sampled by virtual left/right antennae; geometry-derived contact/touch; heading; collision and world bounds.
- `run_sensor_quest.py`: route camera detections and odors into LC4/LPLC2 role inputs; execute modeled tanh dynamics through the supplied graph; pool 12 scalars and pass to the **unchanged canonical** `beastbox/dyn12.py`; use distinct bounded software Q-table for cue–station association. Actions affect only the virtual arena. Reward label is revealed to the Q learner only on terminal contact; neither correct station nor hidden reward is given to vision, odor, movement, or neural state. Neural dynamics, inhibitory signs, normalization, sensory encoding, plasticity and movement decoding are assumptions, not measured Drosophila physiology.
- `render_sensor_quest.py`: visualizes actual seed-0 per-tick positions, neural/dyn12 and memory records in 16-bit-inspired forest-style HUD. Egocentric virtual camera is re-rendered and required to match the archived inferred pixel detection or the video fails to encode. The illustration is visually rich but **not the raw sensory image**. Wing flapping is cosmetic. Do not label it live, real-time, autonomous hardware, full brain, or real animal.

## Actual execution

4 matched seeds × 5 arms × (36 train + 18 held-out layouts + 22 reversal episodes) = **1,520 episodes**. Arms: original published wiring, destination-rewired weight-matched control, no propagation, frozen software memory in reversal, never-learning control. All share the episode schedule, environmental sensors, capped tick budgets, motor decoder and memory hyperparameters where enabled. Held-out geometry differs, reversal swaps food-rule mapping. Not all trials reach a station, so food reward differs from choice correctness. Per-seed variability is descriptive (n=4), no inferential advantage claim.

| Arm | Training food reward | Held-out reward | Reversal reward | Held-out arrival |
| --- | ---: | ---: | ---: | ---: |
| Published subset + software learning | 72.92% | 95.83% | 60.23% | 95.83% |
| Rewired + learning | 65.97% | 93.06% | 55.68% | 93.06% |
| No propagation + learning | 72.22% | 95.83% | 54.55% | 95.83% |
| Frozen learning on reversal | 72.92% | 95.83% | 0.00% | 95.83% |
| Never learning | 39.58% | 33.33% | 55.68% | 91.67% |

One of the four reversal runs of the real-wiring arm has a 100% reward rate over reversal episodes 16–20; the four-seed pooled average over that five-episode window was 100%, but this is a small, retrospectively examined subset. The full 22-episode reversal mean remains 60.23%. Results do not establish an anatomical advantage or robust generalization; biological connectivity makes a smaller, not scientifically established difference to this controller. The cue/station software-learning effect is the clearest observed mechanism.

### Quality gates

- `OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -v`: **28 tests passed**, including eight new sensory/occlusion, hidden-reward, geometry-touch, determinism, provenance and camera-replay gates. Older tests preserved.
- Independently reran full seed 0; identical SHA-256 `1c0e419930abd8d5ce71447c78e2832066a474500485167eafbfce39a720ed8b` for old and new 15 MB `seed-0.jsonl`.
- H.264 video: 1280×720, 10 fps, 1,976 frames, **197.6 s** (3m 17.6s), SHA-256 `2ddae944eb909a301e0b7e99ac2cf0ec5838ee91dbaadec9504b6696ccb1607d`. The full seed-0 episode sequence is sped-up and shown sequentially; other seeds and arms are in the evidence ledger, not visualized as multiple flies.

### Reproduce from this exported archive

Requires Python ≥3.10, numpy, pillow, ffmpeg. From the archive root:

```bash
cd 'cosmic fruit fly'
OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -v
for seed in 0 1 2 3; do OPENBLAS_NUM_THREADS=1 python run_seed.py --seed "$seed"; done
OPENBLAS_NUM_THREADS=1 python aggregate_quest.py --seeds 4
OPENBLAS_NUM_THREADS=1 python render_sensor_quest.py
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of json sensor_quest_demo/Cosmic_Fruit_Fly_Sensor_Quest_3m18s.mp4
```

The evidence JSON records code/data/ledger hashes; `video_manifest.json` binds video, renderer, scene asset and input evidence. Re-render video encoder exact-byte hashes may depend on ffmpeg version; executed runs and schema checks are the reproducibility gate.

**Merge/release boundary:** This is an isolated local implementation using a copy of the public canonical dyn12 and graph. It is not yet committed/pushed in full, is not the full-production COSMOS CNS/R12/persistent-memory/SYNAPSE/HEARTLIGHT/model-provider integration, has no genuine camera or odor hardware, and has no external host/network/actuator authority. No merged PR or GitHub Actions CI run is claimed. `MODEL ≠ SYSTEM; MODEL ≠ MEMORY; MODEL ≠ AUTHORITY`.
