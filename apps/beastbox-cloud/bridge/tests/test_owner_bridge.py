"""Exercise original durable COSMOS loop in the owner bridge; no fake provider swaps."""
import importlib.util
import json
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

if __name__=="__main__":
    unittest.main()
