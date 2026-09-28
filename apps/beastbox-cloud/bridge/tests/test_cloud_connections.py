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

    def test_owner_corrects_cli_only_ollama_model_without_disclosing_key_or_inference(self):
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        saved={"action":"save","provider":"ollama_cloud",
               "config":{"model":"gpt-oss:120b-cloud"},"secret":HF}
        code,_=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(saved).encode())
        self.assertEqual(code,200)
        original=bridge.vault.read_host_only("ollama_cloud")["secret"]
        code,result=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
            {"action":"activate","provider":"ollama_cloud","spend_approved":True}).encode())
        self.assertEqual(code,400,result)
        self.assertIn("without -cloud",result["error"])
        self.assertEqual(bridge.app.profile.kind,"reference")
        body={"action":"update_model","provider":"ollama_cloud","model":"gpt-oss:120b"}
        self.assertEqual(bridge.dispatch("POST","/api/connections","",json.dumps(body).encode())[0],401)
        self.assertEqual(bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
            {**body,"secret":HF}).encode())[0],400)
        code,updated=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(body).encode())
        self.assertEqual(code,200,updated)
        self.assertTrue(updated["credential_preserved"])
        self.assertFalse(updated["model_invoked"])
        self.assertNotIn(HF,json.dumps(updated))
        self.assertEqual(bridge.vault.read_host_only("ollama_cloud")["secret"],original)
        self.assertEqual(bridge.vault.public("ollama_cloud")["config"]["model"],"gpt-oss:120b")
        # No model call, no cloud authority, and no substrate reset after correcting metadata.
        self.assertFalse(bridge.app.authority.allowed("cloud"))
        self.assertEqual(bridge.app.profile.kind,"reference")
        code,activated=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
            {"action":"activate","provider":"ollama_cloud","spend_approved":True}).encode())
        self.assertEqual(code,200,activated)
        self.assertEqual(bridge.app.profile.model,"gpt-oss:120b")
        code,denied=bridge.dispatch("POST","/api/connections",AUTH,json.dumps(
            {**body,"model":"gpt-oss:20b-cloud"}).encode())
        self.assertEqual(code,409,denied)
        self.assertEqual(bridge.vault.read_host_only("ollama_cloud")["secret"],original)
        self.assertEqual(bridge.app.profile.model,"gpt-oss:120b")

    def test_ollama_a_b_a_retains_key_memory_checkpoint_and_is_owner_only(self):
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        code,seed=bridge.dispatch("POST","/api/chat",AUTH,
                                  b'{"text":"Stable substrate sentinel from reference model"}')
        self.assertEqual(code,200,seed)
        _,before=bridge.dispatch("GET","/api/conversation",AUTH)
        _,before_orbit=bridge.dispatch("GET","/api/orbit",AUTH)
        bridge.vault.save("ollama_cloud",{"model":"gpt-oss:120b"},HF)
        self.assertEqual(bridge.dispatch("GET","/api/model-inventory","")[0],401)
        with patch.object(bridge_module,"fetch_public_models",return_value=[
            "gpt-oss:120b","gpt-oss:20b","nemotron-3-ultra"]) as inventory:
            code,listed=bridge.dispatch("GET","/api/model-inventory",AUTH)
            self.assertEqual(code,200)
            self.assertEqual(listed["models"],["gpt-oss:120b","gpt-oss:20b","nemotron-3-ultra"])
            self.assertFalse(listed["account_access_verified"])
            self.assertFalse(listed["inference_attested"])
            self.assertFalse(listed["model_invoked"])
            self.assertNotIn(HF,json.dumps(listed))
            denied={"choice":"ollama_cloud","model":"nemotron-3-ultra"}
            self.assertEqual(bridge.dispatch("POST","/api/models",AUTH,json.dumps(denied).encode())[0],400)
            self.assertEqual(bridge.app.profile.kind,"reference")
            with patch("beastbox.providers._local_opener",
                       side_effect=AssertionError("no paid inference or local model calls")):
                for name in ("gpt-oss:120b","nemotron-3-ultra","gpt-oss:120b"):
                    data={"choice":"ollama_cloud","model":name,"spend_approved":True}
                    status,result=bridge.dispatch("POST","/api/models",AUTH,json.dumps(data).encode())
                    self.assertEqual(status,200,result)
                    self.assertEqual(result["model"],name)
                    self.assertTrue(result["credential_preserved"])
                    self.assertEqual(result["substrate"],"EXISTING_DURABLE_STATE")
                    self.assertEqual(result["inference"],"NOT_ATTESTED_UNTIL_REAL_CHAT")
                    self.assertEqual(bridge.vault.read_host_only("ollama_cloud")["secret"],HF)
                    self.assertEqual(bridge.app.profile.model,name)
                    self.assertTrue(bridge.app.authority.allowed("cloud"))
                    self.assertEqual(bridge.dispatch("GET","/api/conversation",AUTH)[1],before)
                    self.assertEqual(bridge.dispatch("GET","/api/orbit",AUTH)[1]["runtime"]["checkpoint_sha256"],
                                     before_orbit["runtime"]["checkpoint_sha256"])
                invalid={"choice":"ollama_cloud","model":"not-in-public-catalog","spend_approved":True}
                code,failed=bridge.dispatch("POST","/api/models",AUTH,json.dumps(invalid).encode())
                self.assertEqual(code,409,failed)
                self.assertEqual(bridge.app.profile.model,"gpt-oss:120b")
                self.assertEqual(bridge.vault.read_host_only("ollama_cloud")["secret"],HF)
            self.assertGreaterEqual(inventory.call_count,4)
        restarted=bridge_module.OwnerBridge(self.root,TOKEN)
        self.assertEqual(restarted.app.profile.model,"gpt-oss:120b")
        self.assertFalse(restarted.app.authority.allowed("cloud"))
        self.assertEqual(restarted.dispatch("GET","/api/conversation",AUTH)[1],before)
        self.assertEqual(restarted.dispatch("GET","/api/orbit",AUTH)[1]["runtime"]["checkpoint_sha256"],
                         before_orbit["runtime"]["checkpoint_sha256"])

    def test_ollama_catalog_failure_is_fail_closed_without_credential_change(self):
        from beastbox.ollama_models import ModelInventoryUnavailable
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        bridge.vault.save("ollama_cloud",{"model":"gpt-oss:120b"},HF)
        with patch.object(bridge_module,"fetch_public_models",
                          side_effect=ModelInventoryUnavailable("public inventory unavailable")):
            code,result=bridge.dispatch("POST","/api/models",AUTH,json.dumps(
                {"choice":"ollama_cloud","model":"nemotron-3-ultra","spend_approved":True}).encode())
        self.assertEqual(code,503,result)
        self.assertEqual(bridge.vault.read_host_only("ollama_cloud")["config"]["model"],"gpt-oss:120b")
        self.assertEqual(bridge.app.profile.kind,"reference")
        self.assertFalse(bridge.app.authority.allowed("cloud"))
        self.assertNotIn(HF,json.dumps(result))

    def test_readonly_model_inventory_detects_wrong_cloud_model_with_zero_inference(self):
        from beastbox.cloud_connection_checks import verify_connection
        from unittest.mock import MagicMock
        record={"config":{"model":"gpt-oss:120b-cloud"},"secret":HF}
        class Answer:
            status=200
            def __enter__(self): return self
            def __exit__(self,*_): return False
            def read(self,_): return json.dumps(
                {"data":[{"id":"gpt-oss:120b"}]}).encode()
        opener=MagicMock()
        opener.open.return_value=Answer()
        bad=verify_connection("ollama_cloud",record,opener=opener)
        self.assertEqual(bad["status"],"MODEL_ID_MODE_MISMATCH")
        self.assertNotIn(HF,json.dumps(bad))
        request=opener.open.call_args.args[0]
        self.assertEqual(request.full_url,"https://ollama.com/v1/models")
        self.assertEqual(request.get_method(),"GET")
        record["config"]["model"]="gpt-oss:120b"
        good=verify_connection("ollama_cloud",record,opener=opener)
        self.assertEqual(good["status"],"MODEL_LISTED_AUTH_UNVERIFIED")
        self.assertIn("NOT been verified",good["detail"])
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
            ("ollama_cloud","gpt-oss:120b","https://ollama.com/v1"),
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
                    self.assertEqual(code,502,result)
                    self.assertEqual(result["provider_failure"],"MODEL_UNAVAILABLE")
                    self.assertIn("no fallback",result["error"])
                    self.assertNotIn(HF,json.dumps(result))
                    self.assertNotIn("private upstream detail",json.dumps(result))
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
        bridge.vault.save("ollama_cloud",{"model":"gpt-oss:120b"},HF)
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
        self.assertEqual(bridge.app.profile.model,"gpt-oss:120b")
        self.assertTrue(bridge.app.authority.allowed("cloud"))
        self.assertEqual(bridge.dispatch("GET","/api/conversation",AUTH)[1]["turns"],[])

    def test_byok_restart_preserves_state_but_requires_owner_reactivation(self):
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        # A clearly labeled local reference turn seeds existing substrate state.
        code,seed=bridge.dispatch("POST","/api/chat",AUTH,b'{"text":"Local reference persistence fixture"}')
        self.assertEqual(code,200,seed)
        _,history=bridge.dispatch("GET","/api/conversation",AUTH)
        bridge.vault.save("ollama_cloud",{"model":"gpt-oss:120b"},HF)
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


    def test_azure_sas_preflight_is_private_and_does_not_call_network(self):
        from beastbox.cloud_connection_checks import _azure_sas_preflight, verify_connection
        from datetime import datetime, timezone
        base="sv=2024-11-04&sr=c&sp=r&se=2099-01-01T00%3A00%3A00Z&sig=FAKE%2Bsignature"
        now=datetime(2026,9,21,tzinfo=timezone.utc)
        self.assertIsNone(_azure_sas_preflight("?"+base,now))
        for token, expected in [
            (base.replace("sp=r","sp=w"),"SAS_READ_PERMISSION_MISSING"),
            (base.replace("sr=c","sr=b"),"SAS_SCOPE_INVALID"),
            (base.replace("se=2099-01-01T00%3A00%3A00Z","se=2020-01-01T00%3A00%3A00Z"),"SAS_EXPIRED"),
            (base.replace("se=2099-01-01T00%3A00%3A00Z","se=malformed"),"SAS_TIME_INVALID"),
            ("https://account.blob.core.windows.net/c?"+base,"SAS_FORMAT_INVALID"),
            ("SharedAccessSignature="+base,"SAS_FORMAT_INVALID"),
        ]:
            with self.subTest(status=expected):
                self.assertEqual(_azure_sas_preflight(token,now), expected)
                if expected not in ("SAS_EXPIRED", "SAS_NOT_YET_VALID"):
                    with patch("beastbox.cloud_connection_checks._azure_sas_preflight",return_value=expected):
                        value=verify_connection("azure_blob",{"config":{"account":"fixture","container":"private"},"secret":token})
                    self.assertEqual(value["status"],expected)
                    self.assertNotIn(token,json.dumps(value))
                    self.assertNotIn("FAKE+signature",json.dumps(value))
        self.assertEqual(_azure_sas_preflight(
            base+"&st=2099-01-01T00%3A00%3A00Z",now),"SAS_NOT_YET_VALID")

    def test_azure_sdk_failures_are_bounded_and_one_read_only_request(self):
        import sys
        from types import ModuleType
        from beastbox.cloud_connection_checks import verify_connection
        from datetime import datetime, timezone

        azure,core,exceptions,storage,blob=(ModuleType(name) for name in [
            "azure","azure.core","azure.core.exceptions","azure.storage","azure.storage.blob"])
        class FakeHttpResponseError(Exception):
            def __init__(self,code):
                self.status_code=code
                super().__init__("SECRET_PRIVATE_UPSTREAM_DETAIL")
        class FakeClient:
            last=None
            def __init__(self,*,account_url,credential):
                self.account_url,self.credential=account_url,credential
                self.calls=0
                FakeClient.last=self
            def get_container_client(self,name):
                self.container=name
                return self
            def get_container_properties(self,**options):
                self.calls+=1
                self.options=options
                if code:
                    raise FakeHttpResponseError(code)
                return {"ok":True}
        exceptions.HttpResponseError=FakeHttpResponseError
        blob.BlobServiceClient=FakeClient
        azure.core,azure.storage=core,storage
        core.exceptions=exceptions
        storage.blob=blob
        modules={module.__name__:module for module in [azure,core,exceptions,storage,blob]}
        secret="sv=2024-11-04&sr=c&sp=r&se=2099-01-01T00%3A00%3A00Z&sig=FAKE%2Bsignature"
        record={"config":{"account":"fixture","container":"private"},"secret":secret}
        with patch.dict(sys.modules,modules):
            for code,expected in [(0,"CONTAINER_READ_VERIFIED"),(403,"AZURE_PERMISSION_DENIED"),
                                  (404,"AZURE_CONTAINER_NOT_FOUND"),(401,"AZURE_AUTH_REJECTED"),
                                  (429,"AZURE_RATE_LIMITED"),(500,"AZURE_REMOTE_UNAVAILABLE")]:
                with self.subTest(http_code=code):
                    with patch("beastbox.cloud_connection_checks._azure_sas_preflight",return_value=None):
                        result=verify_connection("azure_blob",record)
                    self.assertEqual(result["status"],expected)
                    self.assertEqual(FakeClient.last.calls,1)
                    self.assertEqual(FakeClient.last.container,"private")
                    self.assertEqual(FakeClient.last.account_url,"https://fixture.blob.core.windows.net")
                    self.assertEqual(FakeClient.last.options.get("retry_total"),0)
                    self.assertNotIn(secret,json.dumps(result))
                    self.assertNotIn("SECRET_PRIVATE_UPSTREAM_DETAIL",json.dumps(result))
                    self.assertNotIn("fixture",json.dumps(result))


    def test_account_key_metadata_check_uses_the_selected_mode_without_sas_preflight(self):
        import sys
        from types import ModuleType
        from beastbox.cloud_connection_checks import verify_connection

        azure=ModuleType("azure")
        core=ModuleType("azure.core")
        exceptions=ModuleType("azure.core.exceptions")
        storage=ModuleType("azure.storage")
        blob=ModuleType("azure.storage.blob")
        class FakeHttpResponseError(Exception):
            def __init__(self, status):
                self.status_code=status
                super().__init__("SECRET_UPSTREAM_ERROR")
        calls=[]
        class FakeClient:
            def __init__(self, *, account_url, credential):
                calls.append(("constructor", account_url, credential))
            def get_container_client(self, container):
                calls.append(("container", container))
                return self
            def get_container_properties(self, **kwargs):
                calls.append(("properties", kwargs))
                return {"metadata": "fixture"}
        exceptions.HttpResponseError=FakeHttpResponseError
        blob.BlobServiceClient=FakeClient
        azure.core,azure.storage=core,storage
        core.exceptions=exceptions
        storage.blob=blob
        modules={m.__name__:m for m in [azure,core,exceptions,storage,blob]}
        key=base64.b64encode(b"K"*64).decode("ascii")
        record={"config":{"account":"fixture","container":"cosmo","auth_mode":"account_key"},
                "secret":key}
        with patch.dict(sys.modules,modules):
            with patch("beastbox.cloud_connection_checks._azure_sas_preflight",
                       side_effect=AssertionError("SAS preflight must not run for an account key")):
                response=verify_connection("azure_blob",record)
        self.assertEqual(response["status"],"CONTAINER_READ_VERIFIED")
        self.assertEqual(response["auth_mode"],"account_key")
        self.assertEqual(calls[0],("constructor","https://fixture.blob.core.windows.net",key))
        self.assertEqual(calls[1],("container","cosmo"))
        self.assertEqual(calls[2][0],"properties")
        self.assertEqual(calls[2][1]["retry_total"],0)
        self.assertEqual(len(calls),3)
        self.assertNotIn(key,json.dumps(response))
        self.assertNotIn("SECRET_UPSTREAM_ERROR",json.dumps(response))

    def test_azure_account_key_mode_is_explicit_encrypted_and_legacy_sas_is_preserved(self):
        # A synthetic 64-byte key has the shape of an Azure access key; it is
        # NOT a real credential, and this test never contacts Azure.
        key=base64.b64encode(b"K"*64).decode("ascii")
        vault=ConnectionVault(self.root)
        sas="sv=2024-11-04&sr=c&sp=r&se=2099-01-01T00%3A00%3A00Z&sig=fixture"
        old=vault.save("azure_blob",{"account":"teststore","container":"private"},sas)
        self.assertEqual(old["config"]["auth_mode"],"container_sas")
        self.assertNotIn(sas,json.dumps(old))
        self.assertEqual(ConnectionVault(self.root).read_host_only("azure_blob")["secret"],sas)
        for wrong in ("nonsense","AccountKey="+key,"https://teststore.blob.core.windows.net/"):
            with self.subTest(kind="invalid account key"):
                with self.assertRaises(ConnectionError):
                    vault.save("azure_blob",{"account":"teststore","container":"private",
                                               "auth_mode":"account_key"},wrong)
        saved=vault.save("azure_blob",{"account":"teststore","container":"private",
                                       "auth_mode":"account_key"},key)
        self.assertEqual(saved["config"]["auth_mode"],"account_key")
        self.assertNotIn(key,json.dumps(saved))
        self.assertNotIn(key.encode(),(self.root/DATABASE).read_bytes())
        self.assertEqual(ConnectionVault(self.root).read_host_only("azure_blob")["secret"],key)
        self.assertNotIn("secret",json.dumps(vault.list_public()))
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        with patch.object(bridge_module,"verify_connection",return_value={
            "provider":"azure_blob","status":"CONTAINER_READ_VERIFIED",
            "detail":"Synthetic metadata read only."}) as verify:
            status,response=bridge.dispatch("POST","/api/connections",AUTH,
                json.dumps({"action":"test","provider":"azure_blob"}).encode())
        self.assertEqual(status,200)
        self.assertEqual(response["status"],"CONTAINER_READ_VERIFIED")
        verify.assert_called_once()
        self.assertEqual(verify.call_args.args[1]["config"]["auth_mode"],"account_key")
        self.assertEqual(verify.call_args.args[1]["secret"],key)
        self.assertNotIn(key,json.dumps(response))


    def test_azure_owner_read_requires_auth_explicit_blob_and_separate_model_sharing(self):
        bridge=bridge_module.OwnerBridge(self.root,TOKEN)
        key=base64.b64encode(b"K"*64).decode("ascii")
        bridge.vault.save("azure_blob",{"account":"teststore","container":"cosmo",
                                        "auth_mode":"account_key"},key)
        request={"blob_name":"docs/guide.txt","read_confirmed":True}
        raw=json.dumps(request).encode()
        self.assertEqual(bridge.dispatch("POST","/api/azure-read","",raw)[0],401)
        self.assertEqual(bridge.dispatch("POST","/api/azure-read",AUTH,
            json.dumps({"blob_name":"docs/guide.txt"}).encode())[0],400)
        sample={"source":"AZURE_BLOB_EXPLICIT_READ","blob_name":"docs/guide.txt",
                "sha256":"a"*64,"bytes":7,"text":"private",
                "retrieval_verified":True,"persisted":False,"model_invoked":False,
                "source_claims_verified":False}
        with patch.object(bridge_module,"read_owner_text",return_value=sample) as read:
            status,returned=bridge.dispatch("POST","/api/azure-read",AUTH,raw)
            self.assertEqual(status,200)
            self.assertEqual(returned,sample)
            read.assert_called_once()
            self.assertEqual(read.call_args.args[0]["secret"],key)
            self.assertEqual(read.call_args.args[1],"docs/guide.txt")
        self.assertNotIn(key,json.dumps(returned))
        self.assertEqual(bridge.dispatch("GET","/api/conversation",AUTH)[1]["turns"],[])
        self.assertFalse(bridge.app.authority.allowed("cloud"))
        self.assertEqual(bridge.dispatch("POST","/api/azure-read",AUTH,
            json.dumps({"blob_name":"../secret.txt","read_confirmed":True}).encode())[0],400)


if __name__=="__main__":
    unittest.main()
