"""Synthetic owner-only 18K opt-in selection; stable 14K must remain untouched."""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from beastbox import rawrphos_experimental_local as exp

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rawrphos_18k_bridge_test", ROOT / "apps/beastbox-cloud/bridge/owner_bridge.py")
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
TOKEN = "synthetic-exp-owner-" + "x" * 40


def fixture_checkpoint(root):
    path = root / "step-00018000"
    path.mkdir()
    (path / "metadata.json").write_text(json.dumps({
        "model_id": exp.MODEL, "lineage": "native-from-scratch",
        "training_steps": exp.STEP, "checkpoint_sha256": exp.SHA}))
    (path / "manifest.json").write_text(json.dumps({
        "schema": "rawrphos-checkpoint-v1", "files": {"model.safetensors": exp.SHA}}))
    return path


def info(sha=exp.SHA):
    return {"ready": True, "model_id": exp.MODEL, "lineage": "native-from-scratch",
            "training_steps": exp.STEP, "checkpoint_sha256": sha, "serving_backend": "pytorch-cpu"}


class Reply:
    status = 200
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, size): return json.dumps(self.data).encode()[:size]


def test_experimental_opt_in_does_not_change_stable_selection_or_memory(tmp_path):
    path = fixture_checkpoint(tmp_path)
    opener = SimpleNamespace(open=lambda *_a, **_k: Reply(info()))
    env = {"RAWRPHOS_18K_CHECKPOINT_PATH": str(path),
           "RAWRPHOS_API_KEY": "synthetic-private-" + "x" * 32,
           "BEASTBOX_TINY_LOCAL_ENABLED": "no", "BEASTBOX_HF_MODEL_ID": "",
           "BEASTBOX_CONNECTION_VAULT_KEY": ""}
    with patch.dict(os.environ, env), patch("beastbox.rawrphos_experimental_local._local_opener", return_value=opener):
        app = BRIDGE.OwnerBridge(tmp_path / "memory", TOKEN)
        before = app.app.dispatch("GET", "/api/orbit")[1]["runtime"]
        code, catalog = app.dispatch("GET", "/api/models", "Bearer " + TOKEN)
        assert code == 200
        options = {row["choice"]: row for row in catalog["choices"]}
        assert "rawrphos_native" in options
        assert options["rawrphos_native_18k_experimental"]["readiness"] == "INSTALLED_AND_READY"
        assert options["rawrphos_native_18k_experimental"]["experimental"] is True
        assert options["rawrphos_native_18k_experimental"]["promotion_checks_pass"] is False
        assert not catalog["active"]["experimental"] and catalog["active"]["loaded_step"] is None
        code, selected = app.dispatch("POST", "/api/models", "Bearer " + TOKEN,
                                      b'{"choice":"rawrphos_native_18k_experimental"}')
        assert code == 200 and selected["loaded_step"] == 18000
        assert selected["checkpoint_sha256"] == exp.SHA and selected["promotion_checks_pass"] is False
        assert app.app.profile.base_url == "http://127.0.0.1:8768/v1"
        after = app.app.dispatch("GET", "/api/orbit")[1]["runtime"]
        assert before["system_id"] == after["system_id"]
        assert before["checkpoint_sha256"] == after["checkpoint_sha256"]
        code, catalog = app.dispatch("GET", "/api/models", "Bearer " + TOKEN)
        assert code == 200 and catalog["active"]["experimental"] is True and catalog["active"]["loaded_step"] == 18000
        assert BRIDGE.OwnerBridge(tmp_path / "memory", TOKEN).app.profile.base_url == "http://127.0.0.1:8768/v1"


def test_missing_or_wrong_18k_model_is_unavailable_and_does_not_switch(tmp_path):
    path = fixture_checkpoint(tmp_path)
    env = {"RAWRPHOS_18K_CHECKPOINT_PATH": str(path),
           "RAWRPHOS_API_KEY": "synthetic-private-" + "x" * 32,
           "BEASTBOX_TINY_LOCAL_ENABLED": "no", "BEASTBOX_HF_MODEL_ID": "",
           "BEASTBOX_CONNECTION_VAULT_KEY": ""}
    with patch.dict(os.environ, env):
        app = BRIDGE.OwnerBridge(tmp_path / "memory", TOKEN)
        original = app.app.profile
        assert exp.status()["readiness"] == "OFFLINE_OR_DISCONNECTED"
        code, _ = app.dispatch("POST", "/api/models", "Bearer " + TOKEN,
                               b'{"choice":"rawrphos_native_18k_experimental"}')
        assert code == 503 and app.app.profile == original
        (path / "metadata.json").write_text(json.dumps({"model_id": exp.MODEL, "training_steps": 14000}))
        assert exp.status()["readiness"] == "FAILED_CHECKPOINT_VERIFICATION"
        assert app.dispatch("POST", "/api/models", "", b'{"choice":"rawrphos_native_18k_experimental"}')[0] == 401


def test_18k_server_hash_mismatch_rejected(tmp_path):
    path = fixture_checkpoint(tmp_path)
    opener = SimpleNamespace(open=lambda *_a, **_k: Reply(info("0" * 64)))
    with patch.dict(os.environ, {"RAWRPHOS_18K_CHECKPOINT_PATH": str(path),
                                  "RAWRPHOS_API_KEY": "synthetic-private-" + "x" * 32,
                                  "BEASTBOX_TINY_LOCAL_ENABLED": "no",
                                  "BEASTBOX_CONNECTION_VAULT_KEY": ""}), \
            patch("beastbox.rawrphos_experimental_local._local_opener", return_value=opener):
        assert exp.status()["readiness"] == "FAILED_CHECKPOINT_VERIFICATION"
