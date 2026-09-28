"""Offline read-only Azure text retrieval tests. No account, SDK or network used."""
import hashlib
import unittest
from types import SimpleNamespace

from beastbox.azure_read import MAX_CONTEXT_BYTES, AzureReadError, read_owner_text


class FakeBlob:
    def __init__(self, content=b"verified fixture", mime="text/plain", fail=False):
        self.content, self.mime, self.fail = content, mime, fail
        self.property_calls = self.download_calls = 0

    def get_blob_properties(self, **options):
        self.property_calls += 1
        assert options["retry_total"] == 0
        if self.fail:
            raise RuntimeError("SECRET_FAKE_UPSTREAM")
        return SimpleNamespace(size=len(self.content),
                               content_settings=SimpleNamespace(content_type=self.mime))

    def download_blob(self, **options):
        self.download_calls += 1
        assert options["length"] == MAX_CONTEXT_BYTES + 1
        assert options["max_concurrency"] == 1
        assert options["retry_total"] == 0
        return SimpleNamespace(readall=lambda: self.content)


class FakeService:
    def __init__(self, blob):
        self.blob = blob
        self.calls = []

    def get_blob_client(self, **options):
        self.calls.append(options)
        return self.blob


class ReadTests(unittest.TestCase):
    record = {"config": {"account": "fixture", "container": "cosmo",
                         "auth_mode": "account_key"}, "secret": "FAKE-NEVER-REAL"}

    def test_one_explicit_text_read_and_digest_without_persistence(self):
        blob = FakeBlob(b"observed text\n")
        service = FakeService(blob)
        result = read_owner_text(self.record, "observations/latest.txt", service=service)
        self.assertEqual(service.calls, [{"container": "cosmo", "blob": "observations/latest.txt"}])
        self.assertEqual((blob.property_calls, blob.download_calls), (1, 1))
        self.assertEqual(result["sha256"], hashlib.sha256(blob.content).hexdigest())
        self.assertEqual(result["bytes"], len(blob.content))
        self.assertEqual(result["text"], "observed text\n")
        self.assertFalse(result["persisted"])
        self.assertFalse(result["model_invoked"])
        self.assertFalse(result["source_claims_verified"])
        self.assertNotIn(self.record["secret"], str(result))

    def test_invalid_path_never_touches_storage(self):
        for bad in ("../secret.txt", "a/../b.txt", "/root.txt", "a//b.txt",
                    "a?.txt", "a.png", "", "a\\b.txt", "a/."):
            with self.subTest(name=bad):
                service = FakeService(FakeBlob())
                with self.assertRaises(AzureReadError):
                    read_owner_text(self.record, bad, service=service)
                self.assertEqual(service.calls, [])

    def test_rejects_large_binary_bad_utf8_and_network_errors(self):
        for blob in (FakeBlob(b"x" * (MAX_CONTEXT_BYTES + 1)),
                     FakeBlob(b"\xff\xfe"), FakeBlob(b"ok", mime="image/jpeg"),
                     FakeBlob(b"private", fail=True), FakeBlob(b"  \n  ")):
            with self.subTest(blob=blob.mime):
                service = FakeService(blob)
                with self.assertRaises(AzureReadError) as caught:
                    read_owner_text(self.record, "one.txt", service=service)
                self.assertNotIn("SECRET_FAKE_UPSTREAM", str(caught.exception))
                self.assertNotIn("FAKE-NEVER-REAL", str(caught.exception))
                self.assertEqual(blob.property_calls, 1)
                self.assertLessEqual(blob.download_calls, 1)


    def test_azure_sdk_constructor_failure_is_sanitized(self):
        import sys
        from types import ModuleType
        from unittest.mock import patch
        azure=ModuleType("azure")
        storage=ModuleType("azure.storage")
        blob=ModuleType("azure.storage.blob")
        class BrokenClient:
            def __init__(self, **kwargs):
                raise RuntimeError("FAKE_SECRET_IN_SDK_ERROR")
        blob.BlobServiceClient=BrokenClient
        azure.storage=storage
        storage.blob=blob
        modules={m.__name__:m for m in [azure,storage,blob]}
        with patch.dict(sys.modules,modules):
            with self.assertRaises(AzureReadError) as caught:
                read_owner_text(self.record, "one.txt")
        self.assertEqual(str(caught.exception),"Azure document read unavailable or denied")
        self.assertNotIn("FAKE_SECRET_IN_SDK_ERROR",str(caught.exception))



if __name__ == "__main__":
    unittest.main()
