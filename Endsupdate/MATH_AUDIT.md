# Historical CST formula audit

Historical source: `NavisWORLD/The-theory-of-CST/CST_Formula_Explanation.markdown` at repository revision `306362e45af5ed3ac69a2b69cee4e3cddd066b77`, source blob `f388c8090c256acb0ca79dcb08e300b6cdc864ad`. Early simulation source: `PHERACLEASE/test/test1maybe.py` at `10e86764c6d743b5ceaaaf1baab7279a0d6f0ba5`. Numerical transcription: `cst_candidate/model.py:legacy_raw`; this preserves the algebra and the historical rounded c and ħ for comparison, with input validation and explicit singularity errors.

**Dimensional defects:**
- `φ(mc²+Echaos) + c λ + 1` adds joules, metres per second squared (c × inverse seconds) and a dimensionless 1. The accompanying document calls that weighting dimensionless without a conversion.
- `G m_i m_j / (r c²)` has **kg**, not dimensionless units. Multiplication by `mc² + Echaos` thus produces kg·J, not J.
- `k_B T / c` has J·s/m; multiplying the alleged entropy-bit product and `1/r` yields J·s/m², not J. The original prose incorrectly calls it J/m and then J. It also assumes an area-law horizon expression for non-horizon objects.
- A hypothetical `V_12D ≈ 10^144 m^12` has no measured geometric specification. A software vector of length 12 is not evidence for a twelve-dimensional physical volume.
- `r=0` is singular, `mc² + Echaos = 0` divides by zero, large horizon-bit products can overflow, and distinct dimensional terms can dominate regardless of the hypothesized mechanism. The document's illustrative numerical scaling is not a reliable unit verification.

The historical numerical output retains mixed units intentionally; its scalar cannot be meaningfully compared to a corrected dimensionless score as a common physical observable. The current operational dyn12 is a **12-scalar software reference**, not a physical-12D assertion; it is not mathematically invalidated by this audit.

See `CORRECTED_CST_SPEC.md` for the explicit research candidate, with no forced physical-law claim.
