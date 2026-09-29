"""COSMIC.CYPHER can use exactly the two authenticated local original models."""
import json
from unittest.mock import patch
import pytest

from beastbox.cypher.models import ModelSpec, create_model


class Reply:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return None
    def read(self, size=-1):
        return json.dumps({"choices": [{"message": {"content": "fixture original output"}}]}).encode()


def test_local_cypher_secret_only_reaches_original_loopback(monkeypatch):
    monkeypatch.setenv("RAWRPHOS_API_KEY", "s" * 32)
    model = create_model(ModelSpec(alias="phos", backend="qc67-original", model="qc67-phos"))
    calls = []
    class Opener:
        def open(self, req, timeout):
            calls.append((req.full_url, req.get_header("Authorization"), json.loads(req.data)))
            return Reply()
    with patch("beastbox.cypher.models._local_opener", return_value=Opener()):
        assert model.complete("hello") == "fixture original output"
    assert calls[0][0] == "http://127.0.0.1:8771/v1/chat/completions"
    assert calls[0][1] == "Bearer " + "s" * 32
    assert calls[0][2]["model"] == "qc67-phos"
    assert calls[0][2]["max_tokens"] <= 24


def test_secret_never_sent_to_other_hosts_and_models(monkeypatch):
    monkeypatch.setenv("RAWRPHOS_API_KEY", "s" * 32)
    for url in ("http://127.0.0.1:8772/v1", "https://other.example/v1",
                "http://localhost:8771/v1"):
        with pytest.raises(ValueError):
            create_model(ModelSpec(alias="bad", backend="qc67-original",
                                   model="qc67-samgo", base_url=url))
    with pytest.raises(ValueError):
        create_model(ModelSpec(alias="fake", backend="qc67-original", model="borrowed"))
    monkeypatch.delenv("RAWRPHOS_API_KEY")
    with pytest.raises(ValueError, match="invalid host-only"):
        create_model(ModelSpec(alias="samgo", backend="qc67-original",
                               model="qc67-samgo")).complete("hello")
