"""Fail-closed ten-minute protocol tests; run without any model downloads."""
import importlib.util
from pathlib import Path
import unittest
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location("ten_minute_session",ROOT/"ten_minute_session.py")
subject=importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
class ProtocolTests(unittest.TestCase):
    def test_actual_elapsed_target(self):
        self.assertEqual(subject.TOTAL_SECONDS,600)
    def test_three_phases_and_turns(self):
        self.assertEqual(subject.TURNS_EACH*len(subject.PHASES),36)
        self.assertEqual([p for p,_ in subject.PHASES],["A0","B0","A1"])
    def test_followup_uses_real_preceding_response(self):
        turns=[{"response":"Actually I'm a goose, not a lamp."}]
        self.assertIn("goose, not a lamp",subject.question_for("B0",0,turns))
    def test_phos_input_is_128_chars_max(self):
        q="A very long question; "+"repeat "*80
        turn=[{"response":"The image is a dimly lit bedroo", "phase":"A0"}]
        prompt,meta=subject.make_input("B0",q,[{"text":"mango goose 47"}],turn)
        self.assertLessEqual(len(prompt),128)
        self.assertTrue(meta["memory_marker_delivered"])
        self.assertTrue(meta["prior_reply_excerpt_delivered"])
if __name__=="__main__":unittest.main()
