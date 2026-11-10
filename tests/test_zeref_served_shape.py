"""Served-shape chat rows: live preface, answer-only loss, no heldout leakage."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.zeref_served_shape import (
    FRACTION,
    SELECTION_SEED,
    TOKEN_CAP,
    answer_example,
    apply_served_shape,
    descriptor_from_recorded,
    encode_chat_row,
    load_forbidden_texts,
    load_recorded,
    render_prompt,
    row_selected,
)


ROOT = Path(__file__).resolve().parents[1]
HELD_USER = "What is the antonym of noisy?"
GATE_USER = "How many ears do cats have?"


def _encode(text, add_bos=False, add_eos=False):
    # Coarser than the real byte-BPE so a recorded descriptor still fits the cap.
    count = max(1, (len(text) + 19) // 20)
    ids = list(range(3, 3 + count))
    if add_bos:
        ids = [1] + ids
    if add_eos:
        ids = ids + [2]
    return ids


def _rows():
    made = []
    for index in range(6):
        made.append({
            "mode": "chat",
            "source": "zeref-lessons-006",
            "user": "What is public fact %s?" % index,
            "assistant": "Public fact %s is a short authored answer." % index,
        })
    made.append({
        "mode": "chat",
        "source": "zeref-lessons-006",
        "user": HELD_USER,
        "assistant": "The antonym of noisy is quiet.",
    })
    made.append({
        "mode": "chat",
        "source": "zeref-lessons-006",
        "user": GATE_USER,
        "assistant": "Two ears.",
    })
    return made


def _recorded():
    recorded = load_recorded(ROOT)
    recorded["diary"] = recorded["diary"][-3:]
    return recorded


class ServedShapeTest(unittest.TestCase):
    def test_valid_served_shape_rows_use_the_mouth_descriptor(self):
        recorded = _recorded()
        rows = _rows()
        forbidden = load_forbidden_texts(ROOT)
        field = apply_served_shape(rows, forbidden, recorded, _encode, fraction=1.0)
        served = [row for row in rows if row.get("served_shape") is True]
        self.assertGreaterEqual(len(served), 1)
        self.assertEqual(field["fraction"], 1.0)
        self.assertEqual(field["selection_seed"], SELECTION_SEED)
        self.assertEqual(field["rows"], len(served))
        descriptor = descriptor_from_recorded(recorded["state12"], recorded["sequence"])
        body = json.loads(descriptor)
        self.assertEqual(body["schema"], "lived-state-descriptor-v1")
        self.assertEqual(len(body["state12"]), 12)
        self.assertEqual(body["state12"], [float(item) for item in recorded["state12"]])
        for row in served:
            messages = row["messages"]
            self.assertEqual(messages[0]["role"], "system")
            self.assertIn("lived-state-descriptor-v1", messages[0]["content"])
            self.assertEqual(messages[-1], {"role": "user", "content": row["user"]})
            self.assertTrue(render_prompt(messages).endswith("\nassistant:"))
            prior_users = [message["content"] for message in messages if message["role"] == "user"][:-1]
            self.assertGreaterEqual(len(prior_users), 1)
            self.assertLessEqual(len(prior_users), 3)
            self.assertIn("step %s" % recorded["pin_step"], "\n".join(m["content"] for m in messages if m["role"] == "system"))

    def test_token_cap_drops_prior_turns_before_preface_fields(self):
        def priced(text, add_bos=False, add_eos=False):
            # The full absent-channel descriptor does not fit; the state12 object does.
            count = 400 if '"channels"' in text else max(1, len(text) // 8)
            return [0] * (count + int(add_bos) + int(add_eos))

        recorded = _recorded()
        row = {"user": "Short question?", "assistant": "Short answer."}
        huge = "word " * 80
        priors = [(huge, huge), ("earlier question", "earlier answer")]
        from scripts.zeref_served_shape import build_messages
        messages = build_messages(row, priors, recorded, priced, limit=TOKEN_CAP)
        self.assertIsNotNone(messages)
        example = answer_example(priced, messages, row["assistant"], TOKEN_CAP)
        self.assertLessEqual(len(example["input"]) + 1, TOKEN_CAP)
        prior_users = [message["content"] for message in messages if message["role"] == "user"][:-1]
        self.assertNotIn(huge, prior_users)
        self.assertIn("earlier question", prior_users)
        descriptor = next(message["content"] for message in messages if message["role"] == "system" and "state12" in message["content"])
        body = json.loads(descriptor)
        self.assertEqual(body["state12"], [float(item) for item in recorded["state12"]])
        self.assertNotIn("channels", body)
        self.assertTrue(any(message["role"] == "system" and "step %s" % recorded["pin_step"] in message["content"] for message in messages))

    def test_last_prior_drops_before_the_recorded_state(self):
        def tight(text, add_bos=False, add_eos=False):
            if '"channels"' in text:
                count = 500
            elif "earlier question" in text:
                count = 300
            else:
                count = 80
            return [0] * (count + int(add_bos) + int(add_eos))

        recorded = _recorded()
        row = {"user": "Short question?", "assistant": "Short answer."}
        from scripts.zeref_served_shape import build_messages
        messages = build_messages(row, [("earlier question", "earlier answer")], recorded, tight, limit=TOKEN_CAP)
        self.assertIsNotNone(messages)
        self.assertEqual([message["content"] for message in messages if message["role"] == "user"], ["Short question?"])
        body = json.loads(next(message["content"] for message in messages if "state12" in message["content"]))
        self.assertEqual(body["state12"], [float(item) for item in recorded["state12"]])
        self.assertEqual(body["basis"], "dyn12-v1")
        example = answer_example(tight, messages, row["assistant"], TOKEN_CAP)
        self.assertLessEqual(len(example["input"]) + 1, TOKEN_CAP)

    def test_answer_only_mask_hides_preface_and_prior_turns(self):
        recorded = _recorded()
        rows = _rows()
        apply_served_shape(rows, load_forbidden_texts(ROOT), recorded, _encode, fraction=1.0)
        served = next(row for row in rows if row.get("served_shape") is True)
        example = encode_chat_row(_encode, served)
        self.assertTrue(example["served_shape"])
        front = _encode(render_prompt(example["messages"]), add_bos=True)
        tail = _encode(" " + served["assistant"], add_eos=True)
        self.assertEqual(example["target"][: len(front) - 1], [-100] * (len(front) - 1))
        self.assertEqual(example["target"][len(front) - 1 :], tail)
        self.assertNotIn(served["messages"][0]["content"], " ".join(str(item) for item in example["target"] if item != -100))

    def test_no_heldout_or_gate_leakage(self):
        forbidden = load_forbidden_texts(ROOT)
        self.assertIn(HELD_USER.strip().lower(), forbidden)
        self.assertIn(GATE_USER.strip().lower(), forbidden)
        rows = _rows()
        apply_served_shape(rows, forbidden, _recorded(), _encode, fraction=1.0)
        for row in rows:
            if row["user"] in (HELD_USER, GATE_USER):
                self.assertIsNot(row.get("served_shape"), True)
            for message in row.get("messages") or []:
                if message["role"] == "user":
                    self.assertNotIn(message["content"].strip().lower(), {HELD_USER.lower(), GATE_USER.lower()})

    def test_selection_is_deterministic_and_not_the_rotation_seed(self):
        recorded = _recorded()
        forbidden = load_forbidden_texts(ROOT)
        first = _rows()
        second = _rows()
        apply_served_shape(first, forbidden, recorded, _encode)
        apply_served_shape(second, forbidden, recorded, _encode)
        self.assertEqual(first, second)
        self.assertEqual(FRACTION, 0.15)
        self.assertNotEqual(SELECTION_SEED, "zeref-gate-v2-20261023")
        again = row_selected(first[0], SELECTION_SEED, FRACTION)
        self.assertEqual(again, row_selected(dict(first[0]), SELECTION_SEED, FRACTION))
        source = (ROOT / "scripts" / "zeref_served_shape.py").read_text()
        self.assertNotIn("Math.random", source)
        self.assertNotIn("import random", source)
        self.assertNotIn("random.Random", source)


if __name__ == "__main__":
    unittest.main()
