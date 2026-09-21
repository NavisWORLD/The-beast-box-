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
from beastbox.providers import ReferenceTextProvider

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

    def test_owner_corrects_unhosted_ollama_model_without_disclosing_key_or_inference(self):
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        saved={"action":"save","provider":"ollama_cloud",
               "config":{"model":"gpt-oss:120b"},"secret":HF}
        code,_=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(saved).encode())
        self.assertEqual(code,200)
        original=bridge.vault.read_host_only("ollama_cloud")["secret"]
        code,result=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
            {"action":"activate","provider":"ollama_cloud","spend_approved":True}).encode())
        self.assertEqual(code,400,result)
        self.assertIn("-cloud",result["error"])
        self.assertEqual(bridge.app.profile.kind,"reference")
        body={"action":"update_model","provider":"ollama_cloud","model":"gpt-oss:120b-cloud"}
        self.assertEqual(bridge.dispatch("POST","/api/connections","",json.dumps(body).encode())[0],401)
        self.assertEqual(bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
            {**body,"secret":HF}).encode())[0],400)
        code,updated=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(body).encode())
        self.assertEqual(code,200,updated)
        self.assertTrue(updated["credential_preserved"])
        self.assertFalse(updated["model_invoked"])
        self.assertNotIn(HF,json.dumps(updated))
        self.assertEqual(bridge.vault.read_host_only("ollama_cloud")["secret"],original)
        self.assertEqual(bridge.vault.public("ollama_cloud")["config"]["model"],"gpt-oss:120b-cloud")
        # No model call, no cloud authority, and no substrate reset after correcting metadata.
        self.assertFalse(bridge.app.authority.allowed("cloud"))
        self.assertEqual(bridge.app.profile.kind,"reference")
        code,activated=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
            {"action":"activate","provider":"ollama_cloud","spend_approved":True}).encode())
        self.assertEqual(code,200,activated)
        self.assertEqual(bridge.app.profile.model,"gpt-oss:120b-cloud")
        code,denied=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
            {**body,"model":"gpt-oss:20b-cloud"}).encode())
        self.assertEqual(code,409,denied)
        self.assertEqual(bridge.vault.read_host_only("ollama_cloud")["secret"],original)
        self.assertEqual(bridge.app.profile.model,"gpt-oss:120b-cloud")

    def test_readonly_model_inventory_detects_wrong_cloud_model_with_zero_inference(self):
        from beastbox.cloud_connection_checks import verify_connection
        from unittest.mock import MagicMock
        record={"config":{"model":"gpt-oss:120b"},"secret":HF}
        class Answer:
            status=200
            def __enter__(self): return self
            def __exit__(self,*_): return False
            def read(self,_): return json.dumps(
                {"data":[{"id":"gpt-oss:120b-cloud"}]}).encode()
        opener=MagicMock()
        opener.open.return_value=Answer()
        bad=verify_connection("ollama_cloud",record,opener=opener)
        self.assertEqual(bad["status"],"MODEL_NOT_LISTED")
        self.assertNotIn(HF,json.dumps(bad))
        request=opener.open.call_args.args[0]
        self.assertEqual(request.full_url,"https://ollama.com/v1/models")
        self.assertEqual(request.get_method(),"GET")
        record["config"]["model"]="gpt-oss:120b-cloud"
        good=verify_connection("ollama_cloud",record,opener=opener)
        self.assertEqual(good["status"],"MODELS_READ_VERIFIED")
        self.assertIn("NOT verified",good["detail"])
        self.assertEqual(opener.open.call_count,2)

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

    def test_hosted_provider_failure_never_falls_back_or_changes_identity(self):
        # Exercise the real CompatibleChatProvider error path with an unavailable
        # transport. This is deliberately NOT evidence of hosted inference.
        for provider,model,endpoint in [
            ("huggingface","openai/gpt-oss-120b:cheapest","https://router.huggingface.co/v1"),
            ("ollama_cloud","gpt-oss:120b-cloud","https://ollama.com/v1"),
        ]:
            with self.subTest(provider=provider):
                root=self.root/provider
                root.mkdir()
                bridge=bridge_module.OwnerBridge(root,TOKEN)
                _,before=bridge.dispatch("GET","/api/orbit",AUTH)
                bridge.vault.save(provider,{"model":model},HF)
                code,active=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
                    {"action":"activate","provider":provider,"spend_approved":True}).encode())
                self.assertEqual(code,200,active)
                self.assertEqual(bridge.app.profile.base_url,endpoint)
                with patch("beastbox.providers._local_opener") as opener, patch.object(
                    ReferenceTextProvider,"generate",side_effect=AssertionError("reference fallback forbidden")
                ) as reference:
                    opener.return_value.open.side_effect=OSError("private upstream detail "+HF)
                    code,result=bridge.dispatch("POST","/api/chat",AUTH,b'{"text":"An unavailable model must fail"}')
                    self.assertEqual(code,400,result)
                    self.assertIn("no fallback",result["error"])
                    self.assertNotIn(HF,json.dumps(result))
                    request=opener.return_value.open.call_args.args[0]
                    self.assertEqual(request.full_url,endpoint+"/chat/completions")
                    self.assertEqual(request.get_header("Authorization"),"Bearer "+HF)
                    reference.assert_not_called()
                self.assertEqual(bridge.app.profile.kind,"compatible")
                _,after=bridge.dispatch("GET","/api/orbit",AUTH)
                self.assertEqual(before["runtime"]["system_id"],after["runtime"]["system_id"])
                _,history=bridge.dispatch("GET","/api/conversation",AUTH)
                self.assertEqual(history["turns"],[])

    def test_sanitized_provider_http_status_is_reported_without_leaking_key(self):
        from urllib.error import HTTPError
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        bridge.vault.save("ollama_cloud",{"model":"gpt-oss:120b-cloud"},HF)
        code,_=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
            {"action":"activate","provider":"ollama_cloud","spend_approved":True}).encode())
        self.assertEqual(code,200)
        with patch("beastbox.providers._local_opener") as network:
            network.return_value.open.side_effect=HTTPError(
                "https://ollama.com/v1/chat/completions",401,
                "private fixture upstream reason",{"Private":"private fixture"},None
            )
            code,result=bridge.dispatch("POST","/api/chat",AUTH,
                                        b'{"text":"Test fixture only"}')
        self.assertEqual(code,502,result)
        self.assertEqual(result["provider_failure"],"MODEL_AUTH_REJECTED")
        self.assertNotIn(HF,json.dumps(result))
        self.assertNotIn("private fixture",json.dumps(result))
        self.assertNotIn("Test fixture only",json.dumps(result))
        self.assertEqual(bridge.app.profile.model,"gpt-oss:120b-cloud")
        self.assertTrue(bridge.app.authority.allowed("cloud"))
        self.assertEqual(bridge.dispatch("GET","/api/conversation",AUTH)[1]["turns"],[])

    def test_byok_restart_preserves_state_but_requires_owner_reactivation(self):
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        # A clearly labeled local reference turn seeds existing substrate state.
        code,seed=bridge.dispatch("POST","/api/chat",AUTH,b'{"text":"Local reference persistence fixture"}')
        self.assertEqual(code,200,seed)
        _,history=bridge.dispatch("GET","/api/conversation",AUTH)
        bridge.vault.save("ollama_cloud",{"model":"gpt-oss:120b-cloud"},HF)
        bridge.app.authority.grant("filesystem")
        activation=json.dumps({"action":"activate","provider":"ollama_cloud","spend_approved":True}).encode()
        code,result=bridge.dispatch("POST","/api/connections",AUTH,activation)
        self.assertEqual(code,200,result)
        self.assertFalse(bridge.app.authority.allowed("filesystem"))
        restarted=bridge_module.OwnerBridge(self.root,TOKEN)
        self.assertEqual(restarted.app.profile,bridge.app.profile)
        self.assertFalse(any(restarted.app.authority.snapshot().values()))
        with patch("beastbox.providers._local_opener") as network:
            code,result=restarted.dispatch("POST","/api/chat",AUTH,b'{"text":"Must explicitly reauthorize"}')
            self.assertEqual(code,403,result)
            network.assert_not_called()
        _,after=restarted.dispatch("GET","/api/orbit",AUTH)
        self.assertEqual(seed["runtime"]["system_id"],after["runtime"]["system_id"])
        self.assertEqual(seed["runtime"]["checkpoint_sha256"],after["runtime"]["checkpoint_sha256"])
        self.assertEqual(restarted.dispatch("GET","/api/conversation",AUTH)[1],history)
        code,result=restarted.dispatch("POST","/api/connections",AUTH,activation)
        self.assertEqual(code,200,result)
        self.assertTrue(restarted.app.authority.allowed("cloud"))
        self.assertFalse(restarted.app.authority.allowed("filesystem"))
        for route in ("authority","workspace","workspace/run","quantum","storage/export"):
            self.assertEqual(restarted.dispatch("POST","/api/"+route,AUTH,b'{}')[0],404)


if __name__=="__main__":
    unittest.main()
