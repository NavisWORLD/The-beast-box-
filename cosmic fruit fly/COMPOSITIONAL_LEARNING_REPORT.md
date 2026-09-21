# Cosmic Fruit Fly — supervised compositional typing test

**Execution:** 2026-09-20. **Classification:** isolated software experiment with source-derived anatomical connectivity and historical quantum-summary replay. This is NOT a biological language experiment, general intelligence test, live IBM execution, or real physiological recording.

## What changed from the previous 7-minute recording

The previous typing output was an event-to-phrase lookup (`quantum_language.py:VOCAB`); this new experiment leaves it intact as a historical control and adds `learn_compositional_text.py` with supervised mapping from **simulated 96×64 virtual-camera pixels** and three distinct **rendered gesture-color glyphs** to two-token utterances. The program supplies a fixed *NOUN VERB* grammar, an instructor for training labels, a bounded phrase-only terminal, and isolated learned noun/verb associations. It does NOT present the object's name, correct phrase, reward or goal location to the decoder. The environment itself determines object placement; visually decoded RGB features and the glyph enter the communication learner. Decoders train on the two components independently, not on a full phrase lookup.

This is compositional generalization in a designed **software symbol task**: no spontaneous word invention, unsupervised acquisition, natural-language understanding, learning to build, or biological causal claim. Both the vision palette and glyph palette remain stable; the six noun and three verb tokens are randomly permuted per seed, so their association must be acquired with supervision. Reversal cyclically remaps both sets; previously observed pairings receive updated feedback. The apparent text is an in-memory permitted sandbox event only, not a host keyboard.

## Preregistered task split and controls

Six objects (stick, leaf, seed, nest, patch, food), three observed glyph types (notice, mark, remember), 18 possible pairs. Exactly six combinations (one per noun, two per glyph) are held out. Twelve remaining pairs provide teacher feedback; all object and action components appear during training. Training evaluations are **predict-before-feedback**. After training, evaluate all 12 previously seen pairs *without* feedback and six novel combinations *without* feedback. Then cyclically shift all six noun-token associations and all three action-token associations. Retrain using the same 12 pairs, evaluate again on retained and novel combinations without feedback. A frozen-learning control refuses the reversal labels; a whole-phrase memorizer learns pairs but cannot assemble new ones. Testing outputs only affect local reward measurements. No privileged text labels pass through sensor features or neural dynamics.

Eight matched seeds × nine arms = **72 completed runs**; 60 trials per run = **4,320 supervised/held-out episodes**. Each trial generates seven egocentric camera/brain/dyn12 states; seed 0's recorded primary arm has 420 observed pose-and-state snapshots. The graph input is the previously checked, intentionally biased 42-node, 95-edge FlyWire-derived subset. Neural dynamics, sensory encoding and token grammar are computational assumptions.

## Observed results (outcome = correct two-token phrase AND permitted sandbox typing)

| Arm | Seen pairs before reversal | Novel pairs before reversal | Seen pairs after reversal | Novel pairs after reversal |
|---|---:|---:|---:|---:|
| Original-derived topology + nine-job quantum replay + factorized learner | 96/96 | 48/48 | 96/96 | 48/48 |
| Same, replay off | 96/96 | 48/48 | 96/96 | 48/48 |
| Shuffled replay order | 96/96 | 48/48 | 96/96 | 48/48 |
| Rewired connectivity | 96/96 | 48/48 | 96/96 | 48/48 |
| No neural propagation | 96/96 | 48/48 | 96/96 | 48/48 |
| Whole-phrase memorizer | 96/96 | 0/48 | 96/96 | 0/48 |
| Never-learning control | 0/96 | 0/48 | 0/96 | 0/48 |
| Learning frozen at rule reversal | 96/96 | 48/48 | 0/96 | 0/48 |
| Typing permission denied | 0/96 | 0/48 | 0/96 | 0/48 |

**Typing permission control:** its internal symbol predictions were still 96/96 on retained and 48/48 on novel pairs before/after reversal, but *zero* messages passed the actuator gate. Earlier exploratory code initially hit an output-capacity ceiling during the final phase; corrected to a bounded 128-message terminal before this final rerun. The preliminary capacity-confounded result is NOT part of the final comparison.

The original historical replay changed seed-0 modeled neural state compared to replay disabled (mean per-neuron absolute difference **0.07004383**), but no change in test message accuracy. **All full-task performance gain is explained by the deliberately factorized software learner, not biological topology or the IBM signal.** Perfect generalization is specific to a noiseless, small, stable-color task; it does not extrapolate to new unseen object classes or unconstrained communication.

## Reproduction and artifacts

From the extracted project root containing the unchanged `beastbox/dyn12.py`:

```bash
cd 'cosmic fruit fly'
python -m pytest -q tests
python learn_compositional_text.py --seeds 8
python render_compositional_video.py --preview --output preview.png
python render_compositional_video.py --output movie.mp4
```

The latest full regression returned **56 passed, 3 skipped**. A complete, independent second eight-seed execution reproduced **both `runs.jsonl` and `results.json` byte-for-byte**, not just aggregate scores. Recorded ledger SHA-256: `78c55b6947076bf0a7c96bd03619e0d8919c703affff2729f52ec3e02488f9cd`. H.264 MP4, 1280×720, 4 fps, 1,680 frames, **420 seconds (7 minutes)**, SHA-256 `0e1f5945f5238597002e7fd5020843042d0c214ceb3a6831f664aa8fdd3be9ad`. The video is a **rendered replay of the executed simulator's pose, retina, neural and state snapshots**. The pixel-art forest is decorative; it is not the vision sensor's input. Target labels shown in the video are *post-prediction evaluation overlays*. No audiovisual frame implies the experimenter let the fly read a teacher answer during the test.

## Source/authority/release boundaries

- FlyWire-derived input: `data/real_flywire_subset.json`. Third-party extraction from FAFB v783: https://github.com/DenisSergeevitch/desktop-fly/blob/master/data/circuit.json ; the underlying FlyWire-derived material is **CC BY-NC 4.0** and is NOT licensed for unrestricted commercial incorporation.
- IBM replay: nine historic source-reported `ibm_fez` entries from https://github.com/NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2/blob/main/workload_decode_summary.json . This is neither all historical workloads nor revalidation of the QPU's raw output; no live hardware call was made.
- The upstream COSMOS `MockBioProvider` is simulated. No verified EEG, HRV, GSR, ECG, or other personal physiological packet was injected.
- `MODEL != SYSTEM`, `MODEL != MEMORY`, `MODEL != AUTHORITY`. No external tools, host keyboard, network, actuator, deployment or filesystem rights are granted to the simulated agent. Evidence writing by the researcher is separate.
- **Local package only:** these runnable files, video and full ledger are not yet synced to the Beast Box GitHub feature branch. No CI on the new source, no PR/merge, and no claim of readiness. Preserve previous nulls and history unchanged.
