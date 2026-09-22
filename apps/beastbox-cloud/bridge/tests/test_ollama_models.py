"""Offline public model-list tests; network and paid inference are forbidden."""
import json
import unittest
from types import SimpleNamespace

from beastbox.ollama_models import (
    fetch_public_models, ModelInventoryUnavailable, PUBLIC_MODELS_URL,
    MAX_INVENTORY_BYTES,
)


class Response:
    status = 200
    def __init__(self, content):
        self.content = content
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, count):
        assert count == MAX_INVENTORY_BYTES + 1
        return self.content


class Opener:
    def __init__(self, content):
        self.content = content
        self.requests = []
    def open(self, request, timeout):
        self.requests.append(request)
        assert timeout == 6
        return Response(self.content)


class InventoryTests(unittest.TestCase):
    def test_fixed_public_endpoint_no_api_key_and_canonical_ids(self):
        fake = Opener(json.dumps({"object":"list","data":[
            {"id":"gpt-oss:120b"}, {"id":"nemotron-3-ultra"},
            {"id":"gemma4:31b"}, {"id":"gpt-oss:20b"},
            {"id":"gpt-oss:120b"}, {"id":"gpt-oss:120b-cloud"},
            {"id":"bad\nid"}, {"not_id":"malformed"},
        ]}).encode())
        names=fetch_public_models(fake)
        self.assertEqual(names,["gemma4:31b","gpt-oss:120b","gpt-oss:20b","nemotron-3-ultra"])
        self.assertEqual(len(fake.requests),1)
        self.assertEqual(fake.requests[0].full_url,PUBLIC_MODELS_URL)
        self.assertEqual(fake.requests[0].get_method(),"GET")
        self.assertIsNone(fake.requests[0].get_header("Authorization"))
        self.assertNotIn("secret",str(fake.requests[0]))

    def test_fail_closed_on_empty_malformed_oversize_or_network(self):
        for value in (b'{}',b'{"data":[]}',b'{"data":42}',b'not json',
                      b'x'*(MAX_INVENTORY_BYTES+1)):
            with self.subTest(length=len(value)), self.assertRaises(ModelInventoryUnavailable):
                fetch_public_models(Opener(value))
        class FailedOpener:
            def open(self,*_args,**_kwargs):
                raise OSError("PRIVATE_UPSTREAM_URL_OR_KEY")
        with self.assertRaises(ModelInventoryUnavailable) as caught:
            fetch_public_models(FailedOpener())
        self.assertNotIn("PRIVATE_UPSTREAM",str(caught.exception))


if __name__=="__main__":
    unittest.main()
