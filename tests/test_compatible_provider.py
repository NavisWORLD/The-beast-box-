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


def test_cloud_gpt_oss_uses_bounded_low_reasoning_and_no_automatic_retry(monkeypatch):
    requests = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, _):
            return b'{"choices":[{"message":{"content":"Confirmed fixture"}}]}'

    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            return Response()

    monkeypatch.setattr(providers, "_local_opener", Opener)
    provider = providers.CompatibleChatProvider("gpt-oss:120b", "https://ollama.com/v1",
                                                 allow_remote=True, api_key="public-fixture-not-a-token")
    assert provider.generate("Synthetic test message") == "Confirmed fixture"
    assert len(requests) == 1
    payload = json.loads(requests[0].data)
    assert payload["model"] == "gpt-oss:120b"
    assert payload["max_tokens"] == 256
    assert payload["reasoning_effort"] == "low"
    assert payload["stream"] is False
    assert requests[0].full_url == "https://ollama.com/v1/chat/completions"
    assert "public-fixture-not-a-token" not in json.dumps(payload)


@pytest.mark.parametrize("http_status,expected", [
    (401, "MODEL_AUTH_REJECTED"), (403, "MODEL_ACCESS_DENIED"),
    (404, "MODEL_NOT_FOUND"), (408, "MODEL_TIMEOUT"),
    (429, "MODEL_RATE_LIMITED"), (502, "MODEL_UNAVAILABLE"),
])
def test_provider_http_failure_is_bounded_and_no_response_body_is_read(monkeypatch, http_status, expected):
    from urllib.error import HTTPError

    class Opener:
        def open(self, *_args, **_kwargs):
            raise HTTPError(
                "https://ollama.com/v1/chat/completions", http_status,
                "upstream-hidden-secret", {"Private": "upstream-hidden-secret"}, None
            )

    monkeypatch.setattr(providers, "_local_opener", Opener)
    model = providers.CompatibleChatProvider("gpt-oss:120b", "https://ollama.com/v1",
                                             allow_remote=True, api_key="secret-fixture-not-live")
    with pytest.raises(providers.ProviderDiagnosticError) as caught:
        model.generate("Synthetic input must remain private")
    assert caught.value.code == expected
    assert "upstream-hidden-secret" not in str(caught.value)
    assert "secret-fixture-not-live" not in str(caught.value)
    assert "Synthetic input" not in str(caught.value)


def test_gpt_oss_reasoning_only_output_fails_closed_without_invented_answer(monkeypatch):
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, _):
            return b'{"choices":[{"finish_reason":"length","message":{"content":null,"reasoning":"private reasoning"}}]}'
    class Opener:
        def open(self, *_args, **_kwargs):
            return Response()
    monkeypatch.setattr(providers, "_local_opener", Opener)
    model = providers.CompatibleChatProvider("gpt-oss:120b", "https://ollama.com/v1",
                                             allow_remote=True, api_key="public-fixture-not-live")
    with pytest.raises(providers.ProviderDiagnosticError) as caught:
        model.generate("A fixture")
    assert caught.value.code == "MODEL_OUTPUT_EMPTY"
    assert "private reasoning" not in str(caught.value)

def test_cli_tag_does_not_use_direct_api_reasoning_override(monkeypatch):
    requests = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, _): return b'{"choices":[{"message":{"content":"Fixture"}}]}'
    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            return Response()
    monkeypatch.setattr(providers, "_local_opener", Opener)
    model = providers.CompatibleChatProvider("gpt-oss:120b-cloud", "https://ollama.com/v1",
                                            allow_remote=True, api_key="synthetic-do-not-use")
    model.generate("fixture")
    assert "reasoning_effort" not in json.loads(requests[0].data)



def test_native_local_cpu_uses_bounded_64_token_reply_without_changing_other_models(monkeypatch):
    requests = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, _): return b'{"choices":[{"message":{"content":"Hello!"}}]}'

    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            return Response()

    monkeypatch.setattr(providers, "_local_opener", Opener)
    native = providers.CompatibleChatProvider(
        "rawrphos-native", "http://127.0.0.1:8767/v1",
        allow_remote=False, api_key="synthetic-native-key"
    )
    assert native.generate("synthetic bounded owner prompt") == "Hello!"
    payload = json.loads(requests[-1].data)
    assert payload["max_tokens"] == 64 and payload["model"] == "rawrphos-native"
    assert "synthetic-native-key" not in json.dumps(payload)
    research = providers.CompatibleChatProvider(
        "rawrphos-native", "http://127.0.0.1:8768/v1",
        allow_remote=False, api_key="synthetic-experimental-key"
    )
    assert research.generate("synthetic owner-only 18K prompt") == "Hello!"
    assert json.loads(requests[-1].data)["max_tokens"] == 64
    assert requests[-1].full_url == "http://127.0.0.1:8768/v1/chat/completions"
    alternate = providers.CompatibleChatProvider("SmolLM2-135M-Instruct-Q4_K_M", "http://127.0.0.1:11522/v1")
    assert alternate.generate("synthetic SmolLM input") == "Hello!"
    assert json.loads(requests[-1].data)["max_tokens"] == 256
