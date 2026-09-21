# CORY DAVIS // Cosmic Fruit Fly — Three-Token Hard Mode (2026-09-20)

**Scope:** Isolated software simulation of an artificial virtual fruit-fly controller. Executed with FlyWire-derived 42-node/95-edge anatomical subset, canonical dyn12 software state and optional replay of **nine historical IBM `ibm_fez` summaries**. This is **not** a biologically realistic full fly brain, live IBM execution, live animal, actual reproduction, general language model, spontaneous language, or measured AI advantage from QPU inputs.

## What was implemented and run

- **Three-token messages** from a fixed experimenter-designed grammar: one of **eight visually distinguishable object classes** (`stick`, `leaf`, `seed`, `nest`, `patch`, `food`, and two new few-shot classes `crystal`, `water`), one of three gesture glyphs, one of three intent glyphs.
- **48 taught combinations** and **24 predeclared withheld combinations**, so every component but not every combination appears in supervision. Test-only 96x64 camera inputs include **20–28% simulated object-pixel masking and nine nonsemantic distractor speckles**, with no teacher feedback at test. This does **not** test entirely unseen categories without examples, realistic camera noise, open-ended language, or learned grammar. The RGB segmentation uses fixed calibrated object-color prototypes, so the sensory task is deliberately easy.
- A separately permission-gated **in-memory three-token typing actuator** and **in-memory resource gate**. Wrong/unrecognized/unauthorized output fails to unlock the resource. The environment alone holds the target message; predictions are computed before any teacher feedback. No real keyboard, external shell, device, network, cloud or deployment authority.
- Reverse all eight object-, three gesture-, and three intent-token mappings; train again on the **same 48** combinations and test on the **same withheld 24** without feedback. A simulated software offspring copy inherits the parent's trained lookup maps, and a blank-offspring control starts empty. Copying these dictionaries is not biological inheritance.
- Ten matched conditions across four fixed seeds; graph rewiring, no neural propagation, IBM replay off, replay shuffled, holistic phrase memory, no learning, frozen reversal, denied typing and blank offspring controls. **The software decoder consumes the camera-derived discrete features, NOT the 42-node neural state or dyn12.** Consequently, this test cannot establish that wiring or QPU input produces linguistic ability; those values are displayed and logged as separate modeled states.

## Results

**40 complete runs × 264 trials = 10,560 trials.** Every count below is over the four-seed aggregate. A correct message must also be permitted and unlock the resource to count.

| Condition | Previously trained (pre-flip) | Held-out + noise | Reversed held-out + noise | Offspring held-out + noise |
|---|---:|---:|---:|---:|
| Source-derived topology + historic IBM replay | 192/192 | 96/96 | 96/96 | 96/96 |
| Replay off | 192/192 | 96/96 | 96/96 | 96/96 |
| Shuffled replay | 192/192 | 96/96 | 96/96 | 96/96 |
| Rewired topology | 192/192 | 96/96 | 96/96 | 96/96 |
| No neural propagation | 192/192 | 96/96 | 96/96 | 96/96 |
| Holistic phrase memory | 192/192 | 0/96 | 0/96 | 0/96 |
| No learning | 0/192 | 0/96 | 0/96 | 0/96 |
| Frozen reversal | 192/192 | 96/96 | 0/96 | 0/96 |
| Typing denied | 0/192 | 0/96 | 0/96 | 0/96 |
| Blank offspring | 192/192 | 96/96 | 96/96 | 0/96 |

A software factorized mapping generalizes under this simplified test; whole-phrase memorization does not. These are deterministic design-specific counts, **not evidence of general language learning**. No task-success difference is observed between source-derived wiring, rewired, no propagation, and replay-off/shuffled conditions. Historical replay versus off altered the seed-0 *simulated neural state* (mean absolute per-neuron difference **0.01708587**) without changing language success.

## Verification and provenance

- Isolated regression suite: **63 passed, 3 skipped** with historical video artifact in place. The first regression attempt failed one test because the copied workspace lacked the earlier movement video; the missing verified historical evidence was restored intact, then the full suite passed. Do not misrepresent the first run as passing.
- Independent full four-seed re-execution: **byte-identical `runs.jsonl` and `results.json`** to the primary run.
- Ledger SHA-256: `4b8bf249a4559df6c55ecd6b9205fc847f737660ecb4e31536b206b29ad36666`.
- Source subset SHA-256 (unchanged): `5b596574367d7e0e64489509a926a0305581f18568d12fef4339de5b49520cf4`.
- Video: **7:28** (448 sec), H.264 MP4, 1280×720, 4 fps, 1,792 frames; 112 predeclared evenly-spaced trials across the 7 phases from the actual seed-0 primary run. Renderer checks source-code/source-data/ledger hashes and the reconstructed virtual camera hash for every rendered frame. The fruit-fly pose within each trial is a simple cosmetic animation; the 42-neuron/dyn12 series comes from actual executed trial snapshots. The forest picture is decorative, not the simulated camera input.
- Video SHA-256: `c93490433604a813f5b7d150eb28f3afdbd17094774a95e43b420cf08078f6d7`.

## Reproduce from this ZIP

```bash
python -m pip install numpy pillow pytest
cd 'cosmic fruit fly'
python -m pytest -q tests
python hard_mode.py --seeds 4 --output hard_mode_verify
python render_hard_mode.py --preview --output preview.png
# Requires ffmpeg executable on PATH:
python render_hard_mode.py --output replay.mp4
```

Compare `hard_mode_verify/runs.jsonl` and `hard_mode_demo/runs.jsonl` byte-for-byte. For the archived replay, keep the original `hard_mode_demo` results and code checksums unmodified. The execution includes local-only evidence file writes, not agent-granted external authority.

## Scientific / licensing / release boundary

The anatomical input originates from a nonrepresentative 42-neuron subset of third-party FAFB/FlyWire-derived data with **CC BY-NC 4.0** terms. Commercial distribution requires license clearance; do not silently merge that data into the commercial Beast Box. The nine IBM inputs are *source-reported historical summaries*, not the entire IBM archive and not an independently decoded raw QPU sample. No verified personal biosignal source was injected; a mock bio stream is not physiologic evidence. Do not claim measured advantage from biology or quantum, emergent grammar, open-ended speech, consciousness, or a production-safe merge. This is a reproducible isolated experiment; live integrated product CI and commercial license gates remain open.
