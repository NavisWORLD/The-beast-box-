"""Native conversational sampling differs from fixed-seed evaluation probes."""
import json

from beastbox import providers


def test_native_owner_chat_uses_expressive_sampling_without_changing_cloud(monkeypatch):
    calls = []

    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, _):
            return b'{"choices":[{"message":{"content":"Hello from the model"}}]}'

    class Opener:
        def open(self, request, timeout):
            calls.append(json.loads(request.data))
            return Response()

    monkeypatch.setattr(providers, "_local_opener", lambda: Opener())
    native = providers.CompatibleChatProvider(
        "rawrphos-native", "http://127.0.0.1:8767/v1"
    )
    assert native.generate("hello") == "Hello from the model"
    assert calls[0]["temperature"] == 0.75
    assert calls[0]["max_tokens"] == 64
    assert calls[0]["stream"] is False
    cloud = providers.CompatibleChatProvider(
        "another-model", "https://example.com/v1", allow_remote=True
    )
    cloud.generate("hello")
    assert calls[1]["temperature"] == 0
    assert calls[1]["max_tokens"] == 256
