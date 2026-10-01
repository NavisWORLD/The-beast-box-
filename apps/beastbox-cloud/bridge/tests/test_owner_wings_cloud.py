"""Actual owner transport contract; synthetic temporary directory only."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("owner_wings_bridge",Path(__file__).resolve().parents[1]/"owner_bridge.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TOKEN="public-test-activation-owner-token-strong-2026"
AUTH="Bearer "+TOKEN

class OwnerWingsTests(unittest.TestCase):
    def test_authenticated_stop_and_no_cloud_grant(self):
        with tempfile.TemporaryDirectory() as root:
            owner=module.OwnerBridge(Path(root),TOKEN)
            self.assertEqual(owner.dispatch("GET","/api/activation","")[0],401)
            self.assertEqual(owner.dispatch("POST","/api/authority",AUTH,b'{"action":"grant","name":"shell"}')[0],400)
            status,initial=owner.dispatch("GET","/api/activation",AUTH)
            self.assertEqual(status,200)
            self.assertTrue(initial["stopped"])
            status,queued=owner.dispatch("POST","/api/activation",AUTH,b'{"action":"enqueue_maintenance"}')
            self.assertEqual(status,200)
            self.assertEqual(queued["status"],"queued")
            status,_=owner.dispatch("POST","/api/authority",AUTH,b'{"action":"master_stop"}')
            self.assertEqual(status,200)
            status,state=owner.dispatch("GET","/api/activation",AUTH)
            self.assertEqual(status,200)
            self.assertTrue(state["stopped"])
            self.assertEqual(state["counts"]["queued"],1)
            status,run=owner.dispatch("POST","/api/activation",AUTH,b'{"action":"run","max_tasks":1,"wall_seconds":1}')
            self.assertEqual(status,200)
            self.assertEqual(run["status"],"STOPPED")
    def test_cloud_never_enqueues_unconsented_sensor_events_or_unbounded_work(self):
        with tempfile.TemporaryDirectory() as root:
            owner=module.OwnerBridge(Path(root),TOKEN)
            for payload in ({"action":"enqueue_event","event":{"source":"x","text":"y","features":[]}},
                            {"action":"grant","name":"shell"},
                            {"action":"run","max_tasks":100,"wall_seconds":300}):
                code,_=owner.dispatch("POST","/api/activation",AUTH,json.dumps(payload).encode())
                self.assertEqual(code,400)

if __name__=="__main__":
    unittest.main()
