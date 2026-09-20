"""Encryption, ownership, consent, revocation and non-disclosure in owner BYOK settings.

No external provider is called by these tests. All keys are disposable fixtures.
"""
import base64
import importlib.util
import json
import os
import secrets
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest

from beastbox.cloud_connections import ConnectionVault, ConnectionError, DATABASE, KEY_ENV

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("owner_bridge_cloud_tests",HERE/"owner_bridge.py")
bridge_module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_module)

TOKEN="public-test-bridge-token-is-not-live-2026"
AUTH="Bearer "+TOKEN
HF="public-test-HF-token-DO-NOT-USE"
IBM="public-test-IBM-token-DO-NOT-USE"


class BYOKTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.env=patch.dict(os.environ,{KEY_ENV:base64.b64encode(secrets.token_bytes(32)).decode(),
             "BEASTBOX_HF_MODEL_ID":""},clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_encryption_restart_metadata_and_tampering(self):
        vault=ConnectionVault(self.root)
        public=vault.save("huggingface",{"model":"openai/gpt-oss-120b:cheapest"},HF)
        self.assertNotIn(HF,json.dumps(public))
        self.assertNotIn(HF,json.dumps(vault.list_public()))
        self.assertIn("ENCRYPTED_HOST_ONLY",json.dumps(vault.list_public()))
        self.assertEqual((self.root/DATABASE).stat().st_mode & 0o777,0o600)
        self.assertNotIn(HF.encode(),(self.root/DATABASE).read_bytes())
        restart=ConnectionVault(self.root)
        self.assertEqual(restart.read_host_only("huggingface")["secret"],HF)
        with sqlite3.connect(self.root/DATABASE) as db:
            blob=db.execute("SELECT sealed FROM connections WHERE provider='huggingface'").fetchone()[0]
            db.execute("UPDATE connections SET sealed=? WHERE provider='huggingface'",(blob[:-1]+bytes([blob[-1]^1]),))
            db.commit()
        with self.assertRaisesRegex(ConnectionError,"cannot be authenticated"):
            restart.read_host_only("huggingface")

    def test_reject_unrecognized_and_unscoped_credentials(self):
        vault=ConnectionVault(self.root)
        for name,config,secret in [
            ("example",{"url":"http://127.0.0.1"},"test-token-invalid"),
            ("azure_blob",{"account":"abc","container":"private"},"account-master-key-not-allowed"),
            ("huggingface",{"model":"https://internal.invalid"},"test-token-invalid")]:
            with self.assertRaises(ConnectionError):
                vault.save(name,config,secret)

    def test_owner_bridge_requires_auth_and_spend_approval(self):
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        valid={"action":"save","provider":"huggingface",
             "config":{"model":"openai/gpt-oss-120b:cheapest"},"secret":HF}
        self.assertEqual(bridge.dispatch("POST","/api/connections","",json.dumps(valid).encode())[0],401)
        code,res=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(valid).encode())
        self.assertEqual(code,200,res)
        self.assertNotIn(HF,json.dumps(res))
        code,listed=bridge.dispatch("GET","/api/connections",AUTH)
        self.assertEqual(code,200)
        self.assertNotIn(HF,json.dumps(listed))
        self.assertEqual(bridge.dispatch("POST","/api/connections",AUTH,
            json.dumps({"action":"activate","provider":"huggingface"}).encode())[0],400)
        code,active=bridge.dispatch("POST","/api/connections",AUTH,
            json.dumps({"action":"activate","provider":"huggingface","spend_approved":True}).encode())
        self.assertEqual(code,200,active)
        self.assertEqual(active["inference"],"NOT_ATTESTED_UNTIL_REAL_CHAT")
        self.assertEqual(bridge.app.profile.base_url,"https://router.huggingface.co/v1")
        self.assertEqual(bridge.app._provider().api_key,HF)
        self.assertNotIn(HF,(self.root/"cosmic-provider.json").read_text())
        code,removed=bridge.dispatch("POST","/api/connections",AUTH,
            json.dumps({"action":"remove","provider":"huggingface"}).encode())
        self.assertEqual(code,200,removed)
        self.assertTrue(removed["active_model_deactivated"])
        self.assertEqual(bridge.app.profile.kind,"reference")
        self.assertFalse(bridge.app.authority.allowed("cloud"))
        self.assertNotIn(HF,json.dumps(removed))

    def test_read_only_test_is_explicit_no_network_in_suite(self):
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        saved={"action":"save","provider":"ibm_watsonx",
               "config":{"region":"us-south","project_id":"test_project","model":"ibm/granite-example"},
               "secret":IBM}
        self.assertEqual(bridge.dispatch("POST","/api/connections",AUTH,json.dumps(saved).encode())[0],200)
        with patch.object(bridge_module,"verify_connection",return_value={"provider":"ibm_watsonx","status":"IAM_AUTH_VERIFIED"}) as test_call:
            code,res=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
                {"action":"test","provider":"ibm_watsonx"}).encode())
            self.assertEqual(code,200)
            self.assertEqual(res["status"],"IAM_AUTH_VERIFIED")
            test_call.assert_called_once()
        self.assertNotIn(IBM,json.dumps(res))


if __name__=="__main__":
    unittest.main()
