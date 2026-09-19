"""Scope and negative-control tests for preregistered CST shadow ablation."""
import dataclasses
import math
import unittest

from cst_candidate.model import Entity, Parameters, evaluate
from run_cst_ablation_004 import micro_case, measure, stellar_case, START_SEED


class CandidateShadowAblationTest(unittest.TestCase):
    def test_stellar_score_equals_eta_zero_without_fitted_boost(self):
        row = measure(stellar_case(START_SEED), Parameters())
        self.assertGreater(row["max_abs_info_j"], 0.0)
        self.assertEqual(row["corrected_minus_ablated_binary64_changed"], 0)

    def test_micro_score_detects_information_and_shuffling(self):
        p = Parameters(r0_m=1, softening_m=0.1, reference_energy_j=1e-20, temperature_k=300)
        row = measure(micro_case(START_SEED), p)
        self.assertGreater(row["max_abs_info_j"], 0.0)
        self.assertGreater(row["corrected_minus_ablated_binary64_changed"], 0)

    def test_zero_info_negative_control(self):
        e = [dataclasses.replace(x, information_bits=0.0) for x in micro_case(START_SEED)]
        p = Parameters(r0_m=1, softening_m=0.1, reference_energy_j=1e-20, temperature_k=300)
        self.assertEqual(evaluate(e, p, "corrected"), evaluate(e, p, "ablated"))

    def test_invalid_physical_input_fail_closed(self):
        e = micro_case(START_SEED)
        e[0] = dataclasses.replace(e[0], mass_kg=float("nan"))
        with self.assertRaises(ValueError):
            measure(e, Parameters())


if __name__ == "__main__":
    unittest.main()
