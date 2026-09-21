# Cosmic Fruit Fly — real-connectivity subset + moving virtual fly

**Classification:** Executed computational simulation, rendered as a video. **No physical fruit fly was recorded.** Anatomy is derived from public real data, but neural dynamics, sensory mapping, motor decoding and 2D walking are computational assumptions. This is not a complete brain, a VNC simulation, biological locomotion, or a demonstrated improvement over matched controls.

## Source and explicit selection

- FlyWire Codex female adult brain FAFB v783 (October 2023), sourced via publicly published derived data: [`DenisSergeevitch/desktop-fly` `data/circuit.json`](https://github.com/DenisSergeevitch/desktop-fly/blob/master/data/circuit.json), source Git blob SHA-1 `10a7d0726571881e77e93e33bd7a23d900025e49`. Original file reports 668 nodes and 18,968 directed edge records; labels and per-connection signs are from that published third-party preprocessing, not independent physiology measurements.
- The bounded 42-node selection is **biased**: nine LC4 visual nodes, nine LPLC2 visual nodes, eleven untyped/other nodes, two DNp09, two DNa01, two DNa02, two GF, two MDN, and three escape-related DN cells, each selected by incident absolute connectivity with named DNs. Their 247 retained source edge records were summed into 95 directed pairs; source cell root IDs, role labels, and laterality remain attached.
- A source-derived canonical subset (ids, roles, sides, edges) was cross-checked against the repository response with FNV-1a32 `a2b8f5fa` (noncryptographic transcription check). The actual stored bytes have SHA-256 `5b596574367d7e0e64489509a926a0305581f18568d12fef4339de5b49520cf4`. The entire upstream source file was not independently downloaded into the compute container; the Git blob SHA is a repository reference, **not** a SHA-256 of the subset.
- Original source and derived subset data: **CC BY-NC 4.0**, noncommercial only. Attribution: Dorkenwald et al., *Nature* 634, 124–138 (2024), DOI 10.1038/s41586-024-07558-y; Schlegel et al., *Nature* 634, 139–152 (2024), DOI 10.1038/s41586-024-07686-5; FlyWire collaboration and the desktop-fly extraction author. Do not incorporate data into a commercial Beast Box distribution without applicable permission or review. The simulation code is separate from source dataset rights.

## Executed movement model

`fly_movement.py`: body position (x,y), heading, goal bearing, looming obstacle, and source-role/side-targeted visual inputs drive a bounded recurrent network. Update uses normalized directed signed graph, synchronous `tanh` dynamics, and the unchanged archived `beastbox.dyn12.update_dyn12` (SHA-256 `a60d2479fb678b7e446c0ace18f2fac352fa20ec4ba9f7894228b658a78f852f`). A **hand-defined motor adapter** reads DN populations and generates a scalar forward velocity and turn command; no VNC, motor neurons, gait measurements, calibrated synaptic conductances, or actual physical fly body are modeled. The fly graphic has animated wings and legs purely for visual communication; flapping is not generated from neural spikes.

The virtual fly moves under a default forward-speed parameter even without network propagation. Therefore **movement itself is not proof that the fly brain generated locomotion**. The key comparison is the effect of topology on controller output and trajectories. Four matched conditions × eight seeds × 260 simulated time steps ran; all conditions share identical obstacle and goal, sensory mapping and numerical parameters. Rewiring permutes target endpoints while retaining source and signed edge weights; it does not maintain destination in-degrees. Lesions zero both in- and outgoing weights for ten sampled neurons. No provider, external actuator, network, shell or filesystem authority is granted to any simulated entity. Actual code writes only the local evidence files chosen by the caller.

## Observed numerical results (all values are simulation units)

| Condition | Final target distance, mean ± seed SD | Distance traveled, mean ± seed SD | Absolute turn, mean ± seed SD |
|---|---:|---:|---:|
| Real subset connectivity | 3.76173 ± 1.01848 | 3.66594 ± 2.09012 | 0.27297 ± 0.17855 |
| Weight-matched topology rewire | 5.12802 ± 2.26279 | 8.26174 ± 2.20498 | 1.01110 ± 0.42547 |
| Ten-neuron lesion | 4.56762 ± 3.12043 | 6.46894 ± 2.41556 | 0.58606 ± 0.29451 |
| No network propagation | 2.07496 ± 1.17201 | 6.34337 ± 2.11472 | 0.00000 ± 0.00000 |

These are **not** measurements of real flies; the no-propagation controller reaches a smaller final target distance in this environment. Different work budgets are not compute-matched, and this is an illustrative controller, not a statistically powered claim. It illustrates that real anatomical edges affect the modeled neural states and trajectories, but is not proof of accurate fly behavior or graph advantage. Keep unsuccessful outcomes unchanged.

## Video record and tests

`real_fly_demo/movement_traces.jsonl` contains all executed per-tick positions, neural states, dyn12 state and controller values. `results.json` contains per-arm aggregates and data/code hashes. `render_moving_fly.py` renders the **actual saved traces** and continuously labels the result as a simulation. The 30.0-second H.264 MP4 (1280×720, 12 fps) is playback time, not physical or simulated seconds; no camera or live UI recording was performed. Video SHA-256 is in `real_fly_demo/video_manifest.json`.

All 13 isolated tests passed, including exact subset transcription, deterministic identical-seed simulation, lesions disconnecting in/out, wiring changes, canonical dyn12 dimensionality, and trace/video hash binding. Full Beast Box integration tests, biological validation, dataset primary re-extraction and CI **have not run**. Existing synthetic archived evidence is unmodified.

## Reproduction

From the ZIP root with Python 3.10+, NumPy, Pillow, ffmpeg, and the included unchanged `beastbox/dyn12.py`:

```bash
cd 'cosmic fruit fly'
python -m unittest discover -s tests -v
python fly_movement.py --seeds 8 --ticks 260
python render_moving_fly.py --frames 360
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of json real_fly_demo/Cosmic_Fruit_Fly_Real_Wiring_Moving_Demo.mp4
```

**GitHub state:** The earlier `experiment/cosmic-fruit-fly-closure-002` feature branch contains only a truthful partial execution report, not this real-connectivity movement implementation. These new files were executed and packaged locally, **not pushed or merged**. Release/merge gate remains **not ready**.
