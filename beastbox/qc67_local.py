"""Owner-authenticated exact-checkpoint choices for published QC67 local sidecar.

No runtime downloads, no aliases to other weights, no remote inference.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.request

from beastbox.providers import _local_opener

URL = "http://127.0.0.1:8771/v1"
PINS = {
    "qc67-phos": "bdcd4a39aa54bfc6c274580e210f993e528214d7207cb19dc258a2f801f6b84d",
    "qc67-samgo": "871c265c062430c77d5528ee5fb9119f7d86668ebd81cfa4951db6a906a92b5a",
}
REVISION = "b414724c627300c41b099dcc6853766d08fd27a4"


def profile(model: str) -> dict:
    if model not in PINS:
        raise ValueError("Unknown original QC67 model")
    return {"kind": "compatible", "model": model, "base_url": URL,
            "allow_remote": False, "api_key_env": "RAWRPHOS_API_KEY"}


def status(model: str) -> dict:
    if model not in PINS:
        raise ValueError("Unknown original QC67 model")
    result = {"choice": model.replace("-", "_"), "model": model,
              "label": ("PHOS — Original 12D Character LM (experimental)"
                        if model == "qc67-phos" else "SAMGO — Original 54D LM (experimental)"),
              "kind": "local", "configured": False, "requires_spend_approval": False,
              "experimental": True, "readiness": "AVAILABLE_NOT_INSTALLED",
              "checkpoint_sha256": PINS[model], "origin": "phera-ra/QC67_cosmo"}
    if os.environ.get("BEASTBOX_QC67_LOCAL_ENABLED") != "yes":
        return result
    root = Path(os.environ.get("QC67_INSTALL_DIR", ""))
    if not os.environ.get("QC67_INSTALL_DIR") or root.is_symlink() or not root.is_dir():
        return result
    key = os.environ.get("RAWRPHOS_API_KEY", "")
    if len(key) < 32 or any(char in key for char in "\r\n"):
        result["readiness"] = "OFFLINE_OR_DISCONNECTED"
        return result
    req = urllib.request.Request("http://127.0.0.1:8771/model/info?model=" + model,
                                 headers={"Authorization": "Bearer " + key})
    try:
        with _local_opener().open(req, timeout=6) as response:
            raw = response.read(16385)
            if response.status != 200 or len(raw) > 16384:
                raise ValueError("Invalid original QC67 identity response")
        info = json.loads(raw)
    except (OSError, ValueError, TypeError):
        result["readiness"] = "OFFLINE_OR_DISCONNECTED"
        return result
    if (not isinstance(info, dict) or info.get("ready") is not True
            or info.get("model_id") != model or info.get("checkpoint_sha256") != PINS[model]
            or info.get("revision") != REVISION
            or info.get("serving_backend") != "pytorch-cpu-original"
            or info.get("model_weights_updated") is not False):
        result["readiness"] = "FAILED_CHECKPOINT_VERIFICATION"
        return result
    result["configured"] = True
    result["readiness"] = "INSTALLED_AND_READY"
    return result
