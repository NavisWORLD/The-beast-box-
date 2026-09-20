"""The conversation must depend on real previous model text and preserve every turn."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

FILE = Path(__file__).resolve().parents[1] / "continuous_conversation.py"
spec = importlib.util.spec_from_file_location("continuous_conversation", FILE)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class ConversationTests(unittest.TestCase):
    def test_follow_up_uses_actual_prior_response(self):
        turns = [{"response": "A weird purple goose said hello.", "phase": "A0"}]
        followup = subject.follow_up(turns, "A0", 2)
        self.assertIn("A weird purple goose said hello.", followup)

    def test_first_return_prompt_quotes_phos_not_fake_text(self):
        turns = [{"response": " The image is a dimly lit bedroo", "phase": "B0"}]
        question = subject.follow_up(turns, "A1", 1)
        self.assertIn("dimly lit bedroo", question)

    def test_phos_exact_input_fits_real_window(self):
        memory = [{"text": "User marker: mango goose 47."}]
        turns = [{"response": "Unexpected last response!", "phase": "A0"}]
        prompt, meta = subject.make_input("B0", "Tell me a story about the marker", memory, turns)
        self.assertLessEqual(len(prompt), 128)
        self.assertTrue(meta["memory_marker_delivered"])
        self.assertTrue(meta["prior_reply_excerpt_delivered"])

    def test_full_dialogue_is_recorded_even_when_model_fails(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            ledger = subject.core.Ledger(out)
            turns = []
            def fail_model(_):
                raise RuntimeError("offline")
            row = subject.execute_turn(ledger, "A0", subject.core.A_ID, fail_model,
                                       "Hello", [{"text": "marker"}], turns,
                                       out / "conversation_turns.jsonl")
            ledger.close()
            self.assertIsNone(row["response"])
            self.assertIn("offline", row["error"])
            self.assertEqual(subject.core.verify(out / "events.jsonl")[0], 2)
            line = json.loads((out / "conversation_turns.jsonl").read_text().strip())
            self.assertEqual(line["question"], "Hello")
            self.assertIsNone(line["response"])

    def test_phase_plan_contains_multiple_turns(self):
        self.assertEqual(sum(n for _, _, n in subject.PHASES), 10)
        self.assertEqual([phase for phase, _, _ in subject.PHASES], ["A0", "B0", "A1"])


if __name__ == "__main__":
    unittest.main()
