# Cosmic Fruit Fly — visible-42 build/grow sandbox experiment

**Classification: executed virtual-only, scripted-goal engineering demonstration.** The third-party extracted 42-neuron/95-aggregated-edge subset is derived from FlyWire FAFB v783 source connectivity. Neural dynamics, sensor transduction, motor decoding, behaviors, mutation/prior, resource ecology and simulated offspring are computational inventions. The experiment does **not** demonstrate biological reproduction, autonomous planning, that a complete fly brain has been connected, or a connectome-related performance advantage. Forest art is a decorative backdrop; retinal pixels are generated separately from geometry.

## Recovery and experimental changes

Started from the already-preserved `Cosmic_Fruit_Fly_Sensor_Quest_Source_Evidence.zip` (the public GitHub feature branch contains only its prior partial-execution record). Preserved previous source and reports. Added `sandbox_ecology.py` (virtual resource pixels, sensation and default-deny action gates), `run_build_grow.py` (11-stage closed-loop run with sensor-driven movement, actual recurrent 42-state dynamics and canonical public `dyn12.update_dyn12`), `render_build_grow.py` (live **replay** graph: every node's intensity derives from logged simulated neural values), `render_build_grow_tail.py` (deterministic interrupted-export recovery) and `run_one_build_grow.py` (CLI permissions). The forest world asset came from the previous local evidence ZIP.

The experimenter scripts the high-level task order: pick up a stick; place at nest; pick up a leaf; place; build nest; pick up a seed; plant; wait for growth; feed; return to nest and spawn one *software offspring* if nest/growth/energy preconditions are satisfied; then have the offspring navigate toward replenished food. Low-level navigation uses egocentric 96×64 segmented virtual camera pixels, simulated odor, modeled neural states, dyn12, and contact. **No task reward or resource coordinates are handed to the movement policy;** the test runner has coordinates to place virtual objects and verify terminal proximity. More flexible independent planning is not demonstrated.

### Measured controls: 4 matched seeds (0–3)

| Condition | Stages completed / 11 | Nest completed | Growth | Software offspring spawned | Offspring reaches food |
|:--|--:|:--:|:--:|:--:|:--:|
| Real-derived wiring | 11.0 | 4/4 | 4/4 | 4/4 | 4/4 |
| Rewired endpoints, signed-weight multiset held | 11.0 | 4/4 | 4/4 | 4/4 | 4/4 |
| No neural propagation | 11.0 | 4/4 | 4/4 | 4/4 | 4/4 |
| Build action forbidden | 4.0 | 0/4 | 0/4 | 0/4 | 0/4 |
| Reproduce action forbidden | 9.0 | 4/4 | 4/4 | 0/4 | 0/4 |

The task sequence is authored by a program; success does not imply emergent invention or learned construction. The original anatomical subset provides **no observed completion advantage** against rewiring or zero propagation. Four seeds are an engineering check, not an inference-ready biological evaluation. Programmed reproduction does not imply living offspring, species behavior or heritable learning.

### Video record

Four actual recorded per-tick real-derived-wiring runs were replayed in order. A sensor raster is regenerated from each archived sensor pose and object-visibility state and required to match its pixel-derived observations exactly, or the renderer fails closed. All 42 nodes and 95 graph edges are displayed (color intensity follows computed neural activity). The decorative forest pixels are **not** used for sensing and are not a camera frame. No physical fly, live visual hardware, software compilation on GitHub, or live game engine is shown. The 337.6-second, 1280×720 MP4 was constructed from 1,688 source frames at 5 simulation frames per second, encoded with frame duplication to 25 fps; no new simulation states were inserted by encoding. Interruption recovery concatenated two verified segments; the source renderer can regenerate the full file in one run with sufficient execution time.

### Verification and lineage

41 isolated regression tests passed (1 skipped). Deterministic independent re-execution across the complete 20-run control matrix reproduced both `runs.jsonl` and `results.json` SHA-256 hashes exactly. Last video frame decoded at 1280×720. See `build_grow_demo/results.json`, `build_grow_demo/runs.jsonl`, and `build_grow_demo/video_manifest.json`; manifest hashes bind code, source input, art and video. This experiment does not modify historical evidence, runtime authority, or core provider interfaces. Public canonical dyn12 used unchanged. No internet access or authenticated git push is available in this execution container.

**Data licensing:** the third-party FlyWire-derived anatomical subset is CC BY-NC 4.0; non-commercial and attribution conditions apply. The source is `DenisSergeevitch/desktop-fly`, `data/circuit.json` (blob `10a7d0726571881e77e93e33bd7a23d900025e49`), itself derived from FlyWire FAFB v783. See `data/real_flywire_subset.json` for provenance. Do not distribute commercially without separate rights review.

**Not merge-ready:** full project integration, real input hardware, independently validated biological physiology, direct source sync, and CI still remain unverified.

## Reproduce

From the archive root:

```bash
python -m unittest discover -s 'cosmic fruit fly/tests' -v
python 'cosmic fruit fly/run_build_grow.py' --seeds 4
python 'cosmic fruit fly/render_build_grow.py' --preview
python 'cosmic fruit fly/render_build_grow.py'   # full video render, requires ffmpeg and time
# Deny reproduction or choose an isolated control:
python 'cosmic fruit fly/run_one_build_grow.py' --arm real_wiring --allow 'scan,inspect,move,turn,pickup,carry,place,build,plant,grow,feed,rest,explore' --out /tmp/denied.json
```

Python 3.10+, NumPy, Pillow and ffmpeg/libx264. The scripted-run metrics rely on the exact included data and code versions. Do not treat any unchanged previous report as a result of this experiment.
