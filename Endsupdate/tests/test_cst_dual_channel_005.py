"""Research-only dual-channel numerical tests; no model or runtime mutation."""
import dataclasses
import math
import unittest

from cst_candidate.dual_channel import information_channels
from cst_candidate.model import Parameters, evaluate
from run_cst_ablation_004 import micro_case, stellar_case
from run_cst_dual_channel_005 import SEED_START, evaluate_case


class IndependentInformationChannelTest(unittest.TestCase):
    def test_independent_stellar_signal_survives_aggregate_cancellation(self):
        entity = stellar_case(SEED_START)
        p = Parameters()
        old = evaluate(entity, p, "corrected")
        old_without = evaluate(entity, p, "ablated")
        fresh = information_channels(entity, p)
        self.assertTrue(any(c.signed_log_signal != 0 for c in fresh))
        self.assertTrue(all(math.isfinite(x["score"]) for x in old + old_without))

    def test_dimensionless_thermal_reconstruction_and_eta_zero(self):
        entity = micro_case(SEED_START)
        p = Parameters(r0_m=1, softening_m=0.1, reference_energy_j=1e-20, temperature_k=300)
        actual = evaluate(entity, p, "corrected")
        channels = information_channels(entity, p)
        for c, a in zip(channels, actual):
            self.assertTrue(math.isclose(
                c.reconstructed_information_j, a["information_j"], rel_tol=1e-13, abs_tol=0
            ))
        zero = information_channels(entity, dataclasses.replace(p, eta=0))
        self.assertTrue(all(c.signed_log_signal == 0 for c in zero))

    def test_zero_information_and_negative_eta_fail_closed(self):
        zeroed = [dataclasses.replace(x, information_bits=0) for x in stellar_case(SEED_START)]
        self.assertTrue(all(c.geometric_potential == 0 for c in information_channels(zeroed)))
        with self.assertRaisesRegex(ValueError, "eta"):
            information_channels(zeroed, Parameters(eta=-1))

    def test_separately_seeded_aggregate_versus_channel_comparison(self):
        row = evaluate_case(stellar_case(SEED_START), Parameters())
        self.assertTrue(0 <= row["original_aggregate_corrected_vs_eta_zero_different"] <= 3)
        self.assertGreater(row["dual_channel_corrected_vs_eta_zero_different"], 0)


if __name__ == "__main__":
    unittest.main()
