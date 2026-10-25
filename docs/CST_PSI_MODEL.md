# CST ψ, Hebbian outer-product rule and the live tick (MODEL / SIMULATED)

Everything here is Cory Davis's **12-Dimensional Cosmic Synapse Theory (CST) as a model simulation**. It is a hypothesis
he is exploring, not a proven physical law, and nothing in this code claims proof, awareness or consciousness. RAWRPHØS
is his own Hebbian transformer and is not touched here.

Labels used: ψ = **MODEL** · per-second ticks = **SIMULATED** · IBM seed = **RECORDED** · placement = **SEEDED**.

## 1. ψ (psi) — `apps/beastbox-cloud/lib/physics/cst-psi.mjs`

Port of `The-theory-of-CST/cst_psi.py` (the unit-consistent version, 2026-10-15; it supersedes the mixed-unit
`CST_Formula_Explanation.markdown`). Every term is an energy divided by `E_ref,i = m_i c² (1 + λ_i τ)`:

| term | meaning |
|---|---|
| K | `(1+φ+λτ)·(½ m|v|²)/E_ref` kinetic / chaotic |
| S | `Σ exp(−r/r0)·G m_i m_j / r / E_ref` screened |
| U | `−Σ G m_i m_j / r / E_ref` Newtonian |
| I | `−Σ k_B T_CMB N_i N_j (ℓ/r) / E_ref`, `N = c³A/(4ħG ln2)` bits, informational |

`τ`, `r0` and `ℓ` are explicit model parameters, not physical constants.

* `psiTerms()` / `psi()` are the exact port. `tests/cst-psi.test.mjs` checks them against reference values produced by
  running the Python file (`tests/fixtures/cst-psi-reference.json`, relative tolerance 1e-9).
* Honest observation: at physical scales the informational term I is about 1e52–1e75 while K, S, U are about 1e-7, so the
  full ψ is numerically I. That is a property of the formula as written, reported, not hidden.
* `creaturePsi()` gives each creature a ψn in (0,1) from its 11 CST channels. A creature has no masses, distances or
  horizon radii, so S, U and I are **not invented**: only the mass- and scale-free K term is computed
  (`v = channel·0.1c`, `λτ = chaos·0.9056`, the Lorenz largest exponent). Those two scales are model choices.
* Modulation (opt-in): `stepCSTState(S, dt, emotion, {psi:true})` shifts the coherence target and the Hebbian target by
  `gain·(ψn − ½)`, `gain = PSI_GAIN = 0.10`, so the nudge is bounded to ±0.05 before the usual clamp to [0,1].
  Without the flag the step is bit-identical to the original (a frozen copy of the old rule is compared in the tests).

## Lorenz dt: 0.35 here vs 0.035 in Sim Earth

Both engines use explicit Euler Lorenz with σ=10, ρ=28·(1+0.30·(arousal−½)), β=8/3. The Sim Earth reference
(`standalone/SIM_EARTH_7_08_REALITY_BODY.html`) advances it by `dt·0.035`; `stepCSTState` uses `dt·0.35`, ten times faster.
At the ≤50 ms steps Beast Box uses, 0.35 gives livelier wind/turbulence for cosmetic motion. This is a visual-tempo choice
made in the port. It is not calibrated against, or measured to match, Sim Earth. Anyone comparing trajectories between the
two must rescale time by 10.

## 3. Per-second live tick now runs on the CST integrator (SIMULATED)

`lib/zeref/live-tick.mjs`: the per-second wiggle of each recorded diary signal used to be a hash wander (±3). The default
engine is now `stepCSTState` (with the `{psi:true}` MODEL nudge), driven by the recorded signals
(energy→arousal, resonance/warmth→valence, curiosity/signal/memory→curiosity), settled for 600 warm-up steps, then stepped
6×0.05 per live second. Each recorded signal shows `recorded ± 3`, where the offset is the movement of one CST channel since
second 0 (energy→chaos, signal→Lorenz x, memory→coherence, resonance→resonance; other keys are assigned by a seeded hash).

What did **not** change: the label stays SIMULATED; the clock is injected; no `Math.random`; `liveSecond(base, nowMs)` is
still a pure function (second N is always second N; a per-base cursor only caches it, and going backwards recomputes from
second 0); the xp rule; the rolling hash chain over every second; the recorded diary is only read, never written.

Fallback: `liveBase(d, {engine:'wander'})`, a diary with no signals, and any second beyond `CST_MAX_SECONDS` (1 day with no new
recorded tick, to keep catch-up under about a quarter of a second) use the previous hash wander, unchanged and pinned in the tests.
Chain compatibility: the CST engine uses the schema `beast-live-tick/v2` and a different chain genesis and head key, so a head
chained under the old engine is never resumed under the new one: the run restarts that segment from second 0.
Lorenz tempo: see the dt note above (0.35 vs 0.035): one live second is about 0.105 Lorenz time units here.
