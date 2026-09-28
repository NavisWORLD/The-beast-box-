"""Matched software-state controls for consented numeric sensor input.

Synthetic numerical fixtures only; no wearable, provider, billing, or model calls.
"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from beastbox.bio_inputs import bio_event
from beastbox.cst_sensor_preview import compare_sensor_state

SOURCE = Path(__file__).resolve().parents[1] / "owner_bridge.py"
spec = importlib.util.spec_from_file_location("owner_bridge_cst_preview_tests", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TOKEN = "public-cst-preview-fixture-not-a-real-secret-2026"
AUTH = "Bearer " + TOKEN


class IsolatedCSTPreviewTests(unittest.TestCase):
    def test_isolated_reference_state_has_matched_zero_shuffle_and_frozen_controls(self):
        event = bio_event(readings={"accelerometer_rms_g": 0.75}, source="browser_sensor", consent=True)
        result = compare_sensor_state(event)
        self.assertEqual(result, compare_sensor_state(event))
        self.assertEqual(result["schema"], "cst-software-sensor-preview-v1")
        self.assertEqual(result["present_channels"], ["accelerometer_rms_g"])
        self.assertEqual(set(result["controls"]), {"baseline", "zero_gate", "shuffled"})
        self.assertEqual(len(result["controls"]["baseline"]["dyn12"]), 12)
        self.assertEqual(result["frozen_dyn12"], [0.0] * 12)
        self.assertGreater(result["delta_l2"]["vs_zero_gate"], 0)
        self.assertGreater(result["delta_l2"]["vs_shuffled"], 0)
        self.assertGreater(result["delta_l2"]["vs_frozen"], 0)
        self.assertFalse(result["model_invoked"])
        self.assertFalse(result["persisted"])
        self.assertFalse(result["physical_sensor_attested"])

    def test_missing_channel_payload_or_wrong_event_fails_closed(self):
        event = bio_event(readings={"accelerometer_rms_g": 0.75}, source="browser_sensor", consent=True)
        with self.assertRaises(ValueError):
            compare_sensor_state({**event, "authority": "model"})
        with self.assertRaises(ValueError):
            compare_sensor_state({**event, "features": [0.1] * 11})
        with self.assertRaises(ValueError):
            compare_sensor_state({**event, "features": [float("nan")] * 12})
        with self.assertRaises(ValueError):
            compare_sensor_state({**event, "features": [0.2] * 12})
        with self.assertRaises(ValueError):
            compare_sensor_state({"schema": "sensor-event-v1", "source": "text", "text": "a", "features": []})

    def test_owner_route_needs_both_host_flag_and_separate_request_consent(self):
        request = json.dumps({"action": "cst_preview", "source": "browser_sensor", "consent": True,
                              "compare_confirmed": True, "readings": {"accelerometer_rms_g": 0.75}}).encode()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(os.environ, {"BEASTBOX_BIO_INGEST_ENABLED": "yes",
                                         "BEASTBOX_CST_PREVIEW_ENABLED": "no",
                                         "BEASTBOX_BIO_PERSIST_ENABLED": "no"}):
                host = module.OwnerBridge(root, TOKEN)
                self.assertFalse(host.dispatch("GET", "/api/bio", AUTH)[1]["cst_preview_enabled"])
                self.assertEqual(host.dispatch("POST", "/api/bio", AUTH, request)[0], 503)
            with patch.dict(os.environ, {"BEASTBOX_BIO_INGEST_ENABLED": "yes",
                                         "BEASTBOX_CST_PREVIEW_ENABLED": "yes",
                                         "BEASTBOX_BIO_PERSIST_ENABLED": "no"}):
                host = module.OwnerBridge(root, TOKEN)
                status, original = host.dispatch("GET", "/api/storage", AUTH)
                self.assertEqual(status, 200)
                self.assertTrue(host.dispatch("GET", "/api/bio", AUTH)[1]["cst_preview_enabled"])
                self.assertEqual(host.dispatch("POST", "/api/bio", "", request)[0], 401)
                self.assertEqual(host.dispatch("POST", "/api/bio", AUTH,
                    json.dumps({"action": "cst_preview", "source": "browser_sensor", "consent": True,
                                "readings": {"accelerometer_rms_g": 0.75}}).encode())[0], 400)
                self.assertEqual(host.dispatch("POST", "/api/bio", AUTH,
                    json.dumps({"action": "cst_preview", "source": "browser_sensor", "consent": True,
                                "compare_confirmed": False,
                                "readings": {"accelerometer_rms_g": 0.75}}).encode())[0], 400)
                status, report = host.dispatch("POST", "/api/bio", AUTH, request)
                self.assertEqual(status, 200, report)
                self.assertFalse(report["model_invoked"])
                self.assertFalse(report["persisted"])
                self.assertEqual(report["step"], 1)
                _, after = host.dispatch("GET", "/api/storage", AUTH)
                self.assertEqual(after["checkpoint_sha256"], original["checkpoint_sha256"])
                self.assertEqual(after["memory_digest"], original["memory_digest"])
                self.assertEqual(after["system_id"], original["system_id"])


if __name__ == "__main__":
    unittest.main()
