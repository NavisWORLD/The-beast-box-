"""CI only: no synthetic substitution; test authenticated HTTP serving of real originals."""
from __future__ import annotations

from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import urllib.request
import urllib.error

from models.qc67.install_pinned import install
from models.qc67.inference.server import Handler, OriginalModels


def main():
    with tempfile.TemporaryDirectory(prefix="qc67-real-service-") as root:
        install(Path(root) / "originals")
        engine = OriginalModels(Path(root) / "originals")
        Handler.engine = engine
        Handler.secret = "q" * 32
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:" + str(server.server_address[1])
        try:
            for model in ("qc67-phos", "qc67-samgo"):
                h = {"Authorization": "Bearer " + "q" * 32}
                with urllib.request.urlopen(urllib.request.Request(
                        base + "/model/info?model=" + model, headers=h), timeout=20) as r:
                    info = json.loads(r.read())
                assert info["ready"] is True and info["model_id"] == model
                assert info["model_weights_updated"] is False
                packet = json.dumps({"model": model, "stream": False,
                                     "messages": [{"role": "user", "content": "Hello"}],
                                     "max_tokens": 1, "temperature": 0}).encode()
                req = urllib.request.Request(base + "/v1/chat/completions",
                    data=packet, method="POST", headers={**h, "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    response = json.loads(r.read())
                assert response["model"] == model and response["research"] is True
                assert isinstance(response["choices"][0]["message"]["content"], str)
                assert response["choices"][0]["message"]["content"]
                print("REAL_ORIGINAL_HTTP_INFERENCE_PASS", model, info["checkpoint_sha256"],
                      "one_token", "generated_not_quality_attested", flush=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    main()
