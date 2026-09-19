"""Regression and sensitivity tests for independent CST source lineage."""
import math
import unittest

from cst_candidate.diagnostics import score_diagnostics
from cst_candidate.historical_11d import Legacy11DInput, legacy_11d_psi
from cst_candidate.model import C_LEGACY, Entity, PHI, Parameters, evaluate
from tests.test_cst_candidate import sample


class Historical11DTest(unittest.TestCase):
    def test_reproduces_known_single_term(self):
        x = Legacy11DInput(mass_kg=1e30, chaos_energy_j=0.0,
                           lyapunov_s_inv=0.0, path_length_m=0.0,
                           connectivity_m_s2=0.0, gravitational_potential_j=0.0,
                           delta_t_s=.01)
        r = legacy_11d_psi(x)
        self.assertAlmostEqual(r["unclipped_psi"], PHI * 1e30 * C_LEGACY**2 / 1e132)
        self.assertFalse(r["clipped"])

    def test_11d_five_term_trace(self):
        x = Legacy11DInput(mass_kg=1e30, chaos_energy_j=1e44,
                           lyapunov_s_inv=0.01, path_length_m=1e5,
                           connectivity_m_s2=1e-10, gravitational_potential_j=-1e41,
                           delta_t_s=.01)
        r = legacy_11d_psi(x)
        self.assertAlmostEqual(r["unclipped_psi"] * 1e132,
                               math.fsum(r["term" + str(i) + "_j"] for i in range(1, 6)),
                               delta=1e-9 * abs(r["unclipped_psi"] * 1e132))

    def test_11d_invalid_fail_closed(self):
        x = Legacy11DInput(1e30, 0, 0, 0, 0, 0, 0.01)
        for options in ({"volume_m11": 0}, {"length_scale_m": -1}, {"clip_abs": float("nan")}):
            with self.assertRaises(ValueError):
                legacy_11d_psi(x, **options)

    def test_11d_historical_clipping(self):
        x = Legacy11DInput(1e30, 0, 0, 0, 0, 0, 0.01)
        result = legacy_11d_psi(x, volume_m11=1e45)
        self.assertTrue(result["clipped"])
        self.assertEqual(result["clipped_psi"], 1e-10)


class ObservabilityTest(unittest.TestCase):
    def test_macro_nonzero_info_masked(self):
        p = Parameters()
        c, a = evaluate(sample(), p)[0], evaluate(sample(), p, mode="ablated")[0]
        d = score_diagnostics(c, a, p)
        self.assertNotEqual(d["information_j"], 0)
        self.assertTrue(d["binary64_score_equal"])
        self.assertNotEqual(d["decimal_resummed_delta"], "0")
        self.assertLess(float(d["info_to_half_ulp"]), 1)

    def test_dimensionally_consistent_micro_case_resolves_info(self):
        v = (0.0,) * 12
        a = Entity(1e-12, (0, 0, 0), v, 0, information_bits=1)
        b = Entity(2e-12, (1, 0, 0), v, 0, information_bits=2)
        p = Parameters(r0_m=1, softening_m=.1, reference_energy_j=1e-20, temperature_k=300)
        c, z = evaluate([a, b], p)[0], evaluate([a, b], p, mode="ablated")[0]
        self.assertNotEqual(c["score"], z["score"])
        d = score_diagnostics(c, z, p)
        self.assertFalse(d["binary64_score_equal"])
        self.assertGreater(float(d["info_to_half_ulp"]), 1)

    def test_bad_diagnostics_reject(self):
        p = Parameters()
        c, a = evaluate(sample(), p)[0], evaluate(sample(), p, mode="ablated")[0]
        with self.assertRaises(ValueError):
            score_diagnostics({**c, "score": float("nan")}, a, p)
        with self.assertRaises(ValueError):
            score_diagnostics(a, a, p)


if __name__ == "__main__":
    unittest.main()
