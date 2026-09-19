# CST source lineage: 11-component simulator → 12-component formula → software state

This note is an additional source audit, not a replacement for the frozen Beast Box or CST histories.

| Source | Frozen repository revision | Source blob | Interpretation |
| --- | --- | --- | --- |
| [Legacy simulator `cst_engine.py`](https://github.com/NavisWORLD/The-theory-of-CST/blob/306362e45af5ed3ac69a2b69cee4e3cddd066b77/cst_engine.py) | `306362e45af5ed3ac69a2b69cee4e3cddd066b77` | `aaa138bf94e24cbd39657952877108df3e720c5e` | 11-coordinate simulator with 12-value memory vector and five-term `compute_psi`. |
| [12-component helper `cst_functions.py`](https://github.com/NavisWORLD/The-theory-of-CST/blob/306362e45af5ed3ac69a2b69cee4e3cddd066b77/cst_functions.py) | same | `7c222c56af9bba932827cc303d3f4db4835f4345` | Another implementation of the 12D informational term: uses the `entropies` array inside an area-law-like expression and an arbitrary `1e-36` volume. It is not the exact same algorithm as the prose document. |
| [Expanded 12D formula](https://github.com/NavisWORLD/The-theory-of-CST/blob/306362e45af5ed3ac69a2b69cee4e3cddd066b77/CST_Formula_Explanation.markdown) | same | `f388c8090c256acb0ca79dcb08e300b6cdc864ad` | Exact algebra transcribed in `cst_candidate/model.py:legacy_raw`. |
| [CST 2026 theory map](https://github.com/NavisWORLD/The-theory-of-CST/blob/306362e45af5ed3ac69a2b69cee4e3cddd066b77/docs/CST_2026.md) | same | `5f6296c73da5de024d0ec3dc6e9de3d282c84068` | Distinguishes computational state dimensions from physical spacetime. |
| [Operational Beast Box dyn12](https://github.com/NavisWORLD/The-beast-box-/blob/8f90e440f0f4ceba502b1a3f8637507491fb23b0/beastbox/dyn12.py) | `8f90e440f0f4ceba502b1a3f8637507491fb23b0` | `6413b9e7da6ebf989693a6122fcb9306a30d0012` | Unmodified, bounded, 12-scalar SOFTWARE reference update. |

## The additional 11D baseline

Source `CSTEntity.compute_psi` evaluates, with `E_c = m c² + E_chaos`:

```text
t1 = φ E_c
t2 = λ E_c Δt
t3 = L m c² / 1e12
t4 = Ω E_c / a0
t5 = Ugrav
psi = clip((t1+t2+t3+t4+t5)/V11, -1e-10, +1e-10)
```

`legacy_11d_psi()` reproduces that algebra for explicitly supplied intermediate values, and returns both the unclipped and clipped results. It **does not** claim end-to-end equivalence: the simulator's upstream state, random sampling, neighbor/velocity-derived Lyapunov heuristic, path measurement and connectivity preprocessing remain outside this pure reference. In particular, `log1p(abs(sum(velocity differences)))` in the historical Lyapunov calculation applies a logarithm to a dimensional quantity without a specified velocity reference, so numerical `λ` should not be interpreted as a measured physical Lyapunov exponent.

A dimensional reading of t3 needs `1e12` to represent a reference length in metres; the historical code does not label its unit. The terms t1, t2 and t5 have J units if their inputs are as labeled; t4 has J units if `Ω` is acceleration and `a0` has the same units. The `V11=1e132 m^11` geometry and output clip are chosen simulation settings, not independently observed physical quantities. These issues are distinct from the **algebraically invalid addition of unlike dimensions** in the later 12D formula.

## The different 12D helper

`cst_functions.py:compute_psi_i` is NOT numerically interchangeable with the expanded formula document. It sets `e_chaos=m c² λ` although `λ` is documented in `s^-1`, changes the interpretation of informational input from an object area/radius to passed entropies, and divides by `1e-36` rather than the document's hypothetical `1e144`. It also treats `R_0=1e6 m` as approximately one megaparsec in a comment, a conversion error: one megaparsec is approximately `3.086e22 m`. This helper is a separate historical variant, not a trustworthy reference for calibration of physical predictions.

None of the three research equations licenses rewriting the operational dyn12, model weights, stored memory or host authority. Preserve the original numerical findings and negative controls separately.
