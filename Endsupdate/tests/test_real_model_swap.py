"""Frozen controls for the independent real-model comparison and its claim boundary."""
import copy
import unittest

from run_real_model_swap import ID, compare_result


def fixture():
    cases = {f"case-{i}": 0.25 * i for i in range(6)}
    identity = {"world_db_sha256": "frozen", "model_a_checkpoint_sha256": "frozen"}
    measurements = {s: {"deltas": dict(cases)} for s in ("A0", "B1", "A2")}
    life = [
        {"stage": "A0", "parameter_sha256_before": "a", "parameter_sha256_after": "a", "parameter_drift": False},
        {"stage": "B1", "parameter_sha256_before": "b", "parameter_sha256_after": "b", "parameter_drift": False},
        {"stage": "A2", "parameter_sha256_before": "a", "parameter_sha256_after": "a", "parameter_drift": False},
    ]
    gates = {
        key: True for key in (
            "requested_model_order_executed", "same_primary_substrate_identity",
            "b1_received_verified_pre_swap_memory", "a2_received_verified_b1_memory",
            "a_only_schedule_executed", "empty_memory_control_executed",
            "empty_memory_is_zero_records", "shuffled_memory_control_executed",
            "all_model_parameters_frozen",
        )
    }
    baseline = {
        "classification": "COMPLETED_DESCRIPTIVE_MEASUREMENT",
        "experiment_id": "persistent-substrate-model-swap-002-historical-b4e53",
        "model_b_revision": "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915",
        "input_identity": identity,
        "primary": {"measurements": measurements, "model_lifecycle": life},
        "paired_metrics": {"a0_a2_restoration_error": {k: 0.0 for k in cases}},
        "structural_gates": gates,
    }
    candidate = copy.deepcopy(baseline)
    candidate["experiment_id"] = ID
    return candidate, baseline


class ABAEvaluationTest(unittest.TestCase):
    def test_frozen_structural_success_does_not_claim_better(self):
        candidate, baseline = fixture()
        report = compare_result(candidate, baseline)
        self.assertTrue(report["model_a_parameters_restored"])
        self.assertEqual(report["model_performance_advantage"],
                         "NOT_EVALUABLE_UNTIL_MATCHED_CORRECTED_CST_RUNTIME_ARM_EXISTS")
        self.assertEqual(report["stage_comparison"]["A0"]["case_delta_candidate_minus_historical"]["case-1"], 0)

    def test_missing_or_failed_gate_is_never_pass(self):
        candidate, baseline = fixture()
        candidate["structural_gates"]["empty_memory_is_zero_records"] = False
        with self.assertRaisesRegex(RuntimeError, "structural"):
            compare_result(candidate, baseline)
        candidate, baseline = fixture()
        del candidate["structural_gates"]["a2_received_verified_b1_memory"]
        with self.assertRaisesRegex(RuntimeError, "structural"):
            compare_result(candidate, baseline)

    def test_frozen_input_and_model_identity_fail_closed(self):
        candidate, baseline = fixture()
        candidate["input_identity"]["world_db_sha256"] = "changed"
        with self.assertRaisesRegex(RuntimeError, "provenance"):
            compare_result(candidate, baseline)
        candidate, baseline = fixture()
        candidate["model_b_revision"] = "unfrozen"
        with self.assertRaisesRegex(RuntimeError, "revision"):
            compare_result(candidate, baseline)

    def test_unrestored_a_or_score_fails(self):
        candidate, baseline = fixture()
        candidate["paired_metrics"]["a0_a2_restoration_error"]["case-1"] = 0.1
        with self.assertRaisesRegex(RuntimeError, "restoration"):
            compare_result(candidate, baseline)
        candidate, baseline = fixture()
        candidate["primary"]["model_lifecycle"][2]["parameter_sha256_after"] = "changed"
        with self.assertRaisesRegex(RuntimeError, "weights"):
            compare_result(candidate, baseline)


if __name__ == "__main__":
    unittest.main()
