"""Bio consent/retention and normalized CST event tests (invented fixtures only)."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from beastbox.bio_inputs import BOUNDS, CHANNELS, bio_event
from beastbox.events import normalize_event

SOURCE = Path(__file__).resolve().parents[1] / "owner_bridge.py"
spec = importlib.util.spec_from_file_location("owner_bridge_bio_tests", SOURCE)
bridge_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_module)
TOKEN = "public-fixture-bio-token-not-a-real-secret-2026"
AUTH = "Bearer " + TOKEN
MEASUREMENT = {"heart_rate_bpm": 80, "hrv_rmssd_ms": 45, "eeg_alpha_relative": .2}


def body(action="preview", **extras):
    return json.dumps({"action": action, "source": "manual", "consent": True,
                       "readings": MEASUREMENT, **extras}).encode()


class BioInputsTests(unittest.TestCase):
    def test_fixed_12d_normalization_and_explicit_missing_channels(self):
        e = bio_event(readings=MEASUREMENT, source="manual", consent=True)
        self.assertEqual(normalize_event(e)["schema"], "normalized-event-v1")
        self.assertEqual(len(e["features"]), 12)
        self.assertEqual(e["features"][3], 0.0)
        metadata = json.loads(e["text"])
        self.assertIn("skin_temperature_c", metadata["missing_channels"])
        self.assertNotIn("readings", metadata)
        self.assertEqual(metadata["provenance"], "USER_SUPPLIED_UNVERIFIED")
        self.assertEqual(e, bio_event(readings=dict(reversed(list(MEASUREMENT.items()))),
                                      source="manual", consent=True))

    def test_rejects_unknown_raw_identifiers_non_finite_and_out_of_range(self):
        for invalid in ({"email": "someone@example.com"}, {"heart_rate_bpm": True},
                        {"heart_rate_bpm": float("nan")}, {"heart_rate_bpm": 500},
                        {"heart_rate_bpm": "80"}, {"heart_rate_bpm": float("inf")}, {}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                bio_event(readings=invalid, source="manual", consent=True)
        for source in ("sensor-serial", "https://device.invalid", ""):
            with self.subTest(source=source), self.assertRaises(ValueError):
                bio_event(readings=MEASUREMENT, source=source, consent=True)
        with self.assertRaises(ValueError):
            bio_event(readings=MEASUREMENT, source="manual", consent=1)
        for name, (lower, upper) in BOUNDS.items():
            with self.subTest(channel=name):
                self.assertEqual(len(bio_event(readings={name: lower}, source="manual",
                                               consent=True)["features"]), len(CHANNELS))
                self.assertEqual(len(bio_event(readings={name: upper}, source="manual",
                                               consent=True)["features"]), len(CHANNELS))

    def test_preview_disabled_and_enabled_without_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(os.environ, {"BEASTBOX_BIO_INGEST_ENABLED": "no",
                                         "BEASTBOX_BIO_PERSIST_ENABLED": "no"}):
                bridge = bridge_module.OwnerBridge(root, TOKEN)
                self.assertEqual(bridge.dispatch("GET", "/api/bio", AUTH)[1]["enabled"], False)
                self.assertEqual(bridge.dispatch("POST", "/api/bio", AUTH, body())[0], 503)
            with patch.dict(os.environ, {"BEASTBOX_BIO_INGEST_ENABLED": "yes",
                                         "BEASTBOX_BIO_PERSIST_ENABLED": "no"}):
                bridge = bridge_module.OwnerBridge(root, TOKEN)
                code, initial = bridge.dispatch("GET", "/api/storage", AUTH)
                self.assertEqual(code, 200)
                self.assertEqual(bridge.dispatch("POST", "/api/bio", "", body())[0], 401)
                code, preview = bridge.dispatch("POST", "/api/bio", AUTH, body())
                self.assertEqual(code, 200)
                self.assertEqual(preview["persisted"], False)
                self.assertEqual(len(preview["event"]["features"]), 12)
                self.assertEqual(bridge.dispatch("POST", "/api/bio", AUTH,
                    body(action="persist", persist_confirmed=True))[0], 403)
                code, after = bridge.dispatch("GET", "/api/storage", AUTH)
                self.assertEqual(code, 200)
                self.assertEqual(after["checkpoint_sha256"], initial["checkpoint_sha256"])
                self.assertEqual(after["memory_digest"], initial["memory_digest"])

    def test_explicit_persist_changes_checkpoint_and_new_instance_recovers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = {"BEASTBOX_BIO_INGEST_ENABLED": "yes",
                   "BEASTBOX_BIO_PERSIST_ENABLED": "yes",
                   "BEASTBOX_BIO_REMOTE_ALLOWED": "no"}
            with patch.dict(os.environ, env):
                first = bridge_module.OwnerBridge(root, TOKEN)
                self.assertEqual(first.dispatch("POST", "/api/bio", AUTH,
                    body(action="persist"))[0], 400)
                self.assertEqual(first.dispatch("POST", "/api/bio", AUTH,
                    body(action="persist", persist_confirmed=False))[0], 403)
                _, old = first.dispatch("GET", "/api/storage", AUTH)
                status, result = first.dispatch("POST", "/api/bio", AUTH,
                    body(action="persist", persist_confirmed=True))
                self.assertEqual(status, 200, result)
                self.assertTrue(result["persisted"])
                _, new = first.dispatch("GET", "/api/storage", AUTH)
                self.assertEqual(new["system_id"], old["system_id"])
                self.assertNotEqual(new["checkpoint_sha256"], old["checkpoint_sha256"])
                second = bridge_module.OwnerBridge(root, TOKEN)
                _, recovered = second.dispatch("GET", "/api/storage", AUTH)
                self.assertEqual(recovered["checkpoint_sha256"], new["checkpoint_sha256"])

    def test_remote_provider_requires_separate_host_and_request_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            env = {"BEASTBOX_BIO_INGEST_ENABLED": "yes",
                   "BEASTBOX_BIO_PERSIST_ENABLED": "yes",
                   "BEASTBOX_BIO_REMOTE_ALLOWED": "no"}
            with patch.dict(os.environ, env):
                first = bridge_module.OwnerBridge(Path(td), TOKEN)
                first.app.profile = first.app.profile.__class__(
                    kind="compatible", model="example", base_url="https://example.org/v1",
                    allow_remote=True)
                status, _ = first.dispatch("POST", "/api/bio", AUTH,
                    body(action="persist", persist_confirmed=True,
                         remote_share_confirmed=True))
                self.assertEqual(status, 403)
                first.bio_remote_allowed = True
                status, _ = first.dispatch("POST", "/api/bio", AUTH,
                    body(action="persist", persist_confirmed=True))
                self.assertEqual(status, 403)
                # No real third-party call is performed.

    def test_unknown_fields_and_non_json_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"BEASTBOX_BIO_INGEST_ENABLED": "yes"}):
                b = bridge_module.OwnerBridge(Path(td), TOKEN)
                self.assertEqual(b.dispatch("POST", "/api/bio", AUTH, b'not json')[0], 400)
                self.assertEqual(b.dispatch("POST", "/api/bio", AUTH, body(serial="private"))[0], 400)
                self.assertEqual(b.dispatch("POST", "/api/bio", AUTH, body(consent=False))[0], 400)


if __name__ == "__main__":
    unittest.main()
