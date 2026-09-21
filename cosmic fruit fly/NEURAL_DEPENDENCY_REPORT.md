# COSMIC FRUIT FLY — neural-relay dependence and learned symbol output

Date: 2026-09-20. Status: **executed and independently replayed in an isolated local container; GitHub source sync blocked**. The previous audio-linked and fusion experiments, results and videos remain unchanged.

## The intervention

The previous `audio_linked_fusion.py` passed calibrated pixel-color features straight to the factorized software word decoder; the 42-node simulated network merely adjusted an abstention threshold. That made it impossible to attribute the successful typing to neural information transmission.

This continuation (`neural_dependency.py`) replaces **only the new task's noun decoder** with a teacher-trained prototype model operating exclusively on 24 *non-sensory* node activations. The fixed camera's 10×10 central pixel patch is reduced to an RGB median (no object name, label, or palette lookup), passed to 18 visual-role neurons with explicitly assumed fixed channel tunings, updated over four numerical neural steps, and read from the 24 remaining neurons. Gesture and intent glyphs retain separate teacher-trained symbol mappings. The expected three-token phrase reaches **only** feedback/scoring after prediction. The local text terminal and in-memory resource gate remain the only actions.

The task retains 48 supervised training combinations, 24 held-out/noisy combinations, a reversed mapping, and a simulated offspring copy. The camera is always fixated on a centered object; this is **not** a general object-recognition or self-directed locomotion test. The source-derived anatomical graph is nonrepresentative and the numerical neural update, encoder and decoder are computational modeling assumptions. A propagation-off ablation yields zero on the readout neurons *by construction*: the test establishes liveness and necessary connection within this architecture, not that one biological topology is uniquely sufficient or better. Rewiring does **not** preserve all graph degree properties.

The 20-window audio-derived packet and linked `ibm_marrakesh` 4,096-count histogram remain independently optional. The measurement histogram lacks original shot order; the replay order is deterministic and artificial. Memorial audio is not independently verified HR/EEG/ECG/HRV, and there was **no new IBM job**. Its original audio is not present in this package; upstream packet/hash binding is checked but raw audio-to-feature extraction is not independently repeated.

## Executed matched results

8 seeds × 10 arms × 168 trials/run = **80 runs, 13,440 trials**. No trial is presented as a physical organism measurement.

| Condition | Held-out correct | After reversal | Offspring-copy held-out |
| --- | ---: | ---: | ---: |
| Original-derived connectivity; auxiliary off | **130/192** | 124/192 | 124/192 |
| Original-derived + audio-linked IBM replay | 103/192 | 104/192 | 102/192 |
| Original-derived + shuffled audio/IBM | 107/192 | see results.json | see results.json |
| Rewired + audio-linked IBM | **130/192** | 124/192 | 121/192 |
| No propagation + audio-linked IBM | **0/192** | 0/192 | 0/192 |
| Audio only | 107/192 | see results.json | see results.json |
| IBM histogram only | 117/192 | see results.json | see results.json |
| No learning | 0/192 | 0/192 | 0/192 |
| Typing denied | 0/192 unlocked | 0/192 | 0/192 |
| Blank offspring | 103/192 pre-offspring | see results.json | 0/192 |

The original relay and rewired relay both scored 130/192 in the noisy holdout across eight seeds, despite differing auxiliary conditions. An active relay is required for this *designed downstream-only task*; **no original-topology advantage is established**. With audio/QPU replay, the original relay scored 103/192, not higher than the 130/192 auxiliary-off baseline; shuffled audio/QPU scored 107/192. These results do not establish a useful quantum advantage, and a mixed-condition comparison is not evidence of a causal topology effect. The `no_propagation` graph has no downstream source stimulation, making its zero a positive mechanism sanity check and also a limitation of this intervention.

The supervised decoder contains labeled noun exemplars and learned token maps. It does not acquire open-ended language or independently invent the stage sequence. A correct three-token message opens a strictly local virtual resource gate. Virtual offspring transfers software memory; there is no biological reproduction.

## Verification and evidence

- Baseline from recovered audio-linked archive: **84 passed, 3 skipped** after restoring two historical test-fixture folders omitted on the first partial extraction. The initial three missing-fixture failures are retained in `baseline_tests.log` for transparency.
- New regression suite: **91 passed, 3 skipped** (`neural_tests.log`). New tests cover visual-only stimulation, pixel perturbation, graph removal, auxiliary channel liveness, decoder independence, terminal permission and matched ablation behavior.
- Independent full eight-seed rerun created **byte-identical** `runs.jsonl` and `results.json`. Ledger SHA-256: `d3fba725df8c437e76d9bdd697baeee1f38f718c7548252bc79f775561d1a397`.
- Fresh rendered MP4: **1280×720 H.264, 1,280 frames / 320 seconds (5:20)**, SHA-256: `0e622d1f092ea52ee59ac4e6e2283c6ae40215195a0b9df575168b6f7446dedd`. Exactly 80 deterministic seed-0 trials from five phases. Every video frame checks the regenerated virtual camera image and the retinal encoder against the trial trace. It is a simulation replay, **not real motion footage**; sprite bobbing and backdrop are decorative.
- Source data SHA-256: subset `5b596574367d7e0e64489509a926a0305581f18568d12fef4339de5b49520cf4`; audio packet `6e0b4a4f879821a6aa7cdb6765bcfcaf72250ad6332d17775bb1fa5d98b45bd4`; archived QPU counts `10e8c18defa7cf5abe5ed37d33d84f909e7dea8f927228dbc05f481e3cb3b168`.

## Distribution, authority and release

This package contains an isolated source copy and its evidence. It does not overwrite the live Beast Box. The GitHub container cannot resolve `github.com`; the connected feature branch previously held only README and `PARTIAL_EXECUTION_RECORD.md`. **Do not claim the executable update or video has been pushed, merged, or run in GitHub CI.** The included guarded push script is for an authenticated Git environment, subject to checking current remote HEAD and source rights.

FlyWire-derived data is sourced through third-party **CC BY-NC 4.0**, with attribution in `data/DATA_LICENSE.md`; do not silently redistribute it inside a commercial Beast Box release. Raw personal bio is not included. No real biological measurement, biological intelligence, consciousness or quantum advantage is claimed.
