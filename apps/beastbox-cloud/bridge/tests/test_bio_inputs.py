"""Offline bio ingestion and real durable COSMOS boundary tests. No real subject/device."""
from __future__ import annotations

import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from beastbox.bio_inputs import SCHEMA, SIGNALS, bio_event
from beastbox.cosmic_web import ProviderProfile
from beastbox.events import normalize_event

SOURCE = Path(__file__).resolve().parents[1] / "owner_bridge.py"
spec = importlib.util.spec_from_file_location("owner_bridge_bio_test", SOURCE)
bridge_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_module)
TOKEN = "public-only-bio-test-token-no-real-authority-2026"
AUTH = "Bearer " + TOKEN


def payload(now: float, **changes) -> dict:
    raw = {
        "source": "manual", "captured_at": now,
        "signals": {"heart_rate_bpm": 72, "movement_index": 0.1},
        "consent": True, "persist": False, "share_remote": False,
    }
    raw.update(changes)
    return raw


class BioInputTests(unittest.TestCase):
    def test_event_is_canonical_bounded_and_descriptive(self):
        event = bio_event("wearable_summary", 1710000000.0,
                          {"heart_rate_bpm": 72, "movement_index": .25},
                          now=1710000000.0)
        parsed = json.loads(event["text"])
        self.assertEqual(parsed["schema"], SCHEMA)
        self.assertEqual(parsed["interpretation"], "RAW_NUMERIC_ONLY")
        self.assertFalse(parsed["medical_interpretation"])
        self.assertEqual(len(event["features"]), len(SIGNALS))
        self.assertTrue(all(-1 <= v <= 1 and math.isfinite(v) for v in event["features"]))
        self.assertEqual(sorted(parsed["measured"]), ["heart_rate_bpm", "movement_index"])
        self.assertEqual(normalize_event(event)["source"], "software-event")

    def test_rejects_stale_or_future_data_and_untrusted_fields(self):
        now = 1710000000.0
        cases = [
            ("manual", now-121, {"heart_rate_bpm": 72}),
            ("manual", now+11, {"heart_rate_bpm": 72}),
            ("manual", now, {"heart_rate_bpm": True}),
            ("manual", now, {"heart_rate_bpm": float("nan")}),
            ("manual", now, {"heart_rate_bpm": 300}),
            ("manual", now, {"patient_id": 1}),
            ("wearable:123", now, {"heart_rate_bpm": 72}),
            ("manual", now, {}),
        ]
        for source, captured, signals in cases:
            with self.subTest(source=source, captured=captured, signals=signals):
                with self.assertRaises(ValueError):
                    bio_event(source, captured, signals, now=now)

    def test_bridge_off_by_default_and_requires_owner_consent(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"BEASTBOX_BIO_ENABLED": "no"}):
                app = bridge_module.OwnerBridge(Path(td), TOKEN)
                self.assertEqual(app.dispatch("GET", "/api/bio", "")[0], 401)
                code, status = app.dispatch("GET", "/api/bio", AUTH)
                self.assertEqual(code, 200)
                self.assertFalse(status["enabled"])
                self.assertFalse(status["default_persistence"])
                self.assertFalse(status["device_capture"])
                self.assertEqual(app.dispatch("POST", "/api/bio", AUTH,
                                              json.dumps(payload(1)).encode())[0], 503)
            with patch.dict(os.environ, {"BEASTBOX_BIO_ENABLED": "yes"}):
                app = bridge_module.OwnerBridge(Path(td), TOKEN)
                body = payload(__import__("time").time(), consent=False)
                self.assertEqual(app.dispatch("POST", "/api/bio", AUTH,
                                              json.dumps(body).encode())[0], 400)
                body["consent"] = True
                body["device_id"] = "must-not-be-accepted"
                self.assertEqual(app.dispatch("POST", "/api/bio", AUTH,
                                              json.dumps(body).encode())[0], 400)

    def test_preview_does_not_mutate_state_and_explicit_persist_does(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"BEASTBOX_BIO_ENABLED": "yes"}):
                app = bridge_module.OwnerBridge(Path(td), TOKEN)
                _, before = app.dispatch("GET", "/api/storage", AUTH)
                body = payload(__import__("time").time())
                code, preview = app.dispatch("POST", "/api/bio", AUTH,
                                             json.dumps(body).encode())
                self.assertEqual(code, 200, preview)
                self.assertEqual(preview["mode"], "VALIDATED_ONLY")
                self.assertFalse(preview["durable_write"])
                self.assertFalse(preview["model_called"])
                _, unchanged = app.dispatch("GET", "/api/storage", AUTH)
                self.assertEqual(unchanged["checkpoint_sha256"], before["checkpoint_sha256"])
                body["persist"] = True
                code, actual = app.dispatch("POST", "/api/bio", AUTH,
                                            json.dumps(body).encode())
                self.assertEqual(code, 200, actual)
                self.assertTrue(actual["durable_write"])
                self.assertFalse(actual["remote_shared"])
                self.assertEqual(actual["result"]["runtime"]["system_id"], before["system_id"])
                self.assertFalse(app.app.authority.allowed("sensors"))
                _, after = app.dispatch("GET", "/api/storage", AUTH)
                self.assertGreater(after["checkpoint_sequence"], before["checkpoint_sequence"])
                self.assertNotEqual(after["checkpoint_sha256"], before["checkpoint_sha256"])
                reopened = bridge_module.OwnerBridge(Path(td), TOKEN)
                _, restored = reopened.dispatch("GET", "/api/storage", AUTH)
                self.assertEqual(restored["checkpoint_sha256"], after["checkpoint_sha256"])
                self.assertEqual(restored["system_id"], before["system_id"])

    def test_remote_provider_requires_separate_sharing_approval(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"BEASTBOX_BIO_ENABLED": "yes"}):
                app = bridge_module.OwnerBridge(Path(td), TOKEN)
                app.app.profile = ProviderProfile.from_dict({
                    "kind": "compatible", "model": "no-network-test",
                    "base_url": "https://example.org/v1", "allow_remote": True,
                })
                _, before = app.dispatch("GET", "/api/storage", AUTH)
                code, denial = app.dispatch("POST", "/api/bio", AUTH, json.dumps(
                    payload(__import__("time").time(), persist=True, share_remote=False)).encode())
                self.assertEqual(code, 403, denial)
                self.assertFalse(app.app.authority.allowed("sensors"))
                _, after = app.dispatch("GET", "/api/storage", AUTH)
                self.assertEqual(before["checkpoint_sha256"], after["checkpoint_sha256"])


if __name__ == "__main__":
    unittest.main()
