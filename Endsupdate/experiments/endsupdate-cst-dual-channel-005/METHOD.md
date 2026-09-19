# CST 005 — dual-channel information representation (research proposal)

## Mathematical idea

The corrected source expression defines an information interaction in joules:

```text
Q_i = -eta * (k_B T) * Σ_(j≠i) f(I_i) f(I_j) exp(-r_ij/r0) (r0/d_ij)
f(I) = I / (1+I)
d_ij = sqrt(r_ij² + epsilon²)
```

Its synthetic stellar aggregate computes `(K*_i+U_i+C_i+Q_i)/E_ref`. Experiments 001 and 004 establish that nonzero `Q_i` is mostly lost when it is summed with much larger terms at binary64 precision. The proposed **new computational representation**, distinct from a new physical law, is to preserve an independently evaluated *dimensionless information geometry*:

```text
h_i = Σ_(j≠i) f(I_i) f(I_j) exp(-r_ij/r0) (r0/d_ij)
Q_i = -eta * k_B*T * h_i
s_i = -log1p(eta * h_i), eta ≥ 0
```

The dimensionless scale comes directly from the source's thermal energy `k_B T`; it is not chosen to force a task improvement, fit an outcome, or modify the original energy equation. `log1p` is a monotone representational compression to preserve small signals without combining them with a large kinetic/gravity scalar. `s_i` is *not the original aggregate score*: its numerical scale cannot be compared as though it were an energy, probability, or dynamical state variable. No originality relative to all mathematics literature is asserted.

## Frozen experiment

`protocol.json` freezes independent seeds 20000–20255 (rather than reused 004 seeds 10000–10255), two synthetic input scales, the original model and operational dyn12 Git blob identities, `eta=1` versus `eta=0`, a cyclic shuffle of information-bit assignments, and zero-information controls. Both the old aggregate score and the new independent channel are observed for each of three entities across 256 cases per regime. Test that the isolated channel reconstructs the original joule-valued `Q_i` within a 1e-13 relative tolerance, responds to eta ablation as intended, and respects entity permutation. No trained coefficients or validation-driven threshold is added.

The readouts are *observability*, not prediction or intelligence: counts of exact corrected-vs-ablated and corrected-vs-shuffled float64 differences. The micro-scale control tests numerical sensitivity but provides no real-world labels. Re-run on Python 3.10 and 3.12 with raw evidence artifacts. All numerical failures and negative outcomes must be preserved.

## Authority and modeling boundary

This module is only `Endsupdate/cst_candidate/dual_channel.py`. The original `beastbox/dyn12.py`, historical evidence, model weights, routing, memories and tool authority remain unchanged. The next possible scientific gate is independent measurement of whether this channel adds useful information under *a separately justified computational mapping* to 12 software-state variables, with matched labels and task metrics. We must not derive a map merely from the desired result.

**Status before run:** proposed independent representation, not validated AI-model improvement and not a physical law.
