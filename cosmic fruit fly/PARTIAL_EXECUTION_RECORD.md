# Cosmic Fruit Fly — isolated execution record (updated 2026-09-19)

**Branch scope:** Evidence status only. The executable experiment, game renderer, forest asset, video, and full ledgers are saved in a local conversation archive; they have **not** been committed to this GitHub branch. Do not merge this documentation-only branch as though it contained the runnable experiment.

## What was recovered

At main `21ecef58011409a257394e5f7e2fb1bdf8a681a6`, `cosmic fruit fly/` contained only a research landing page. The seven historical local scratch commits were not on the remote. An unchanged local copy of the public `beastbox/dyn12.py` was used in isolated experiments; no claim of complete product integration is made.

## Observed isolated experiments

1. Synthetic initial test: 24 nodes / 96 edges, nine conditions, eight seeds, fixed cue-memory task; no biological-data advantage. Seven initial acceptance tests passed.
2. Locomotor demonstration: a nonrepresentative 42-neuron, 95-edge induced subset from the third-party FlyWire FAFB v783 circuit; computational neural dynamics and virtual-body assumptions; animated replay, **not measured animal movement**.
3. Longer software associative learning: 80 train, 40 held-out layouts, 40 rule reversal; eight seeds and five matched arms. The original wiring performed identically to the rewired and no-propagation arms on food reward; software memory learned the cue–station association.
4. **NEW virtual-sensor quest v2:** 96×64 pixel-derived simulated camera with bounded FOV and explicit occlusion; station-specific modeled odor, geometry contact/touch, heading; modeled network and canonical dyn12 state; separate Q-memory; forest-style rendered replay of actual executed seed-0 traces. The decorative forest image does **not** generate the actual sensor pixel buffer. Four matched seeds × five arms × (36 train + 18 held-out + 22 reversal) = **1,520 executed episodes**.

| Quest v2 condition | Training food reward | Held-out food reward | Reversal food reward |
| --- | ---: | ---: | ---: |
| Published subset + software learning | 72.92% | 95.83% | 60.23% |
| Rewired + learning | 65.97% | 93.06% | 55.68% |
| No propagation + learning | 72.22% | 95.83% | 54.55% |
| Frozen learning on reversal | 72.92% | 95.83% | 0% |
| Never learning | 39.58% | 33.33% | 55.68% |

Four seeds are insufficient to establish a reliable wiring advantage. The reward advantage of a software learning rule over no learning is descriptive. Tests: **28 isolated Python tests passed**, including sensor pixel interpretation, sensory occlusion, hidden-reward nonleakage, collision, deterministic replay and data hash checks. Independent rerun of seed 0 reproduced its 15 MB per-tick ledger with SHA-256 `1c0e419930abd8d5ce71447c78e2832066a474500485167eafbfce39a720ed8b`.

**Video locally exported:** H.264 1280×720 at 10 fps, 1,976 frames / 197.6 sec; SHA-256 `2ddae944eb909a301e0b7e99ac2cf0ec5838ee91dbaadec9504b6696ccb1607d`. It is a **rendered execution replay, not a live animal or hardware camera**. No video is hosted in this repository.

## Data/source/license boundaries

FlyWire-derived input data: `data/real_flywire_subset.json`, SHA-256 `5b596574367d7e0e64489509a926a0305581f18568d12fef4339de5b49520cf4`. Third-party upstream source: https://github.com/DenisSergeevitch/desktop-fly/blob/master/data/circuit.json (source blob `10a7d0726571881e77e93e33bd7a23d900025e49`). The derived data carries **CC BY-NC 4.0 noncommercial** terms; it should not be silently shipped in commercial Beast Box. Anatomical connectivity is real-data-derived; simulator physiology, sensors, motor decoding, neural sign assumptions and software Q-learning are assumed. No biological learning, sentience or live-hardware inference claims.

## Unresolved / blocked

The local code/evidence package still needs a real GitHub source sync and CI; the previous GitHub source-blob upload was blocked, and network git is unavailable in the local runtime. Full COSMOS memory/CNS/R12/SYNAPSE/HEARTLIGHT/provider integration, a properly licensed commercial dataset, full-scope connectome simulation, production smoke tests and merge remain open gates.

**Merge-ready: NO.** Preserve the historical reports and all negative/null results. `MODEL ≠ SYSTEM; MODEL ≠ MEMORY; MODEL ≠ AUTHORITY.`


## Subsequent isolated build / grow / visible-42 continuation (2026-09-20)

A new local evidence package was created by resuming the earlier sensor-quest archive. **Only this documentation is being committed here; no new executable source, data, artwork, trace, or video is present in this GitHub branch.** The user has the separately exported 27.8 MB local ZIP and 23.4 MB MP4.

The local implementation adds a 42-neuron connectivity graph showing state-derived simulated activity; 96×64 virtual retinal input and station-specific simulated odor; a proximity/permission-gated virtual action set; modeled pickup, carrying, placement, nest building, seed planting, growth, feeding and software-offspring creation. The high-level 11-stage task order is authored by the experimenter; navigation is sensor-driven. Decorative pixel-art forest imagery is **not** the camera's physics/sensor world, and no biological reproduction or learned construction is claimed.

Four matched seeds per condition; 20 completed runs in total:

| Condition | Mean stages / 11 | Built nest | Grew patch | Software offspring spawned | Offspring reached food |
| --- | ---: | ---: | ---: | ---: | ---: |
| Real-derived 42-node subset | 11 | 4/4 | 4/4 | 4/4 | 4/4 |
| Rewired topology | 11 | 4/4 | 4/4 | 4/4 | 4/4 |
| No neural propagation | 11 | 4/4 | 4/4 | 4/4 | 4/4 |
| Build action disabled | 4 | 0/4 | 0/4 | 0/4 | 0/4 |
| Reproduction disabled | 9 | 4/4 | 4/4 | 0/4 | 0/4 |

The original biological-data-derived subset had **no observed stage-completion advantage** over controls. Four seeds and a scripted goal policy do not support a biological cognition or independent-planning claim. The previous separately measured food-association learning experiment remains historical; this new task does not itself establish new learning.

**Local verification:** 41 isolated tests passed, one skipped; an independent repeat reproduced the complete 20-run ledger and results JSON byte-for-byte. SHA-256 of the new ledger: `74f61c112f99baf155f9a823375b88ae41a0e7b29ebffd238cbe28d90fc4c609`.

**Local video:** 337.6 seconds (5:37.6), 1280×720 H.264, 8,440 encoded frames at 25 fps from 1,688 distinct renderer frames at 5 fps (duplicated display frames only). SHA-256: `ac58be4895c9941335b26aba39b6a2262fffcd33c1c57b08b645e24223edeb12`. This is a rendered replay of actual saved virtual-agent simulation traces, not real animal, hardware camera, or screen capture. Per-step virtual camera interpretations were checked against archived observations.

**Outstanding gates:** transfer actual runnable code/video/evidence into a feature branch, independent GitHub CI, full production interfaces, commercial licensing review for the CC BY-NC 4.0 FlyWire-derived input, and review before merge. **Not merge-ready.**

## Subsequent IBM historical replay + sandbox typing experiment (2026-09-20)

**Important repository boundary:** the runnable code, nine-record derived input, full traces, screenshot, and 7:01.67 MP4 are in the separate local experiment ZIP, **not committed to GitHub**. This commit records execution status only, and the branch remains **NOT MERGE READY**.

Recovered real source data: `NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2/workload_decode_summary.json`, source Git blob SHA-1 `084282a26bf923f03188a2be4c36f3fb34b09987`. Nine source-reported historical `ibm_fez` measurement summaries (March 12, 2026; 4,224 shots per job; 38,016 source-reported shots) were encoded as a small, bounded simulated neural drive. **No live IBM call, no raw QPU result independent re-decoding, and no claim of all workloads.**

The earlier FlyWire-derived 42-node/95-edge anatomical subset and virtual camera/odor/touch/heading remain integrated. The upstream COSMOS bio interface's `MockBioProvider` is explicitly simulated, so **no verified personal EEG/HRV/GSR/ECG signal was injected**; the new normalizer rejects fabricated/missing-provenance bio packets.

A sandbox-only `type_token` permission now maps completed virtual-world events to a 36-word maximum finite vocabulary; 24 allowlisted words were emitted on successful runs (for example `BUILT NEST`, `HELLO LITTLE FLY`). This is NOT learned language or a host keyboard.

**Execution:** six seeds × six matched arms = 36 completed simulations. All arms completed 11/11 authored stages (no stage-completion performance advantage). Mean steps: quantum replay 210.83; replay disabled 210.83; shuffled 211.00; rewired 211.83; no propagation 212.50; typing disabled 210.83. Typing-disabled emitted zero words. Replay versus disabled showed seed-0 mean absolute 42-node neural-state difference 0.03823973 (a numerical coupling result, not behavioral improvement).

**Checks:** 46 isolated Python tests passed, three skipped. Independent 36-run reproduction: byte-identical `runs.jsonl`, SHA-256 `de90389a00482411c7a65e5dd6fc883ca2d53d60ebfb1db04b51b88f0c0dca52`. Rendered video: 421.666667 sec, H.264 MP4 1280×720, SHA-256 `08b887f50b0b543fd0ca3b2dbd718813170a0dda18f14184f5274a251c691564`, **not** live hardware or camera footage. No video is hosted on this branch.

Remaining gates: actually sync source/evidence/video, CI on committed source, license review of CC BY-NC 4.0 FlyWire-derived material, verified physiological source if requested, and broader IBM archive processing. Do not merge or claim biological language acquisition.


## Supervised compositional typing continuation (2026-09-20)

A separate isolated experiment replaces the prior event-to-phrase lookup with a teacher-supervised factorized two-token software decoder. Six camera-perceived objects and three rendered gesture glyphs produce 18 possible object/gesture combinations; 12 combinations are taught, six withheld. Prediction occurs before feedback, and tests provide none. Both noun and verb meanings are deranged at reversal and retrained. The grammar itself is fixed by the experimenter. Permission-gated typing writes only to a local data structure, not the host keyboard.

Execution: eight matched seeds times nine arms = 72 runs, 60 trials per run = 4,320 episodes. The original-derived-topology, historical nine-record IBM replay, factorized learner condition typed 48/48 held-out novel combinations and 48/48 post-reversal novel combinations. The whole-phrase memorization control recalled 96/96 familiar pairs but achieved 0/48 novel combinations. Frozen reversal learning achieved 0/48 post-reversal novel; typing disabled delivered no phrases despite correct internal predictions. Replay disabled, shuffled, rewired and no neural propagation each achieved 48/48 on both novel phases. Hence the software's factorized representation, not the biological topology or quantum data, explains the improvement. Replay versus disabled altered seed-0 modeled neural states (mean absolute delta 0.07004383) without a typing benefit. This is constrained supervised symbolic composition, not natural-language learning or biological speech.

Verification: 56 isolated tests passed, three skipped. Independent full eight-seed rerun reproduced results.json and runs.jsonl byte-for-byte. Ledger SHA-256: 78c55b6947076bf0a7c96bd03619e0d8919c703affff2729f52ec3e02488f9cd. Rendered 7-minute simulation replay: H.264 1280x720 at 4 fps, 1680 frames, video SHA-256 0e1f5945f5238597002e7fd5020843042d0c214ceb3a6831f664aa8fdd3be9ad. The standalone ZIP was extracted and all 56 tests passed (three skipped). ZIP SHA-256: 504e5d5391b6fe8c9371054395918f365989e3ad5f3e08e4073074e26215a9f9.

GITHUB SYNC STATUS: documentation only. Runnable source, ledger, seven-minute video and complete ZIP remain locally exported and are NOT committed or hosted on this feature branch. Preserve earlier nulls and prior work. No merge readiness. FlyWire-derived CC BY-NC 4.0 licensing, full COSMOS product integration, verified physiological input, broader IBM archive processing and GitHub CI are open gates.
