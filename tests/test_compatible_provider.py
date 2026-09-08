import json
from urllib.error import URLError

import pytest

from beastbox import providers


def test_remote_requires_explicit_https_permission():
    for url, allowed in [
        ("https://example.com/v1", False),
        ("http://example.com/v1", True),
        ("https://u:p@example.com/v1", True),
    ]:
        with pytest.raises(ValueError):
            providers.CompatibleChatProvider("model", url, allow_remote=allowed)


def test_compatible_auth_not_in_payload_or_repr(monkeypatch):
    monkeypatch.setenv("TEST_MODEL_KEY", "private-test-key")
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return b'{"choices":[{"message":{"content":"SUNFLOWER"}}]}'

    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            return Response()

    monkeypatch.setattr(providers, "_local_opener", Opener)
    provider = providers.CompatibleChatProvider(
        "model", "https://example.com/v1", allow_remote=True, api_key_env="TEST_MODEL_KEY"
    )
    assert provider.generate("history") == "SUNFLOWER"
    assert requests[0].get_header("Authorization") == "Bearer private-test-key"
    assert "private-test-key" not in repr(provider)
    assert "private-test-key" not in json.dumps(json.loads(requests[0].data))


def test_provider_failure_sanitized(monkeypatch):
    class Opener:
        def open(self, *args, **kwargs):
            raise URLError("private-test-key")

    monkeypatch.setattr(providers, "_local_opener", Opener)
    with pytest.raises(ValueError, match="unavailable") as exc:
        providers.CompatibleChatProvider("m").generate("input")
    assert "private-test-key" not in str(exc.value)
