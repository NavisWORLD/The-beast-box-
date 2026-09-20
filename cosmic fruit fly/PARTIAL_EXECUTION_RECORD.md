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
