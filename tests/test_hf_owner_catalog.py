"""Owner Hugging Face catalog: no arbitrary provider URLs or inferred model readiness."""
import json

import pytest

from beastbox.hf_owner_catalog import API, CatalogUnavailable, list_owner_models


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _):
        return self.payload


class Opener:
    def __init__(self, payload):
        self.payload = payload
        self.headers = None
        self.url = None

    def open(self, request, timeout):
        self.url = request.full_url
        self.headers = dict(request.header_items())
        assert 0 < timeout <= 7
        return Response(self.payload)


def test_catalog_includes_own_models_and_separates_historical_checkpoints():
    opener = Opener(json.dumps([
        {"id": "phera-ra/QC67_cosmo", "pipeline_tag": "text-generation"},
        {"id": "phera-ra/my-chat", "pipeline_tag": "text-generation", "private": True},
        {"id": "phera-ra/my-vision", "pipeline_tag": "image-classification"},
        {"id": "another-user/other", "pipeline_tag": "text-generation"},
    ]).encode())
    result = list_owner_models("private-test-token", opener=opener)
    assert opener.url == API
    assert opener.headers["Authorization"] == "Bearer private-test-token"
    models = {m["id"]: m for m in result["models"]}
    assert set(models) == {"phera-ra/QC67_cosmo", "phera-ra/my-chat", "phera-ra/my-vision"}
    assert not models["phera-ra/QC67_cosmo"]["selectable"]
    assert models["phera-ra/my-chat"]["selectable"]
    assert models["phera-ra/my-chat"]["private"]
    assert not models["phera-ra/my-vision"]["selectable"]
    assert {r["name"] for r in result["research_artifacts"]} == {
        "PHOS / dyn12", "SAMGO / 54D", "COSMIC.CYPHER"
    }
    assert result["model_invoked"] is False
    assert "private-test-token" not in json.dumps(result)


@pytest.mark.parametrize("bad", ["key\nEXTRA", "key\rEXTRA", "key\x00EXTRA", "x" * 4097])
def test_no_untrusted_credential_headers(bad):
    with pytest.raises(CatalogUnavailable, match="CREDENTIAL_INVALID"):
        list_owner_models(bad, opener=Opener(b"[]"))


def test_bounded_catalog_response_and_rejects_bad_shape():
    with pytest.raises(CatalogUnavailable, match="TOO_LARGE"):
        list_owner_models(opener=Opener(b" " * (1024 * 1024 + 1)))
    with pytest.raises(CatalogUnavailable, match="INVALID"):
        list_owner_models(opener=Opener(b'{"models": []}'))
