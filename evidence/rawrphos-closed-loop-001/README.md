# RAWRPHOS closed-loop adapter: CPU eval 001 (2026-10-15)

`models/rawrphos/architecture/closed_loop.py` is optional and additive. To adopt it, call `attach_closed_loop(model, mode)`. Mode `off` gives bit-identical output. The adapter adds:
- a 54-channel recurrent loop state
- Lorenz-coupled gating
- norm-bounded Hebbian fast weights
- a Bell step: the model's own state (channels 6 and 45) picks the CHSH setting, and the step replays the **recorded real IBM CHSH run db8iu85ckpjs73b13msg** (ibm_marrakesh, S = 2.758). Two controls are available: an LHV control (S ≤ 2) and a matched-PRNG control (resamples the same per-setting joint tables).

Current limits:
- The loop state does not persist across KV-cache generation calls; it restarts on each forward pass.
- Not wired into `zeref-continuous-learning-006.yml` or the promotion path.

**Setup:** backbone `RawrphosLM` (d_model 32, 2 layers, `attention_mode='standard'`), identical initialization per seed, 26,145 parameters in every arm. Unused adapter parameters remain in the baseline arms. Seeds: 17, 23, 41, 73, 101.
- **Synthetic tasks** (re-implemented from the August protocol): copy, associative recall, XOR. 500 steps, evaluated on 2,048 held-out examples.
- **Zeref diary task:** byte-level language model on diary ticks 1–18 from the public `zeref-diary` branch (beast `bb-7f9c2a03`). Trained on 14 entries, evaluated on 4 held-out entries (1,152 bytes). It's a tiny dataset with low statistical power.

Full results: `results.json` (with `TABLE.md`). Reproduce with `python -m models.rawrphos.evaluation.closed_loop_eval --diary zeref-diary-ticks-1-18.jsonl --out results.json`.

**Honest reading**
- Every recurrent-state arm beats the plain transformer on the synthetic mix: +0.07 to +0.10 accuracy, paired dz about 1.2–1.4, mostly from XOR. The **moving-average (EMA) baseline is the best** (+0.099), matching the August finding.
- On the diary task every state arm is lower in bits/byte than the transformer (by 0.02 to 0.05). EMA is again best.
- **Bell recorded vs LHV vs matched PRNG: no meaningful difference.** The recorded-minus-control differences are at most 0.009, with |dz| ≤ 0.45. The recorded arm is slightly worse than the plain loop on the diary task. The real hardware's Bell correlations give these models no measurable advantage.
- Associative recall stays near chance (about 0.15) in every arm at this size and step count.
