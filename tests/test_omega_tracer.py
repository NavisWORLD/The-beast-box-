import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from beastbox.durable import DurableRuntime
from beastbox.omega import TracedDurableRuntime, verify_trace_file
from beastbox.providers import ReferenceTextProvider


class FixedProvider:
    model = "fixed"

    def __init__(self, text="ok"):
        self.text = text

    def generate(self, prompt):
        return self.text


class FailingProvider:
    def generate(self, prompt):
        raise RuntimeError("model crashed")


def _tables(root):
    db = sqlite3.connect(Path(root) / "runtime.sqlite3")
    try:
        memories = db.execute("SELECT kind,text FROM memories ORDER BY id").fetchall()
        assoc = db.execute("SELECT a,b,weight,updates FROM associations ORDER BY a,b").fetchall()
        return memories, assoc
    finally:
        db.close()


class TracerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_trace_does_not_change_substrate_contents(self):
        turns = ["Remember the harbor code is cobalt", "What is the harbor code?", "Note the tide is low"]
        plain = DurableRuntime(self.base / "plain", ReferenceTextProvider())
        traced = TracedDurableRuntime(self.base / "traced", ReferenceTextProvider(), trace_path=self.base / "t.jsonl")
        for text in turns:
            a = plain.respond(text)
            b = traced.respond(text)
            self.assertEqual(a["routing"]["memory_ids"], b["routing"]["memory_ids"])
        plain.close()
        traced.close()
        self.assertEqual(_tables(self.base / "plain"), _tables(self.base / "traced"))
        self.assertEqual(len(verify_trace_file(self.base / "t.jsonl")), 3)

    def test_trace_records_real_stage_values(self):
        rt = TracedDurableRuntime(self.base / "rt", FixedProvider("alpha beta"), trace_path=self.base / "t.jsonl")
        rt.respond("gamma delta")
        out = rt.respond_event({"schema": "sensor-event-v1", "source": "synthetic-demo",
                                "text": "gamma epsilon", "features": [0.9, -0.9]})
        rt.close()
        record = verify_trace_file(self.base / "t.jsonl")[-1]
        signal = record["signal"]
        self.assertEqual(record["checkpoint"]["sha256"], out["checkpoint"]["sha256"])
        self.assertEqual(signal["state_after"]["drive_dimension"], 2)
        self.assertNotEqual(signal["state_before"]["dyn12"], signal["state_after"]["state_family_dyn12"])
        self.assertEqual([r["memory_id"] for r in signal["r12"]["ranked"]], out["routing"]["memory_ids"])
        pairs = {(c["a"], c["b"]): c for c in signal["hebbian"]["top_changed"]}
        self.assertEqual(pairs[("epsilon", "gamma")]["weight_before"], 0.0)
        self.assertEqual(pairs[("epsilon", "gamma")]["weight_after"], 0.25)
        self.assertEqual(pairs[("alpha", "beta")]["weight_before"], 0.25)
        self.assertEqual(pairs[("alpha", "beta")]["weight_after"], 0.5)
        self.assertIn("gamma epsilon", signal["model"]["prompt"])

    def test_tampered_trace_fails_verification(self):
        rt = TracedDurableRuntime(self.base / "rt", FixedProvider(), trace_path=self.base / "t.jsonl")
        rt.respond("one")
        rt.respond("two")
        rt.close()
        lines = (self.base / "t.jsonl").read_text().splitlines()
        edited = json.loads(lines[0])
        edited["response"] = "forged"
        (self.base / "t.jsonl").write_text(json.dumps(edited) + "\n" + lines[1] + "\n")
        with self.assertRaises(ValueError):
            verify_trace_file(self.base / "t.jsonl")

    def test_trace_inside_runtime_root_is_rejected(self):
        with self.assertRaises(ValueError):
            TracedDurableRuntime(self.base / "rt", trace_path=self.base / "rt" / "t.jsonl")

    def test_failed_turn_is_traced_and_rolled_back(self):
        rt = TracedDurableRuntime(self.base / "rt", FixedProvider(), trace_path=self.base / "t.jsonl")
        rt.respond("kept")
        before = rt.inspect()
        rt.swap_provider(FailingProvider())
        with self.assertRaises(RuntimeError):
            rt.respond("lost")
        after = rt.inspect()
        rt.close()
        self.assertEqual(before["checkpoint_sha256"], after["checkpoint_sha256"])
        last = verify_trace_file(self.base / "t.jsonl")[-1]
        self.assertEqual(last["status"], "FAILED_ROLLED_BACK")


if __name__ == "__main__":
    unittest.main()
