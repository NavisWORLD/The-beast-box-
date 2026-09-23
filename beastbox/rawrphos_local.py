"""Pinned RAWRPHØS checkpoint readiness, without downloads or inference."""
import json
import os
from pathlib import Path
import urllib.request

from beastbox.providers import _local_opener

MODEL = "rawrphos-native"
STEP = 12000
SHA = "339fb8e1d6f3950e2aa15a6e33bf8c0f28dd655cefc93b7926fb7545e7e97601"
URL = "http://127.0.0.1:8767/v1"


def profile():
    return {"kind": "compatible", "model": MODEL, "base_url": URL,
            "allow_remote": False, "api_key_env": "RAWRPHOS_API_KEY"}


def status():
    result = {"choice": "rawrphos_native", "model": MODEL,
              "label": "RAWRPHØS Native — Local CPU (12K)", "kind": "local",
              "configured": False, "requires_spend_approval": False,
              "readiness": "AVAILABLE_NOT_INSTALLED", "loaded_step": None}
    path = os.environ.get("RAWRPHOS_CHECKPOINT_PATH", "")
    if not path or not Path(path).exists():
        return result
    directory = Path(path)
    try:
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("unsafe directory")
        m, f = directory / "metadata.json", directory / "manifest.json"
        if m.is_symlink() or f.is_symlink():
            raise ValueError("unsafe metadata")
        if max(m.stat().st_size, f.stat().st_size) > 65536:
            raise ValueError("oversized metadata")
        metadata = json.loads(m.read_text())
        manifest = json.loads(f.read_text())
        if (metadata.get("model_id") != MODEL or metadata.get("lineage") != "native-from-scratch"
                or metadata.get("training_steps") != STEP or metadata.get("checkpoint_sha256") != SHA
                or manifest.get("schema") != "rawrphos-checkpoint-v1"
                or manifest.get("files", {}).get("model.safetensors") != SHA):
            raise ValueError("wrong checkpoint")
    except (OSError, ValueError, TypeError, AttributeError):
        result["readiness"] = "FAILED_CHECKPOINT_VERIFICATION"
        return result
    result["configured"] = True
    try:
        limit = Path("/sys/fs/cgroup/memory.max").read_text().strip()
        if limit.isdigit() and int(limit) - int(Path("/sys/fs/cgroup/memory.current").read_text()) < 512 * 1024 * 1024:
            result["readiness"] = "INSUFFICIENT_RESOURCES"
            return result
    except (OSError, ValueError):
        pass
    key = os.environ.get("RAWRPHOS_API_KEY", "")
    if len(key) < 32:
        result["readiness"] = "OFFLINE_OR_DISCONNECTED"
        return result
    request = urllib.request.Request(URL.removesuffix("/v1") + "/model/info",
                                     headers={"Authorization": "Bearer " + key})
    try:
        with _local_opener().open(request, timeout=5) as response:
            raw = response.read(16385)
            if response.status != 200 or len(raw) > 16384:
                raise ValueError("invalid server response")
        info = json.loads(raw)
    except (OSError, ValueError, TypeError):
        result["readiness"] = "OFFLINE_OR_DISCONNECTED"
        return result
    if (not isinstance(info, dict) or info.get("ready") is not True or info.get("model_id") != MODEL
            or info.get("lineage") != "native-from-scratch" or info.get("training_steps") != STEP
            or info.get("checkpoint_sha256") != SHA or info.get("serving_backend") != "pytorch-cpu"):
        result["readiness"] = "FAILED_CHECKPOINT_VERIFICATION"
        return result
    result.update(readiness="INSTALLED_AND_READY", loaded_step=STEP, checkpoint_sha256=SHA)
    return result
