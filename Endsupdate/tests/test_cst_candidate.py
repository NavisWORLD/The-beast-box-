"""Separate mathematical tests; no mutation of the original Beast Box."""
import dataclasses
import math
import unittest

from cst_candidate.model import Entity, Parameters, evaluate, legacy_raw


def sample():
    v = (1e5,) * 12
    return [
        Entity(1e30, (0.0, 0.0, 0.0), v, 3.5e8, 9e45, .01, 100),
        Entity(2e30, (1e10, 0.0, 0.0), v, 4e8, 1e46, .02, 200),
        Entity(1.5e30, (0.0, 2e10, 0.0), v, 3e8, 8e45, .015, 300),
    ]


class CSTCandidateTest(unittest.TestCase):
    def test_legacy_finite_and_unmodified_units(self):
        self.assertTrue(all(math.isfinite(x) for x in legacy_raw(sample())))

    def test_candidate_finite_all_modes(self):
        for mode in ("corrected", "ablated", "control"):
            self.assertTrue(all(math.isfinite(x["score"]) for x in evaluate(sample(), mode=mode)))

    def test_corrected_information_ablates(self):
        s = sample()
        with_info = evaluate(s)
        without = evaluate(s, mode="ablated")
        self.assertTrue(any(a["information_j"] != 0 for a in with_info))
        self.assertTrue(all(a["information_j"] == 0 for a in without))
        # This exact-score null at stellar scales is a result, not a pass for improved accuracy.
        self.assertEqual([a["score"] for a in with_info], [a["score"] for a in without])

    def test_permutation_equivariance(self):
        a = evaluate(sample())
        b = evaluate(list(reversed(sample())))
        for x, y in zip(a, reversed(b)):
            self.assertAlmostEqual(x["score"], y["score"], places=14)

    def test_coincident_candidate_finite_legacy_rejects(self):
        s = sample()
        s[1] = dataclasses.replace(s[1], position_m=s[0].position_m)
        self.assertTrue(all(math.isfinite(x["score"]) for x in evaluate(s)))
        with self.assertRaises(ValueError):
            legacy_raw(s)

    def test_nonfinite_and_negative_reject(self):
        for bad in (float("nan"), float("inf"), -1.0):
            s = sample()
            s[0] = dataclasses.replace(s[0], mass_kg=bad)
            with self.assertRaises(ValueError):
                evaluate(s)

    def test_zero_mass_allowed_corrected_rejected_legacy(self):
        s = sample()
        s[0] = dataclasses.replace(s[0], mass_kg=0, chaos_j=0)
        self.assertTrue(math.isfinite(evaluate(s)[0]["score"]))
        with self.assertRaises(ValueError):
            legacy_raw(s)

    def test_bad_parameters_rejected(self):
        for p in (Parameters(r0_m=0), Parameters(softening_m=0), Parameters(beta=float("nan"))):
            with self.assertRaises(ValueError):
                evaluate(sample(), p)

    def test_legacy_and_candidate_not_same_metric(self):
        self.assertNotEqual(legacy_raw(sample())[0], evaluate(sample())[0]["score"])

    def test_mode_fail_closed(self):
        with self.assertRaises(ValueError):
            evaluate(sample(), mode="legacy")


if __name__ == "__main__":
    unittest.main()
