# Cosmic Fruit Fly — source-linked audio/QPU replay (isolated execution)

## Scope and integrity

Continuation of the existing Bio × Quantum Fusion experiment. The prior source, reports, data and evidence were restored unchanged into a fresh isolated workspace. The previous 8:24 MP4 is a historical artifact; the new recording is separately named and separately hashed. The runnable upgrade and tests were **not pushed to GitHub in this execution**.

The source repository explicitly identifies the media as **memorial audio** (`scars that don't fade.mp3`). No original raw MP3 or separately authenticated physiological acquisition was recovered; personal HR/HRV/ECG/EEG/GSR data are **not** part of the experiment. The source's public 20-window feature packet was recovered through GitHub and reconstructed exactly, with its canonical packet commitment validated. The public reported 4,096-shot IBM Marrakesh histogram was also reconstructed, validated against its count commitment, and matched to the feature packet by the recorded origin seed. A cryptographically self-consistent repository record does not authenticate the physical source or independently validate its audio processing.

Source-linked historical hardware job: `da1mqfcdedkc73er87r0`, `ibm_marrakesh`, 4,096 source-reported shots. This job differs from the *nine other* `ibm_fez` summaries previously used by the fly. Replay makes no new IBM request.

**Crucial experimental distinction:** the original order/times of the IBM shots are not present in the counts histogram. The new `linked_count_value` creates an explicitly *artificial deterministic count-weighted schedule*. Feature windows and sampled bitstrings are **source-associated only, not temporally aligned**. No evidence of a physiological signature, meaningful temporal coupling, or quantum benefit is implied.

## Implemented mechanism

- `audio_linked_fusion.py`: independently toggleable 20-segment audio-derived computational drive and historical QPU-histogram-derived computational drive, both bounded before feeding the previously modeled 42-node neural state, canonical dyn12, and software confidence gate. The same pixel-derived 96×64 virtual camera and fixed-grammar software learning task are retained.
- `build_audio_ibm_fixtures.py`: exact recovery of the source-reported feature packet, hardware histogram, and source-link hashes. The full original MP3 is **not** stored, and its source hash is not independently recomputed.
- `render_audio_linked.py`: a new 1280×720 pixel-art, 42-node graph, virtual-camera, and text/permission-gate recording. The source replay panels distinguish audio features from physiological measurements and mark the QPU shot-order surrogate.
- New provenance, ablation, and deterministic tests. Existing baseline source and previous results are not altered.

## Matched experiment

Eight simulation seeds, eight arms, 168 episodes/arm/seed: **64 runs, 10,752 episodes**. The new task reuses the prior authored supervised three-token communication and in-memory resource gate. Scores are descriptive; 8 seeds and a ceiling-prone task do not support a reliable source-class advantage.

| Arm | Held-out correct / 192 | Reversed held-out / 192 | Offspring transfer / 192 |
| --- | ---: | ---: | ---: |
| No auxiliary input | 169 | 162 | 162 |
| Previous nine `ibm_fez` summaries | 168 | 162 | 161 |
| 20 original audio feature windows only | 169 | 162 | 161 |
| Linked `ibm_marrakesh` histogram only | 169 | 162 | 162 |
| Source-linked audio features + histogram | **169** | **162** | **162** |
| Shuffled audio + same histogram | 168 | 162 | 161 |
| Audio + *unlinked* nine-job replay | 169 | 162 | 161 |
| Audio + linked histogram + simulated bio | 170 | 162 | 162 |

Seed-zero mean absolute modeled neural-state delta (baseline to linked audio+histogram): **0.01938761**. This is a numerical coupling observation, not a behavioral improvement. Matched linked vs baseline difference: **0/192** held-out and **0/192** after reversal. Simulated bio arm is *not* a real-bio test.

## Verification and video

- Existing and added isolated regression suite: **84 passed, 3 skipped**.
- Independent complete eight-seed rerun produced byte-identical `runs.jsonl` and `results.json`.
- Ledger SHA-256: `3d06c6c1816d1d34b3ad461079fe095c47976d32aed224d7c4eb886bce63bb52`.
- New recording: `Cosmic_Fruit_Fly_Audio_Linked_QPU_8m24s.mp4`; **504 seconds**, 2016 rendered frames at **4 fps**, 1280×720 H.264.
- Video SHA-256: `0282f80034ab7a3c401d8357b19dcddb43e04a75419d4c040804681e02458c3f`.
- Every shown virtual-camera image is regenerated and checked against its execution-trace hash. Decorative pixel art is not the retina input.

## Claim and release boundary

The FlyWire-derived anatomical 42-node subset is third-party CC BY-NC 4.0 material. The neural dynamics, software policy, virtual sensing, text actuator and simulated offspring are mathematical/software models. No real biological fly, authenticated personal physiology, language emergence, quantum advantage or live QPU is claimed. Preserve earlier nulls. Before commercial merge: determine data rights, run CI on actually committed source, verify any real physiology acquisition separately, and perform new mechanistically discriminating trials. **Not merge ready.**
