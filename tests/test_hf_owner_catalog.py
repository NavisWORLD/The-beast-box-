"""Read-only Hugging Face inventory; no network calls or paid inference."""
import io

import pytest

from beastbox.hf_owner_catalog import CatalogUnavailable, fetch_owner_models


class _Reply(io.BytesIO):
    status = 200


class _Opener:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def open(self, request, timeout):
        assert request.full_url.startswith("https://huggingface.co/api/models?")
        assert "author=phera-ra" in request.full_url
        assert timeout <= 6
        self.calls += 1
        return _Reply(self.payload)


def test_owner_catalog_separates_research_from_routable_candidates():
    opener = _Opener(b'''[
      {"id":"phera-ra/QC67_cosmo","pipeline_tag":"text-generation","library_name":"pytorch"},
      {"id":"phera-ra/rawrphos-chat-candidate","pipeline_tag":"text-generation","library_name":"transformers"},
      {"id":"phera-ra/vision-candidate","pipeline_tag":"image-classification","library_name":"transformers"}
    ]''')
    result = fetch_owner_models(opener=opener)
    rows = {item["id"]: item for item in result["models"]}
    assert len(rows) == 3
    assert rows["phera-ra/QC67_cosmo"]["router_candidate"] is False
    assert rows["phera-ra/vision-candidate"]["router_candidate"] is False
    assert rows["phera-ra/rawrphos-chat-candidate"]["router_candidate"] is True
    assert result["account_access_verified"] is False
    assert result["inference_attested"] is False
    assert result["private_models_included"] is False
    assert opener.calls == 1


@pytest.mark.parametrize("payload", [
    b'{"error": "auth"}',
    b'[{"id": "other-owner/trap"}]',
    b'[{"id": "phera-ra/../../trap"}]',
    b'[1]',
    b"[" + b" " * 321_000 + b"]",
])
def test_owner_catalog_fails_closed_on_untrusted_payload(payload):
    with pytest.raises(CatalogUnavailable):
        fetch_owner_models(opener=_Opener(payload))


def test_duplicate_public_items_never_duplicate_options():
    op = _Opener(b'[{"id":"phera-ra/a"},{"id":"phera-ra/a"}]')
    assert len(fetch_owner_models(opener=op)["models"]) == 1
