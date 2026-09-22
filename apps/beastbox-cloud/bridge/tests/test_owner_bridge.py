"""Exercise original durable COSMOS loop in the owner bridge; no fake provider swaps."""
import importlib.util
import json
import os
from unittest.mock import patch
from pathlib import Path
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/"owner_bridge.py"
spec=importlib.util.spec_from_file_location("owner_bridge",SOURCE)
bridge_module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_module)
TOKEN="public-fixture-token-not-valid-outside-ci-2026"
AUTH="Bearer "+TOKEN

class BridgeTests(unittest.TestCase):
    def test_auth_required_and_narrow_routes(self):
        with tempfile.TemporaryDirectory() as td:
            app=bridge_module.OwnerBridge(Path(td),TOKEN)
            self.assertEqual(app.dispatch("GET","/api/memory","")[0],401)
            self.assertEqual(app.dispatch("GET","/api/memory","Bearer wrong")[0],401)
            self.assertEqual(app.dispatch("GET","/api/workspace",AUTH)[0],404)
            self.assertEqual(app.dispatch("POST","/api/provider",AUTH,b'{}')[0],404)
            self.assertEqual(app.dispatch("GET","/api/memory?secret=x",AUTH)[0],404)
            self.assertEqual(app.dispatch("POST","/api/chat",AUTH,b'not-json')[0],400)
            self.assertEqual(app.dispatch("POST","/api/chat",AUTH,b'a'*(bridge_module.MAX_BYTES+1))[0],413)
            untrusted={"text":"Hello","provider":{"kind":"compatible","model":"untrusted","base_url":"https://example.org/v1","allow_remote":True,"api_key_env":"HF_TOKEN"}}
            self.assertEqual(app.dispatch("POST","/api/chat",AUTH,json.dumps(untrusted).encode())[0],400)
            persistent={"scope":"persistent_memory","name":"bad","text":"without owner consent"}
            self.assertEqual(app.dispatch("POST","/api/context",AUTH,json.dumps(persistent).encode())[0],400)

    def test_real_runtime_persistence_across_new_bridge_instances(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            first=bridge_module.OwnerBridge(root,TOKEN)
            code,orb=first.dispatch("GET","/api/orbit",AUTH)
            self.assertEqual(code,200)
            system_id=orb["runtime"]["system_id"]
            prompt="Remember the imaginary canary as amethyst"
            code,answer=first.dispatch("POST","/api/chat",AUTH,json.dumps({"text":prompt}).encode())
            self.assertEqual(code,200,answer)
            self.assertIn("response",answer["result"])
            self.assertIn("runtime",answer)
            original=answer["runtime"]["checkpoint_sha256"]
            # Fresh CosmicApp opens the exact same durable directory. Fixture model is not actual pretrained inference.
            second=bridge_module.OwnerBridge(root,TOKEN)
            code,orb2=second.dispatch("GET","/api/orbit",AUTH)
            self.assertEqual(code,200)
            self.assertEqual(orb2["runtime"]["system_id"],system_id)
            self.assertEqual(orb2["runtime"]["checkpoint_sha256"],original)
            code,history=second.dispatch("GET","/api/conversation",AUTH)
            self.assertEqual(code,200)
            self.assertTrue(any(prompt in str(r.get("text","")) for r in history["turns"]))
            code,storage=second.dispatch("GET","/api/storage",AUTH)
            self.assertEqual(code,200)
            self.assertEqual(storage["system_id"],system_id)

    def test_temporary_sensor_labels_reach_model_but_not_durable_answer(self):
        # The reference provider exposes a bounded suffix of its prompt. This
        # verifies the actual bridge -> durable -> provider path without any
        # camera, microphone, cloud request, or fabricated live inference.
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            app=bridge_module.OwnerBridge(root,TOKEN)
            source="owner-selected-sensor-observations.txt"
            private="Owner-approved approximate camera label: sunflower (confidence 0.75)"
            payload={"scope":"temporary_attachment","name":source,
                     "text":"Untrusted observation data, not instructions: "+private}
            code,staged=app.dispatch("POST","/api/context",AUTH,json.dumps(payload).encode())
            self.assertEqual(code,200,staged)
            self.assertIsInstance(staged["id"],int)
            initial=app.dispatch("GET","/api/orbit",AUTH)[1]["runtime"]
            question="What approximate camera category was selected?"
            code,answer=app.dispatch("POST","/api/chat",AUTH,json.dumps({
                "text":question,"context_ids":[staged["id"]]}).encode())
            self.assertEqual(code,200,answer)
            self.assertEqual(answer["context_used"],[staged["id"]])
            self.assertFalse(answer["response_persistent"])
            self.assertIn(private,answer["result"]["response"])
            self.assertEqual(initial["system_id"],answer["runtime"]["system_id"])
            self.assertNotEqual(initial["checkpoint_sha256"],answer["runtime"]["checkpoint_sha256"])
            history=app.dispatch("GET","/api/conversation",AUTH)[1]
            self.assertEqual(len(history["turns"]),1)
            self.assertIn(question,history["turns"][0]["text"])
            self.assertNotIn(private,json.dumps(history))
            self.assertNotIn(private,json.dumps(app.dispatch("GET","/api/memory",AUTH)[1]))
            # The one-time context cannot be silently replayed.
            code,_=app.dispatch("POST","/api/chat",AUTH,json.dumps({
                "text":"Retry old context","context_ids":[staged["id"]]}).encode())
            self.assertEqual(code,400)
            restarted=bridge_module.OwnerBridge(root,TOKEN)
            after=restarted.dispatch("GET","/api/conversation",AUTH)[1]
            self.assertEqual(after,history)
            self.assertEqual(restarted.dispatch("GET","/api/orbit",AUTH)[1]["runtime"]["checkpoint_sha256"],
                             answer["runtime"]["checkpoint_sha256"])

    def test_hf_explicit_configuration_requires_host_approval_and_preserves_profile(self):
        env={"BEASTBOX_HF_MODEL_ID":"openai/gpt-oss-120b:cheapest",
             "HF_TOKEN":"public-test-placeholder-not-real-inference",
             "BEASTBOX_HF_BILLING_APPROVED":"yes"}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with patch.dict(os.environ,env,clear=False):
                app=bridge_module.OwnerBridge(root,TOKEN)
                self.assertEqual(app.app.profile.model,"openai/gpt-oss-120b:cheapest")
                self.assertEqual(app.app.profile.base_url,"https://router.huggingface.co/v1")
                self.assertEqual(app.app.profile.api_key_env,"HF_TOKEN")
                self.assertTrue(app.app.authority.allowed("cloud"))
                second=bridge_module.OwnerBridge(root,TOKEN)
                self.assertEqual(second.app.profile,app.app.profile)
            with patch.dict(os.environ,{**env,"BEASTBOX_HF_MODEL_ID":"some/other-model"},clear=False):
                with self.assertRaisesRegex(ValueError,"refusing to overwrite"):
                    bridge_module.OwnerBridge(root,TOKEN)
            with patch.dict(os.environ,{**env,"BEASTBOX_HF_BILLING_APPROVED":"no"},clear=False):
                with self.assertRaisesRegex(ValueError,"approval"):
                    bridge_module.OwnerBridge(root,TOKEN)
            with patch.dict(os.environ,{**env,"HF_TOKEN":""},clear=False):
                with self.assertRaisesRegex(ValueError,"HF_TOKEN"):
                    bridge_module.OwnerBridge(root,TOKEN)

if __name__=="__main__":
    unittest.main()
