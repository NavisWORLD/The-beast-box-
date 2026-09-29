"""Protocol tests for the two-model $0 API experiment's bounded host planner.

These are deterministic unit tests of host authority, NOT pretrained model results.
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_protocol():
    path = Path(__file__).resolve().parents[1] / "scripts" / "zero_api_real_models_002.py"
    spec = importlib.util.spec_from_file_location("zero_api_real_models_protocol", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PlannedFixture:
    def __init__(self, decisions: list[str]):
        self.decisions = list(decisions)

    def generate(self, prompt: str) -> str:
        return self.decisions.pop(0)


class AuthorityContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_protocol()

    def test_success_requires_two_model_decisions(self):
        with tempfile.TemporaryDirectory() as root:
            p = PlannedFixture([
                '{"action":"read_note"}',
                '{"action":"write_report","text":"Component cobalt-7 requires inspection."}',
            ])
            outcome = self.module.run_local_agent(p, Path(root))
            self.assertTrue(outcome["task_success"])
            self.assertEqual([x["status"] for x in outcome["trace"]],
                             ["host_approved_read_synthetic_note",
                              "host_approved_write_inside_sandbox"])

    def test_hallucinated_path_is_never_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            p = PlannedFixture(['{"action":"read_note","path":"../../secret"}'])
            outcome = self.module.run_local_agent(p, Path(root))
            self.assertFalse(outcome["task_success"])
            self.assertEqual(outcome["trace"][0]["status"],
                             "rejected_unauthorized_or_wrong_action")

    def test_fabricated_report_without_synthetic_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            p = PlannedFixture([
                '{"action":"read_note"}',
                '{"action":"write_report","text":"No verified component identifier."}',
            ])
            outcome = self.module.run_local_agent(p, Path(root))
            self.assertFalse(outcome["task_success"])
            self.assertEqual(outcome["trace"][1]["status"],
                             "rejected_output_invalid_or_unfaithful")

    def test_unsupported_claim_even_with_keyword_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            p = PlannedFixture([
                '{"action":"read_note"}',
                '{"action":"write_report","text":"The synthetic case cobalt-7 presents an emergency safety hazard."}',
            ])
            outcome = self.module.run_local_agent(p, Path(root))
            self.assertFalse(outcome["task_success"])
            self.assertEqual(outcome["trace"][1]["status"],
                             "rejected_output_invalid_or_unfaithful")

    def test_unsupported_tool_action_cannot_execute(self):
        with tempfile.TemporaryDirectory() as root:
            p = PlannedFixture(['{"action":"shell","command":"echo unsafe"}'])
            outcome = self.module.run_local_agent(p, Path(root))
            self.assertFalse(outcome["task_success"])
            self.assertEqual(outcome["trace"][0]["status"],
                             "rejected_unauthorized_or_wrong_action")


if __name__ == "__main__":
    unittest.main()
