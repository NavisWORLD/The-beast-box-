"""Original QC67 installed choices and local server perimeter without downloading weights."""
from __future__ import annotations

import json
from pathlib import Path
import threading
from http.server import ThreadingHTTPServer
import urllib.error
import urllib.request
from unittest.mock import patch

import pytest

from beastbox import qc67_local
from models.qc67.install_pinned import verify
from models.qc67.inference.server import Handler, MAX_BODY


def test_missing_originals_are_never_faked(tmp_path, monkeypatch):
    monkeypatch.setenv("BEASTBOX_QC67_LOCAL_ENABLED", "no")
    assert qc67_local.status("qc67-phos")["configured"] is False
    assert qc67_local.status("qc67-samgo")["configured"] is False
    monkeypatch.setenv("BEASTBOX_QC67_LOCAL_ENABLED", "yes")
    monkeypatch.setenv("QC67_INSTALL_DIR", str(tmp_path))
    monkeypatch.setenv("RAWRPHOS_API_KEY", "a" * 32)
    assert qc67_local.status("qc67-phos")["readiness"] == "OFFLINE_OR_DISCONNECTED"
    with pytest.raises(ValueError):
        qc67_local.profile("borrowed-model")
    with pytest.raises(RuntimeError):
        verify(tmp_path)


class FakeOriginalModels:
    def status(self, model):
        return {"ready": True, "model_id": model,
                "checkpoint_sha256": qc67_local.PINS[model],
                "revision": qc67_local.REVISION,
                "serving_backend": "pytorch-cpu-original",
                "model_weights_updated": False}
    def generate(self, model, prompt, *, max_tokens):
        return ("test original fixture", True)


def test_bearer_and_model_perimeter():
    Handler.engine = FakeOriginalModels()
    Handler.secret = "x" * 32
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = "http://127.0.0.1:" + str(server.server_address[1])
    try:
        def fetch(path, *, token=True, body=None):
            h = {"Content-Type": "application/json"}
            if token:
                h["Authorization"] = "Bearer " + "x" * 32
            req = urllib.request.Request(url + path, data=body,
                                         method="POST" if body is not None else "GET",
                                         headers=h)
            try:
                with urllib.request.urlopen(req, timeout=3) as response:
                    return response.status, json.loads(response.read())
            except urllib.error.HTTPError as exc:
                return exc.code, json.loads(exc.read())
        assert fetch("/model/info?model=qc67-phos", token=False)[0] == 401
        assert fetch("/model/info?model=qc67-phos")[1]["checkpoint_sha256"] == qc67_local.PINS["qc67-phos"]
        assert fetch("/model/info?model=borrowed")[0] == 404
        good = {"model": "qc67-phos", "stream": False,
                "messages": [{"role": "user", "content": "hello"}], "max_tokens": 4}
        assert fetch("/v1/chat/completions", body=json.dumps(good).encode())[1]["choices"][0]["message"]["content"] == "test original fixture"
        assert fetch("/v1/chat/completions", body=json.dumps(dict(good, model="other")).encode())[0] == 400
        assert fetch("/v1/chat/completions", body=json.dumps(dict(good, max_tokens=10000)).encode())[0] == 400
        assert fetch("/v1/chat/completions", body=b"x" * (MAX_BODY + 1))[0] == 413
        assert fetch("/v1/chat/completions", token=False, body=json.dumps(good).encode())[0] == 401
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
