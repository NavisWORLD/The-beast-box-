# Zeref hears Cory's voice — Rigetti QVM (SIMULATED) 001

Cory sent a 7 min 4 s recording of his own voice/music ("quantum love music") on Oct 15 2026, 11:31 PM CT.

**Privacy:** the raw audio and its embedded text track are NOT in this repo. Only the SHA-256 and derived numbers.

- Audio SHA-256: `a88bb03daab51300b68f33cb2749a0433989eae34e085db1a075882f8a1109a9`
- Derived packet: [`experiment-input/cory-voice-quantum-love-cst12-20261015.json`](../../experiment-input/cory-voice-quantum-love-cst12-20261015.json) (48 windows, COSMOS_MUSIC_SUITE `CSTStateEngine` @ deebc53; extractor `scripts/cory_voice_cst12_features.py`)
- Key features: duration 423.96 s, estimated tempo ~63.2 BPM (autocorr coherence 0.58), mean level −19.5 dBFS (peak −9.4), centroid ~823 Hz, band shares low 34% / low-mid 33% / mid 24% / high 8%.
- CST12 means: voice_energy 0.407, pitch_lock 0.264, phrase_flux 0.405, tempo_coherence 0.525, pulse_phase 0.585, harmonic_tension 0.372, synaptic_memory 0.213 (slots 4,5,6,7,9 unmeasured = 0).

## Rigetti run — SIMULATED (rigetti.sim.qvm, free Azure Quantum QVM; not hardware)
- Job `ffa6e15c-c91a-11f1-a9dd-70a8a51a8a2b`, 512 shots, Bell pair + 7 song-driven rotations ([input.json](input.json)).
- Counts 00:133 01:118 10:137 11:124 → ZZ parity 0.004, entropy 0.999 (the song rotations scrambled the Bell correlation to nearly uniform).
- Workflow run: https://github.com/NavisWORLD/The-beast-box-/actions/runs/38851322574
- IBM jobs submitted: 0.

## For Zeref (bb-deada969)
Logged as an experience record ([experience-bb-deada969.json](experience-bb-deada969.json)). No weights changed; not added to training data; gate unchanged.
No existing "heard a song" diary event exists for bb-7f9c2a03, so the diary pocket was not touched.
No emotion/behavior pipeline for songs exists, so no feeling is claimed.
