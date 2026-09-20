"""Offline Azure adapter contract tests. No real Azure Blob account or auth."""
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
import unittest

src=Path(__file__).resolve().parents[1]/"azure_owner_store.py"
spec=importlib.util.spec_from_file_location("azure_owner_store",src)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FakeBlob:
    def __init__(self): self.content=b"";self.metadata={};self.deleted=False
    def upload_blob(self, source, *, overwrite, content_settings, metadata, max_concurrency):
        assert overwrite is False and max_concurrency==1
        self.content=source.read();self.metadata=dict(metadata)
    def get_blob_properties(self):
        if self.deleted: raise FileNotFoundError("deleted")
        return SimpleNamespace(size=len(self.content),metadata=self.metadata)
    def download_blob(self, **kwargs): return SimpleNamespace(readall=lambda:self.content)
    def delete_blob(self): self.deleted=True
class FakeContainer:
    def __init__(self): self.objects={}
    def get_blob_client(self,key): return self.objects.setdefault(key,FakeBlob())
class FakeService:
    def __init__(self): self.container=FakeContainer()
    def get_container_client(self,name):
        assert name=="beastbox-private"
        return self.container
class AzureTests(unittest.TestCase):
    def setUp(self):
        self.service=FakeService()
        self.store=module.AzureOwnerStore(account_url="https://beaststorage.blob.core.windows.net",
            container="beastbox-private",owner_id="a"*32,service=self.service)
    def test_genuine_contract_with_fake_backend(self):
        receipt=self.store.upload(filename="letter.txt",mime="text/plain",content=b"hello owner")
        self.assertEqual(receipt["durability"],"AZURE_BLOB_WRITE_ACKNOWLEDGED")
        data,meta=self.store.download(receipt["id"])
        self.assertEqual(data,b"hello owner")
        self.assertEqual(meta["sha256"],receipt["sha256"])
        self.assertEqual(self.store.delete(receipt["id"])["deleted"],receipt["id"])
        with self.assertRaises(FileNotFoundError): self.store.download(receipt["id"])
    def test_reject_invalid_inputs_and_owner_tamper(self):
        for name in ["../bad.txt","bad.pdf","bad\\path.txt"]:
            with self.assertRaises(module.OwnerStorageError):
                self.store.upload(filename=name,mime="text/plain",content=b"hello")
        with self.assertRaises(module.OwnerStorageError):
            self.store.upload(filename="fake.pdf",mime="application/pdf",content=b"not PDF")
        with self.assertRaises(module.OwnerStorageError):
            module.AzureOwnerStore(account_url="http://127.0.0.1",container="beastbox-private",owner_id="a"*32,service=self.service)
        receipt=self.store.upload(filename="safe.txt",mime="text/plain",content=b"owner")
        blob=self.service.container.get_blob_client(self.store.prefix+receipt["id"])
        blob.metadata["owner"]="b"*32
        with self.assertRaises(module.OwnerStorageError): self.store.download(receipt["id"])
        with self.assertRaises(module.OwnerStorageError): self.store.delete(receipt["id"])
    def test_detect_object_corruption(self):
        r=self.store.upload(filename="one.txt",mime="text/plain",content=b"one")
        blob=self.service.container.get_blob_client(self.store.prefix+r["id"])
        blob.content=b"two"
        with self.assertRaises(module.OwnerStorageError):self.store.download(r["id"])

if __name__=="__main__": unittest.main()
