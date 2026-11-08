"""Owner sensorium ingress (PR A2).

The bridge admits derived numbers into the A1 store only when the lived
backbone flag is on. It does not call a model or a QPU, and it does not take
a subject id from the request.
"""
import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from beastbox.lived_events import (
    CANONICAL_SUBJECT,
    FACE_BIO_HONESTY,
    FACE_BIO_SCHEMA,
    FACE_BIO_SOURCE,
    MOONWRAITH_SUBJECT,
)

SOURCE = Path(__file__).resolve().parents[1] / "owner_bridge.py"
SPEC = importlib.util.spec_from_file_location("owner_bridge_sensor_ingress", SOURCE)
bridge_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge_module)

TOKEN = "public-fixture-sensorium-token-not-a-real-secret"
AUTH = "Bearer " + TOKEN
NOW = 1_700_000_000_000
ORIGIN = "ab" * 32
PRIOR = "cd" * 32
ON = {
    "BEASTBOX_LIVED_BACKBONE": "on",
    "BEASTBOX_LIVED_ORIGIN_COMMITMENT": ORIGIN,
    "BEASTBOX_LIVED_PRIOR_HEAD": PRIOR,
}


def measured(value, source, quality=1.0):
    return {"label": "MEASURED", "value": value, "status": "present", "source": source, "quality": quality}


def absent(source="none", status="absent"):
    return {"label": "ABSENT", "value": None, "status": status, "source": source, "quality": None}


def face_record(*, present=True, pulse=None):
    return {
        "schema": FACE_BIO_SCHEMA,
        "source": FACE_BIO_SOURCE,
        "heartbeat_label": "ESTIMATE",
        "honesty": FACE_BIO_HONESTY,
        "face": {"present": present, "scale": 0.22 if present else 0.02, "x": 0.05 if present else 0.0, "y": -0.1 if present else 0.0, "blink": 0.3 if present else 0.0},
        "pulse": pulse,
        "raw_audio_published": False,
        "raw_video_published": False,
        "raw_frames_in_packet": False,
    }


def channels(sound=0.2, pulse=None):
    return {
        "brightness": measured(0.42, "camera"),
        "hue": measured(18, "camera"),
        "frame_motion": measured(0.05, "camera"),
        "device_motion": measured(0.1, "device_motion"),
        "sound": measured(sound, "microphone") if sound is not None else absent("none", "denied"),
        "pulse_bpm": measured(pulse, "fingertip_ppg", 0.8) if pulse is not None else absent(),
    }


def sample(seq, face=None, **overrides):
    body = {
        "schema": "sensor-sample-v1",
        "surface_id": "app-shell",
        "session_id": "shell-a2",
        "consent_epoch": overrides.pop("consent_epoch", 1),
        "source_seq": seq,
        "captured_at_ms": NOW,
        "channels": overrides.pop("channels", channels()),
        "face": face,
    }
    body.update(overrides)
    return body


def batch(samples, **extra):
    body = {
        "schema": "sensor-batch-v1",
        "retention_consent": True,
        "nonce": str(samples[0]["source_seq"]) if samples else "0",
        "samples": samples,
    }
    body.update(extra)
    return json.dumps(body).encode()


class LivedSensorIngressTests(unittest.TestCase):
    def dispatch(self, app, method, path, payload=b""):
        with patch.object(bridge_module.time, "time", return_value=NOW / 1000):
            return app.dispatch(method, path, AUTH, payload)

    def test_flag_off_admits_nothing_and_leaves_the_legacy_chain_alone(self):
        env = {"BEASTBOX_LIVED_BACKBONE": "off", "BEASTBOX_LIVED_ORIGIN_COMMITMENT": "", "BEASTBOX_LIVED_PRIOR_HEAD": ""}
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, env, clear=False):
            app = bridge_module.OwnerBridge(Path(td), TOKEN)
            calls = []
            app.app.dispatch = lambda *args, **kwargs: calls.append(args)
            code, body = self.dispatch(app, "POST", "/api/sensorium", batch([sample(1, face_record())]))
            self.assertEqual(code, 200, body)
            self.assertFalse(body["enabled"])
            self.assertFalse(body["admitted"])
            self.assertFalse(body["model_invoked"])
            self.assertFalse(body["qpu_invoked"])
            self.assertEqual(calls, [])
            self.assertFalse((Path(td) / "lived-backbone").exists())

    def test_ordered_samples_commit_without_a_model_and_a_replay_does_not_advance(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, ON, clear=False):
            app = bridge_module.OwnerBridge(Path(td), TOKEN)
            calls = []
            app.app.dispatch = lambda *args, **kwargs: calls.append(args)
            first = [sample(1, face_record()), sample(2, face_record(present=False), channels=channels(sound=None))]
            code, body = self.dispatch(app, "POST", "/api/sensorium", batch(first))
            self.assertEqual(code, 200, body)
            self.assertTrue(body["admitted"])
            self.assertFalse(body["model_invoked"])
            self.assertFalse(body["qpu_invoked"])
            self.assertEqual([item["status"] for item in body["receipts"]], ["admitted", "admitted"])
            self.assertEqual(body["snapshot"]["sequence"], 2)
            self.assertEqual(body["snapshot"]["subject_id"], CANONICAL_SUBJECT)
            self.assertEqual(body["snapshot"]["scope"], "owner")
            self.assertNotIn("origin_commitment", body["snapshot"])
            self.assertNotIn("state12", body["snapshot"])
            self.assertNotIn("channels", body["snapshot"])
            self.assertNotIn("0.42", json.dumps(body))
            self.assertEqual(calls, [])
            store = sqlite3.connect(Path(td) / "lived-backbone" / f"{CANONICAL_SUBJECT}.sqlite")
            try:
                rows = store.execute("SELECT payload FROM lived_events ORDER BY sequence").fetchall()
            finally:
                store.close()
            self.assertEqual(len(rows), 2)
            second = json.loads(rows[1][0])["sample"]
            self.assertFalse(second["face"]["face"]["present"])
            self.assertIsNone(second["channels"]["sound"]["value"])
            self.assertEqual(second["channels"]["sound"]["label"], "ABSENT")
            # Sensor admission never opens the chat runtime, so the legacy
            # continuity file is absent rather than carrying a lived profile.
            runtime_path = Path(td) / "runtime.sqlite3"
            self.assertFalse(runtime_path.exists())
            again_code, again = self.dispatch(app, "POST", "/api/sensorium", batch([sample(1, face_record()), sample(2, face_record(present=False))]))
            self.assertEqual(again_code, 200, again)
            self.assertEqual([item["status"] for item in again["receipts"]], ["duplicate", "duplicate"])
            self.assertEqual(again["snapshot"]["chain_head"], body["snapshot"]["chain_head"])
            self.assertEqual(again["snapshot"]["sequence"], 2)

    def test_request_cannot_choose_a_subject_send_media_or_skip_retention(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, ON, clear=False):
            app = bridge_module.OwnerBridge(Path(td), TOKEN)
            for extra in (
                {"subject_id": MOONWRAITH_SUBJECT},
                {"subject_id": "guest-device-01"},
                {"scope": "guest"},
                {"image": "data:image/png"},
                {"transcript": "hello there"},
                {"feelings": {"joy": 10}},
            ):
                code, body = self.dispatch(app, "POST", "/api/sensorium", batch([sample(1, face_record())], **extra))
                self.assertEqual(code, 400, body)
                self.assertFalse(body["admitted"])
            code, body = self.dispatch(app, "GET", "/api/sensorium?subject=" + MOONWRAITH_SUBJECT)
            self.assertEqual(code, 404, body)
            refused = json.dumps({
                "schema": "sensor-batch-v1",
                "retention_consent": False,
                "nonce": "1",
                "samples": [sample(1, face_record())],
            }).encode()
            code, body = self.dispatch(app, "POST", "/api/sensorium", refused)
            self.assertEqual(code, 400, body)
            self.assertFalse((Path(td) / "lived-backbone").exists())

    def test_camera_pulse_revocation_and_missing_attachment_do_not_invent_a_chain(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, ON, clear=False):
            app = bridge_module.OwnerBridge(Path(td), TOKEN)
            bad = sample(1, face_record())
            bad["channels"]["pulse_bpm"] = measured(72, "camera")
            code, body = self.dispatch(app, "POST", "/api/sensorium", batch([bad]))
            self.assertEqual(code, 422, body)
            self.assertEqual(body["error"], "camera_pulse")
            self.assertFalse(body["model_invoked"])
            ok, admitted = self.dispatch(app, "POST", "/api/sensorium", batch([sample(1, face_record(pulse={"bpm": 72, "sqi": 0.55}))]))
            self.assertEqual(ok, 200, admitted)
            self.assertIsNone(admitted["receipts"][0].get("origin_commitment"))
            feed = json.dumps({
                "schema": "sensor-feed-off-v1",
                "retention_consent": True,
                "session_id": "shell-a2",
                "consent_epoch": 1,
            }).encode()
            code, body = self.dispatch(app, "POST", "/api/sensorium", feed)
            self.assertEqual(code, 200, body)
            self.assertEqual(body["receipts"][0]["kind"], "feed_off")
            code, body = self.dispatch(app, "POST", "/api/sensorium", batch([sample(2, face_record())]))
            self.assertEqual(code, 422, body)
            self.assertEqual(body["error"], "revoked")
        missing = {"BEASTBOX_LIVED_BACKBONE": "on", "BEASTBOX_LIVED_ORIGIN_COMMITMENT": "", "BEASTBOX_LIVED_PRIOR_HEAD": ""}
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, missing, clear=False):
            app = bridge_module.OwnerBridge(Path(td), TOKEN)
            code, body = self.dispatch(app, "POST", "/api/sensorium", batch([sample(1, face_record())]))
            self.assertEqual(code, 503, body)
            self.assertFalse(body["admitted"])
            self.assertNotIn(ORIGIN, json.dumps(body))
            self.assertFalse((Path(td) / "lived-backbone").exists())


if __name__ == "__main__":
    unittest.main()
