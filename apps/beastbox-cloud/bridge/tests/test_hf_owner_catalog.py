"""Owner-only Hugging Face listing and model handoff, without remote inference."""
import base64
import importlib.util
import json
import os
import secrets
from pathlib import Path
from unittest.mock import patch

from beastbox.cloud_connections import KEY_ENV

SOURCE = Path(__file__).resolve().parents[1] / "owner_bridge.py"
spec = importlib.util.spec_from_file_location("owner_bridge_hf_catalog_tests", SOURCE)
bridge_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_module)
AUTH = "Bearer bounded-test-owner-token-2026-september"


def fixture_catalog(_token):
    return {
        "owner": "phera-ra", "status": "HF_OWNER_REPOSITORY_LIST_ONLY",
        "models": [
            {"id": "phera-ra/demo-chat", "task": "text-generation", "selectable": True},
            {"id": "phera-ra/QC67_cosmo", "task": "text-generation", "selectable": False},
            {"id": "phera-ra/second-chat", "task": "text-generation", "selectable": True},
        ],
        "research_artifacts": [], "inference_attested": False, "model_invoked": False,
    }


def test_owner_only_hf_inventory_and_credentials_preserved(tmp_path):
    env = {KEY_ENV: base64.b64encode(secrets.token_bytes(32)).decode(),
           "BEASTBOX_HF_MODEL_ID": ""}
    with patch.dict(os.environ, env):
        bridge = bridge_module.OwnerBridge(tmp_path, AUTH.removeprefix("Bearer "))
        bridge.vault.save("huggingface", {"model": "phera-ra/old-chat"}, "fixture-private-HF-token")
        with patch.object(bridge_module, "list_owner_models", side_effect=fixture_catalog):
            assert bridge.dispatch("GET", "/api/hf-inventory", "")[0] == 401
            status, inventory = bridge.dispatch("GET", "/api/hf-inventory", AUTH)
            assert status == 200
            assert inventory["models"][0]["id"] == "phera-ra/demo-chat"
            assert "fixture-private-HF-token" not in json.dumps(inventory)
            # A research weight cannot be activated via a generic router.
            attempt = {"choice": "hf_owner_model", "model": "phera-ra/QC67_cosmo",
                       "spend_approved": True}
            assert bridge.dispatch("POST", "/api/models", AUTH, json.dumps(attempt).encode())[0] == 409
            assert bridge.app.profile.kind == "reference"
            # No implicit approval or one-click installation.
            attempt = {"choice": "hf_owner_model", "model": "phera-ra/demo-chat"}
            assert bridge.dispatch("POST", "/api/models", AUTH, json.dumps(attempt).encode())[0] == 400
            attempt["spend_approved"] = True
            status, response = bridge.dispatch("POST", "/api/models", AUTH, json.dumps(attempt).encode())
            assert status == 200, response
            assert response["inventory"] == "OWNER_REPO_LISTED_INFERENCE_UNVERIFIED"
            assert bridge.app.profile.model == "phera-ra/demo-chat"
            assert bridge.vault.read_host_only("huggingface")["secret"] == "fixture-private-HF-token"
            assert bridge.app.authority.allowed("cloud")
            assert "fixture-private-HF-token" not in json.dumps(response)
            # Changing a live HF binding behind an active profile must not
            # strand that model on a mismatched encrypted credential.
            switch_again = {"choice": "hf_owner_model", "model": "phera-ra/second-chat",
                            "spend_approved": True}
            status, refused = bridge.dispatch(
                "POST", "/api/models", AUTH, json.dumps(switch_again).encode())
            assert status == 409 and "Switch to local" in refused["error"]
            assert bridge.vault.read_host_only("huggingface")["config"]["model"] == "phera-ra/demo-chat"
            assert bridge.app.profile.model == "phera-ra/demo-chat"
