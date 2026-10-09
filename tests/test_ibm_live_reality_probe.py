"""Offline deterministic safety tests; no IBM or Azure credential required."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "ibm_live_reality_probe.py"
SPEC = importlib.util.spec_from_file_location("ibm_live_reality_probe", SOURCE)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class IBMRealityProbeTests(unittest.TestCase):
    def test_healthy_open_plan_requires_explicit_headroom(self):
        q = module.guard_usage({
            "usage_limit_seconds": 600,
            "usage_consumed_seconds": 40,
            "usage_remaining_seconds": 560,
            "usage_limit_reached": False,
        }, "test-instance")
        self.assertTrue(q["headroom_for_one_300_second_job"])
        self.assertEqual(module.QPU_LIMIT_SECONDS, 240)
        self.assertLessEqual(module.QPU_LIMIT_SECONDS, module.OWNER_MAX_TOTAL_SECONDS)
        self.assertNotIn("test-instance", str(q))

    def test_fail_closed_on_partial_quota_and_paid(self):
        for data in (
            {"usage_limit_seconds": 600, "usage_consumed_seconds": 320, "usage_remaining_seconds": 280},
            {"usage_limit_seconds": 1200, "usage_consumed_seconds": 0, "usage_remaining_seconds": 1200},
            {"usage_limit_seconds": 600, "usage_consumed_seconds": 0, "usage_remaining_seconds": 601},
            {"usage_limit_seconds": 600, "usage_consumed_seconds": 0},
        ):
            with self.subTest(data=data), self.assertRaises((RuntimeError, ValueError)):
                module.guard_usage(data, "test-instance")

    def test_measured_counts_strict(self):
        self.assertEqual(module.validate_counts({"00": 140, "11": 116}, 256),
                         {"00": 140, "11": 116})
        for counts in ({"00": 255}, {"000": 256}, {"00": -1, "11": 257},
                       {"00": True, "11": 255}, {"00": 100, " 00": 156}):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                module.validate_counts(counts, 256)

    def test_linked_vs_product_expectation(self):
        self.assertEqual(module.parity_stats({"00": 128, "11": 128})["z_parity_correlation"], 1)
        self.assertEqual(module.parity_stats({"00": 64, "01": 64, "10": 64, "11": 64})["p_equal"], .5)

    def test_hardware_runner_never_triggers_automatically(self):
        content = SOURCE.read_text()
        self.assertIn('GITHUB_EVENT_NAME") != "workflow_dispatch"', content)
        self.assertIn('BEAST_IBM_EXECUTION_CONFIRM") != "RUN_ONE_IBM_240S"', content)
        self.assertIn("sampler.options.max_execution_time = QPU_LIMIT_SECONDS", content)
        self.assertIn('job = sampler.run(isa, shots=SHOTS_EACH)', content)
        self.assertIn('if prior:', content)
        self.assertNotIn('IBM_QUANTUM_TOKEN": token', content)


if __name__ == "__main__":
    unittest.main()
