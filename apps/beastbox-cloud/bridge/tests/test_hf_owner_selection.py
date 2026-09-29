"""Public owner HF catalog is separate from credential and model-entitlement checks."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "owner_bridge.py"
SPEC = importlib.util.spec_from_file_location("owner_bridge_hf_tests", SOURCE)
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
TOKEN = "fixture-owner-only-token-0123456789-abcdef"
AUTH = "Bearer " + TOKEN
PUBLIC_MODELS = {"provider": "huggingface", "owner": "phera-ra",
    "models": [
        {"id": "phera-ra/QC67_cosmo", "router_candidate": False},
        {"id": "phera-ra/router-chat", "router_candidate": True},
        {"id": "phera-ra/next-router-chat", "router_candidate": True},
    ],
    "status": "PUBLIC_OWNER_CATALOG_ONLY", "account_access_verified": False,
    "inference_attested": False, "model_invoked": False,
}


class HFSelectionTests(unittest.TestCase):
    def _fixture(self, root):
        app = BRIDGE.OwnerBridge(root, TOKEN)
        app.vault.save("huggingface", {"model": "phera-ra/initial"},
                       "hf_example_test_dummy_key_0123456789")
        return app

    def test_requires_encrypted_owner_credentials_and_separates_research(self):
        env = {BRIDGE.KEY_ENV: base64.b64encode(b"x" * 32).decode(),
               "BEASTBOX_TINY_LOCAL_ENABLED": "no", "BEASTBOX_HF_MODEL_ID": ""}
        with patch.dict(os.environ, env):
            with tempfile.TemporaryDirectory() as directory:
                app = self._fixture(Path(directory))
                with patch.object(BRIDGE, "fetch_owner_models", return_value=PUBLIC_MODELS):
                    self.assertEqual(app.dispatch("GET", "/api/hf-model-inventory", "")[0], 401)
                    status, inventory = app.dispatch("GET", "/api/hf-model-inventory", AUTH)
                    self.assertEqual(status, 200)
                    self.assertFalse(inventory["account_access_verified"])
                    bad = {"choice": "huggingface", "model": "phera-ra/QC67_cosmo",
                           "spend_approved": True}
                    status, result = app.dispatch("POST", "/api/models", AUTH, json.dumps(bad).encode())
                    self.assertEqual(status, 409)
                    self.assertEqual(app.vault.public("huggingface")["config"]["model"],
                                     "phera-ra/initial")
                    not_owner = dict(bad, model="other/foreign")
                    self.assertEqual(app.dispatch("POST", "/api/models", AUTH,
                                                  json.dumps(not_owner).encode())[0], 400)
                    no_approval = dict(bad, model="phera-ra/router-chat", spend_approved=False)
                    self.assertEqual(app.dispatch("POST", "/api/models", AUTH,
                                                  json.dumps(no_approval).encode())[0], 400)
                    desired = dict(bad, model="phera-ra/router-chat")
                    status, selected = app.dispatch("POST", "/api/models", AUTH,
                                                    json.dumps(desired).encode())
                    self.assertEqual(status, 200, selected)
                    self.assertFalse(selected["account_access_verified"])
                    self.assertEqual(app.app.profile.model, desired["model"])
                    self.assertEqual(app.vault.public("huggingface")["config"]["model"],
                                     desired["model"])
                    self.assertNotIn("hf_example_test_dummy_key", str(selected))
                    self.assertEqual(selected["inference"], "NOT_ATTESTED_UNTIL_REAL_CHAT")
                    changed = dict(bad, model="phera-ra/next-router-chat")
                    self.assertEqual(app.dispatch("POST", "/api/models", AUTH,
                                                  json.dumps(changed).encode())[0], 409)

    def test_inventory_failure_leaves_original_model_unchanged(self):
        env = {BRIDGE.KEY_ENV: base64.b64encode(b"x" * 32).decode(),
               "BEASTBOX_TINY_LOCAL_ENABLED": "no", "BEASTBOX_HF_MODEL_ID": ""}
        with patch.dict(os.environ, env):
            with tempfile.TemporaryDirectory() as directory:
                app = self._fixture(Path(directory))
                with patch.object(BRIDGE, "fetch_owner_models",
                                  side_effect=BRIDGE.CatalogUnavailable()):
                    packet = {"choice": "huggingface", "model": "phera-ra/router-chat",
                              "spend_approved": True}
                    code, _ = app.dispatch("POST", "/api/models", AUTH,
                                           json.dumps(packet).encode())
                    self.assertEqual(code, 503)
                    self.assertEqual(app.vault.public("huggingface")["config"]["model"],
                                     "phera-ra/initial")
                    self.assertEqual(app.app.profile.kind, "reference")


if __name__ == "__main__":
    unittest.main()
