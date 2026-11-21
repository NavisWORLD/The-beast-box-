"""Dedicated self-learn export key (2026-11-19): opens GET /api/self-learn-export only."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

BRIDGE = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, BRIDGE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load("owner_bridge")
TOKEN = "public-fixture-token-not-valid-outside-ci-2026"
KEY = "public-fixture-export-key-not-valid-outside-ci-2026"


class ExportKeyTests(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("ZEREF_SELF_LEARN_EXPORT_KEY")
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        from beastbox import self_learn
        self_learn.record(self.root, scope="guest", user="what is the moon made of",
                          reply="rock and dust, and it shines with the sun", step=1, now=1)
        self.app = bridge.OwnerBridge(self.root, TOKEN)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("ZEREF_SELF_LEARN_EXPORT_KEY", None)
        else:
            os.environ["ZEREF_SELF_LEARN_EXPORT_KEY"] = self._old
        self.td.cleanup()

    def test_off_by_default(self):
        os.environ.pop("ZEREF_SELF_LEARN_EXPORT_KEY", None)
        status, _ = self.app.dispatch("GET", "/api/self-learn-export", "Bearer " + KEY)
        self.assertEqual(status, 401)

    def test_key_opens_export_only(self):
        os.environ["ZEREF_SELF_LEARN_EXPORT_KEY"] = KEY
        status, body = self.app.dispatch("GET", "/api/self-learn-export", "Bearer " + KEY)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["count"], 1)
        self.assertFalse(body["pin_written"])
        status, body = self.app.dispatch("GET", "/api/self-learn-export?since_id=1", "Bearer " + KEY)
        self.assertEqual((status, body["count"]), (200, 0))
        for method, path in [("GET", "/api/memory"), ("GET", "/api/provider"), ("GET", "/api/conversation"),
                             ("POST", "/api/chat"), ("POST", "/api/self-learn-export"), ("GET", "/api/bio")]:
            status, _ = self.app.dispatch(method, path, "Bearer " + KEY, json.dumps({"text": "hi"}).encode())
            self.assertEqual(status, 401, (method, path))

    def test_short_or_owner_equal_key_is_refused(self):
        os.environ["ZEREF_SELF_LEARN_EXPORT_KEY"] = "short"
        self.assertEqual(self.app.dispatch("GET", "/api/self-learn-export", "Bearer short")[0], 401)
        os.environ["ZEREF_SELF_LEARN_EXPORT_KEY"] = TOKEN  # must differ from the owner token: no second door
        self.assertTrue(self.app._export_key_ok("GET", "/api/self-learn-export", "Bearer " + TOKEN) is False)

    def test_owner_token_still_works_and_bad_query_rejected(self):
        os.environ["ZEREF_SELF_LEARN_EXPORT_KEY"] = KEY
        self.assertEqual(self.app.dispatch("GET", "/api/self-learn-export", "Bearer " + TOKEN)[0], 200)
        self.assertEqual(self.app.dispatch("GET", "/api/self-learn-export?since_id=-1", "Bearer " + KEY)[0], 400)
        self.assertEqual(self.app.dispatch("GET", "/api/self-learn-export?x=1", "Bearer " + KEY)[0], 400)
        self.assertEqual(self.app.dispatch("GET", "/api/self-learn-export", "Bearer " + KEY + "x")[0], 401)


if __name__ == "__main__":
    unittest.main()
