from __future__ import annotations

import importlib.util
import json
import platform
import sqlite3
import sys
import urllib.request
from pathlib import Path


def run_doctor(ollama_url: str = "http://127.0.0.1:11434") -> dict[str, object]:
    checks: dict[str, object] = {
        "python": sys.version.split()[0],
        "python_supported": sys.version_info >= (3, 10),
        "platform": platform.platform(),
        "sqlite": sqlite3.sqlite_version,
        "qiskit_available": importlib.util.find_spec("qiskit") is not None,
        "qiskit_ibm_runtime_available": importlib.util.find_spec("qiskit_ibm_runtime") is not None,
        "torch_available": importlib.util.find_spec("torch") is not None,
        "huggingface_hub_available": importlib.util.find_spec("huggingface_hub") is not None,
    }
    try:
        with urllib.request.urlopen(ollama_url.rstrip("/") + "/api/tags", timeout=1.0) as r:
            data = json.loads(r.read().decode("utf-8"))
            checks["ollama_local"] = True
            checks["ollama_models"] = [x.get("name") for x in data.get("models", [])][:10]
    except Exception:
        checks["ollama_local"] = False
    checks["cwd_writable"] = Path(".").exists()
    return checks
