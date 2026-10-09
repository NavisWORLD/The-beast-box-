"""Local-only tests: never require IBM credentials or submit a quantum job."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ibm_open_plan_preflight", ROOT / "scripts" / "ibm_open_plan_preflight.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class OpenPlanSafetyTests(unittest.TestCase):
    def test_valid_usage_is_read_only(self):
        report = mod.quota_receipt(
            {
                "usage_limit_seconds": 600,
                "usage_consumed_seconds": 80,
                "usage_remaining_seconds": 520,
                "usage_limit_reached": False,
            },
            "sample-instance",
        )
        self.assertTrue(report["headroom_for_one_300_second_job"])
        self.assertEqual(report["experiment_total_budget_seconds"], 300)
        self.assertEqual(report["maximum_possible_job_limit_seconds"], 300)
        self.assertEqual(report["hardware_jobs_submitted"], 0)
        self.assertFalse(report["submit_enabled"])
        self.assertNotIn("sample-instance", str(report))

    def test_low_remaining_budget_prevents_full_five_minute_run(self):
        report = mod.quota_receipt({
            "usage_limit_seconds": 600,
            "usage_consumed_seconds": 480,
            "usage_remaining_seconds": 120,
        }, "sample-instance")
        self.assertFalse(report["headroom_for_one_300_second_job"])
        self.assertEqual(report["maximum_possible_job_limit_seconds"], 120)

    def test_paid_or_missing_limits_fail_closed(self):
        for case in [
            {"usage_limit_seconds": 9999, "usage_consumed_seconds": 0, "usage_remaining_seconds": 9999},
            {"usage_limit_seconds": 600, "usage_consumed_seconds": 0},
            {"usage_limit_seconds": 600, "usage_consumed_seconds": 20, "usage_remaining_seconds": 800},
            {"usage_limit_seconds": 600, "usage_consumed_seconds": 0, "usage_remaining_seconds": float("nan")},
            {"usage_limit_seconds": 600, "usage_consumed_seconds": 0, "usage_remaining_seconds": 100,
             "usage_limit_reached": True},
        ]:
            with self.subTest(case=case), self.assertRaises(ValueError):
                mod.quota_receipt(case, "sample-instance")


if __name__ == "__main__":
    unittest.main()
