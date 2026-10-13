"""Protocol fixtures only: prove the existing driver fails closed before charges."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "apps/beastbox-cloud/scripts/zeref_diary_qvm.py"
spec = importlib.util.spec_from_file_location("private_qvm_bounds_driver", SOURCE)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class PrivateBounds(unittest.TestCase):
    def execute(self, quota, changes=None):
        calls = []
        quil = "DECLARE ro BIT[3]\nMEASURE 0 ro[0]\nMEASURE 1 ro[1]\nMEASURE 2 ro[2]\n"
        plan = {"target": "rigetti.sim.qvm", "shots": 256, "cost_cap_usd": 0,
                "quil": quil, "quil_sha256": hashlib.sha256(quil.encode()).hexdigest(),
                "job_name": "PROTOCOL-FIXTURE", "beast_id": "bb-fixture", "event_id": "fixture-event", "tick": 1}
        plan.update(changes or {})
        class Job:
            id = "PROTOCOL-FIXTURE-ONLY"
            def get_results(self, **kwargs):
                return {"ro": [[0, 0, 0]] * 256}
        class Target:
            name = "rigetti.sim.qvm"
            def submit(self, *args, **kwargs):
                calls.append(kwargs)
                return Job()
        class Workspace:
            @classmethod
            def from_connection_string(cls, value):
                return cls()
            def get_quotas(self):
                return quota
            def get_targets(self, name):
                return Target()
        sdk = types.ModuleType("qdk.azure")
        sdk.Workspace = Workspace
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"AZURE_QUANTUM_CONNECTION_STRING": "PROTOCOL-FIXTURE-NOT-A-CREDENTIAL"}), patch.dict("sys.modules", {"qdk.azure": sdk}):
            source, result = Path(folder) / "plan.json", Path(folder) / "result.json"
            source.write_text(json.dumps(plan))
            driver.main(source, result, private_bounded=True)
            return json.loads(result.read_text()), calls

    def test_missing_or_exhausted_quota_blocks_before_submission(self):
        for quota in [[], [{"dimension": "emulator_hours", "limit": 5, "utilization": 5, "holds": 0}]]:
            receipt, calls = self.execute(quota)
            self.assertFalse(receipt["ok"])
            self.assertIsNone(receipt["job_id"])
            self.assertEqual(calls, [])

    def test_paid_target_excessive_shots_and_changed_circuit_are_rejected(self):
        for change in [{"target": "rigetti.qpu.ankaa-3"}, {"shots": 257}, {"cost_cap_usd": 1}, {"quil_sha256": "0" * 64}]:
            receipt, calls = self.execute([], change)
            self.assertFalse(receipt["ok"])
            self.assertEqual(calls, [])

    def test_permitted_protocol_fixture_records_circuit_and_exact_counts(self):
        receipt, calls = self.execute([{"dimension": "emulator_hours", "limit": 5, "utilization": 0, "holds": 0}])
        self.assertTrue(receipt["ok"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt["counts"], {"000": 256})
        self.assertTrue(receipt["private_execution"])
        self.assertEqual(receipt["event_id"], "fixture-event")
