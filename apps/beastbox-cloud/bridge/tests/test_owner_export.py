"""Owner-substrate export tests. Never assert a GGUF, pretrained model or cloud deployment."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

BRIDGE=Path(__file__).resolve().parents[1]
def load(name: str):
    spec=importlib.util.spec_from_file_location(name,BRIDGE/(name+".py"))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

bridge=load("owner_bridge")
export=load("export_bundle")
TOKEN="public-fixture-token-not-valid-outside-ci-2026"

class OwnerArchiveTests(unittest.TestCase):
    def test_real_substrate_export_verify_restore_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            root=base/"owner"
            root.mkdir()
            app=bridge.OwnerBridge(root,TOKEN)
            prompt="The owner-retained blue notebook is deliberately imaginary"
            status,response=app.dispatch("POST","/api/chat","Bearer "+TOKEN,json.dumps({"text":prompt}).encode())
            self.assertEqual(status,200,response)
            archive=base/"owned-universe.zip"
            result=export.export_archive(root,archive)
            self.assertTrue(archive.is_file())
            self.assertEqual(result["gguf"],"NOT_INCLUDED")
            self.assertEqual(result["authority"],"NOT_TRANSFERRED")
            self.assertEqual(result["model_weights"],"NOT_INCLUDED")
            self.assertEqual(result["archive_sha256"],export.sha256(archive))
            self.assertEqual(export.verify_archive(archive,result["manifest_sha256"])["checkpoint_sha256"],result["checkpoint_sha256"])
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(set(z.namelist()),{"manifest.json","runtime.sqlite3"})
            restored=base/"restored"
            receipt=export.restore_archive(archive,restored,result["manifest_sha256"])
            self.assertTrue(receipt["restored"])
            self.assertEqual(receipt["checkpoint_sha256"],result["checkpoint_sha256"])
            original=bridge.OwnerBridge(restored,TOKEN)
            status,history=original.dispatch("GET","/api/conversation","Bearer "+TOKEN)
            self.assertEqual(status,200)
            self.assertTrue(any(prompt in str(x.get("text","")) for x in history["turns"]))
            with self.assertRaisesRegex(ValueError,"new state directory"):
                export.restore_archive(archive,restored,result["manifest_sha256"])
            with self.assertRaisesRegex(ValueError,"new .zip"):
                export.export_archive(root,archive)

    def test_reject_unrecognized_zip_members(self):
        with tempfile.TemporaryDirectory() as td:
            malicious=Path(td)/"bad.zip"
            with zipfile.ZipFile(malicious,"w") as z:
                z.writestr("../credential.env","not really a credential")
            with self.assertRaisesRegex(ValueError,"exactly the permitted"):
                export.verify_archive(malicious,"0"*64)

if __name__=="__main__":
    unittest.main()
