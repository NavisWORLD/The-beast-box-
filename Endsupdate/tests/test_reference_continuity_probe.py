"""Fresh-process continuity verifier controls with synthetic receipts only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import verify_reference_continuity as probe


class ReferenceContinuityVerifierTest(unittest.TestCase):
    def _payloads(self):
        before = {"valid": True, "schema": "runtime-inspection-v1", "system_id": "test-id",
                  "sequence": 0, "turn": 0, "checkpoint_sha256": "old", "memory_digest": "old-memory"}
        middle = {"checkpoint": {"system_id": "test-id", "sequence": 1, "sha256": "new"},
                  "model": {"provider": "ReferenceTextProvider", "model": "COSMOS reference"}}
        after = {"valid": True, "schema": "runtime-inspection-v1", "system_id": "test-id",
                 "sequence": 1, "turn": 1, "checkpoint_sha256": "new", "memory_digest": "new-memory"}
        return before, middle, after

    def test_verified_three_process_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "evidence.json"
            with patch.object(probe, "dedicated_data_dir", return_value=Path(temp) / "missing"):
                with patch.object(probe, "_invoke", side_effect=self._payloads()):
                    with patch.object(probe, "OUT", output):
                        doc = probe.run()
            self.assertTrue(all(doc["checks"].values()))
            self.assertEqual(json.loads(output.read_text())["classification"],
                             "FRESH_PROCESS_REFERENCE_ONLY_SOFTWARE_SMOKE")

    def test_model_swap_mislabel_fails_closed(self):
        before, middle, after = self._payloads()
        middle["model"] = {"provider": "LocalOllamaProvider", "model": "some-other-model"}
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(probe, "dedicated_data_dir", return_value=Path(temp) / "missing"):
                with patch.object(probe, "_invoke", side_effect=(before, middle, after)):
                    with patch.object(probe, "OUT", Path(temp) / "evidence.json"):
                        with self.assertRaisesRegex(RuntimeError, "frozen check"):
                            probe.run()

    def test_existing_state_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(probe, "dedicated_data_dir", return_value=Path(temp)):
                with patch.object(probe, "_invoke") as invoke:
                    with self.assertRaisesRegex(ValueError, "new candidate state"):
                        probe.run()
                    invoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
