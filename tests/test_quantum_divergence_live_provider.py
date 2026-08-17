from beastbox.quantum_divergence.live_cli import build_seed_provider


class _FakeSeedRuntime:
    class OllamaProvider:
        def __init__(self, model, url):
            self.kind = "ollama"
            self.model = model
            self.url = url

    class OpenAICompatProvider:
        def __init__(self, model, url):
            self.kind = "openai-local"
            self.model = model
            self.url = url


def test_build_seed_provider_can_select_llama_server():
    provider = build_seed_provider(
        _FakeSeedRuntime,
        model="hf.co/phera-ra/QC67_cosmo",
        provider_kind="llama-server",
        provider_url="http://127.0.0.1:8080",
    )
    assert provider.kind == "openai-local"
    assert provider.model == "hf.co/phera-ra/QC67_cosmo"
    assert provider.url == "http://127.0.0.1:8080"


def test_build_seed_provider_rejects_unknown_provider():
    try:
        build_seed_provider(_FakeSeedRuntime, model="m", provider_kind="bad", provider_url="http://127.0.0.1:8080")
    except ValueError as exc:
        assert "provider" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")
