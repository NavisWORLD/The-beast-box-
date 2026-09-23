"""Owner-only RAWRPHØS selection tests (synthetic metadata, not live 12K inference)."""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rawrphos_bridge_test", ROOT / "apps/beastbox-cloud/bridge/owner_bridge.py")
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)
from beastbox import rawrphos_local as native

TOKEN = "synthetic-owner-token-" + "x" * 40


def checkpoint(root):
    path = root / "step-00012000"
    path.mkdir()
    (path / "metadata.json").write_text(json.dumps({
        "model_id": native.MODEL, "lineage": "native-from-scratch",
        "training_steps": native.STEP, "checkpoint_sha256": native.SHA}))
    (path / "manifest.json").write_text(json.dumps({
        "schema": "rawrphos-checkpoint-v1", "files": {"model.safetensors": native.SHA}}))
    return path


def info(sha=native.SHA):
    return {"ready": True, "model_id": native.MODEL, "lineage": "native-from-scratch",
            "training_steps": native.STEP, "checkpoint_sha256": sha,
            "serving_backend": "pytorch-cpu"}


class Reply:
    status = 200
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, size): return json.dumps(self.data).encode()[:size]


def env(path):
    return patch.dict(os.environ, {
        "RAWRPHOS_CHECKPOINT_PATH": str(path), "RAWRPHOS_API_KEY": "synthetic-key-" + "x" * 32,
        "BEASTBOX_TINY_LOCAL_ENABLED": "no", "BEASTBOX_HF_MODEL_ID": "",
        "BEASTBOX_CONNECTION_VAULT_KEY": ""})


def choice(app, name="rawrphos_native"):
    return app.dispatch("POST", "/api/models", "Bearer " + TOKEN, json.dumps({"choice": name}).encode())


def native_choice(app):
    status, data = app.dispatch("GET", "/api/models", "Bearer " + TOKEN)
    assert status == 200
    return next(entry for entry in data["choices"] if entry["choice"] == "rawrphos_native")


def test_native_selector_preserves_durable_state_and_restart(tmp_path):
    path = checkpoint(tmp_path)
    opener = SimpleNamespace(open=lambda *_a, **_k: Reply(info()))
    with env(path), patch("beastbox.rawrphos_local._local_opener", return_value=opener):
        app = BRIDGE.OwnerBridge(tmp_path / "memory", TOKEN)
        before = app.app.dispatch("GET", "/api/orbit")[1]["runtime"]
        assert native_choice(app)["readiness"] == "INSTALLED_AND_READY"
        assert native_choice(app)["loaded_step"] == 12000
        code, result = choice(app)
        assert code == 200 and result["checkpoint_sha256"] == native.SHA
        assert app.app.profile.model == native.MODEL
        assert app.app.authority.allowed("cloud") is False
        after = app.app.dispatch("GET", "/api/orbit")[1]["runtime"]
        assert before["system_id"] == after["system_id"]
        assert before["checkpoint_sha256"] == after["checkpoint_sha256"]
        assert BRIDGE.OwnerBridge(tmp_path / "memory", TOKEN).app.profile.model == native.MODEL


def test_invalid_checkpoint_and_offline_do_not_switch(tmp_path):
    path = checkpoint(tmp_path)
    with env(path):
        app = BRIDGE.OwnerBridge(tmp_path / "memory", TOKEN)
        assert native_choice(app)["readiness"] == "OFFLINE_OR_DISCONNECTED"
        assert choice(app)[0] == 503
        assert app.app.profile.model != native.MODEL
        assert app.dispatch("POST", "/api/models", "", b'{"choice":"rawrphos_native"}')[0] == 401
        assert choice(app, "unknown")[0] == 400
        (path / "metadata.json").write_text(json.dumps({"model_id": native.MODEL, "training_steps": 6000}))
        assert native_choice(app)["readiness"] == "FAILED_CHECKPOINT_VERIFICATION"
        assert choice(app)[0] == 503


def test_server_hash_mismatch_is_rejected(tmp_path):
    path = checkpoint(tmp_path)
    opener = SimpleNamespace(open=lambda *_a, **_k: Reply(info("0" * 64)))
    with env(path), patch("beastbox.rawrphos_local._local_opener", return_value=opener):
        app = BRIDGE.OwnerBridge(tmp_path / "memory", TOKEN)
        assert native_choice(app)["readiness"] == "FAILED_CHECKPOINT_VERIFICATION"
        assert choice(app)[0] == 503
