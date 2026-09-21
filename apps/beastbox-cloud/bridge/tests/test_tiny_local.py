"""Test real durable COSMOS with a local OpenAI-compatible socket and no paid calls."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from beastbox import tiny_local
from beastbox.cosmic_web import CosmicApp


class LocalCompletion(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        value = json.loads(self.rfile.read(length))
        assert value["stream"] is False and value["model"] == tiny_local.MODEL_ID
        assert value["messages"][0]["role"] == "user"
        body = json.dumps({"choices": [{"message": {"content": "TEST_PROVIDER_REAL_SOCKET_REPLY"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class TinyLocalTests(unittest.TestCase):
    def test_default_off_does_not_touch_weight_or_change_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CosmicApp(tmp)
            with patch.dict("os.environ", {"BEASTBOX_TINY_LOCAL_ENABLED": "no"}), \
                 patch.object(tiny_local, "verify_model", side_effect=AssertionError("read")):
                self.assertFalse(tiny_local.configure_tiny_owner_brain(app))
            self.assertEqual(app.profile.kind, "reference")
            self.assertFalse((Path(tmp) / "cosmic-provider.json").exists())

    def test_checksum_failure_is_fail_closed_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CosmicApp(tmp)
            with patch.dict("os.environ", {"BEASTBOX_TINY_LOCAL_ENABLED": "yes"}), \
                 patch.object(tiny_local, "verify_model", side_effect=ValueError("checksum mismatch")):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    tiny_local.configure_tiny_owner_brain(app)
            self.assertEqual(app.profile.kind, "reference")
            self.assertFalse((Path(tmp) / "cosmic-provider.json").exists())

    def test_selected_provider_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CosmicApp(tmp)
            app._set_profile({"kind": "ollama", "model": "owner-selected"})
            with patch.dict("os.environ", {"BEASTBOX_TINY_LOCAL_ENABLED": "yes"}), \
                 patch.object(tiny_local, "verify_model", return_value=tiny_local.MODEL_SHA256):
                with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                    tiny_local.configure_tiny_owner_brain(app)
            self.assertEqual(app.profile.model, "owner-selected")

    def test_real_local_protocol_and_persistent_substrate(self):
        server = HTTPServer(("127.0.0.1", 0), LocalCompletion)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                app = CosmicApp(tmp)
                before = app.dispatch("GET", "/api/orbit")[1]["runtime"]
                code, reference = app.dispatch("POST", "/api/chat", {"text": "Remember blue heron 17"})
                self.assertEqual(code, 200, reference)
                self.assertIn("reference", reference["result"]["response"])
                with patch.dict("os.environ", {"BEASTBOX_TINY_LOCAL_ENABLED": "yes"}), \
                     patch.object(tiny_local, "verify_model", return_value=tiny_local.MODEL_SHA256), \
                     patch.object(tiny_local, "LOCAL_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1"):
                    self.assertTrue(tiny_local.configure_tiny_owner_brain(app))
                    self.assertFalse(app.authority.allowed("cloud"))
                    code, generated = app.dispatch("POST", "/api/chat", {"text": "What do you remember?"})
                self.assertEqual(code, 200, generated)
                self.assertEqual(generated["result"]["response"], "TEST_PROVIDER_REAL_SOCKET_REPLY")
                self.assertEqual(generated["runtime"]["system_id"], before["system_id"])
                self.assertFalse((Path(tmp) / "cosmic-provider.json").exists())
                reopened = CosmicApp(tmp)
                self.assertEqual(reopened.profile.kind, "reference")
                after = reopened.dispatch("GET", "/api/orbit")[1]["runtime"]
                self.assertEqual(after["system_id"], before["system_id"])
                self.assertEqual(after["checkpoint_sha256"], generated["runtime"]["checkpoint_sha256"])
                history = reopened.dispatch("GET", "/api/conversation")[1]["turns"]
                self.assertTrue(any("TEST_PROVIDER_REAL_SOCKET_REPLY" in str(row) for row in history))
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
