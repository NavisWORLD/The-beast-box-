import json, unittest
from pathlib import Path
from beastbox import rawrphos_local as r

class PublicPin(unittest.TestCase):
    def test_repo_pin_is_14000_or_proven_promotion(self):
        pin = json.loads(r.PIN_PATH.read_text())
        if pin["promotion"] is None:
            self.assertEqual((r.STEP, r.SHA), (r.BASE_STEP, r.BASE_SHA))
        else:
            self.assertTrue(pin["promotion"]["chat_not_worse"])
            self.assertEqual((r.STEP, r.SHA), (pin["training_steps"], pin["checkpoint_sha256"]))
    def _with(self, payload):
        old = r.PIN_PATH
        tmp = Path(self._testMethodName + ".json"); tmp.write_text(json.dumps(payload))
        try:
            r.PIN_PATH = tmp; return r._public_pin()
        finally:
            r.PIN_PATH = old; tmp.unlink()
    def test_unproven_promotion_keeps_14000(self):
        bad = {"schema": "rawrphos-public-pin-v1", "model_id": "rawrphos-native", "training_steps": 15000,
               "checkpoint_sha256": "a" * 64, "promotion": {"chat_not_worse": False}}
        self.assertEqual(self._with(bad), (r.BASE_STEP, r.BASE_SHA))
    def test_proven_promotion_serves_new_step(self):
        good = {"schema": "rawrphos-public-pin-v1", "model_id": "rawrphos-native", "training_steps": 15000,
                "checkpoint_sha256": "a" * 64, "promotion": {"chat_not_worse": True, "baseline_sha256": r.BASE_SHA,
                "candidate_sha256": "a" * 64, "release_tag": "zeref-006-cycle-9-aaaa", "chat_eval_sha256": "b" * 64}}
        self.assertEqual(self._with(good), (15000, "a" * 64))
if __name__ == "__main__": unittest.main()
