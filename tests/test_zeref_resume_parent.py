"""Lineage check for the Zeref 006 training parent.

A same-cycle sibling whose recorded parent sha does not lead back to the pin
must not be resumed, even when it is newer than a sibling that does.
"""
from __future__ import annotations

import unittest

from scripts.zeref_resume_parent import select_training_parent, pin_scores_from_report, not_worse_than_pin


PIN = "ab" * 32


def _release(cycle, checkpoint, parent, list_index, **overrides):
    record = {
        "tag": "zeref-006-cycle-%d-%s" % (cycle, checkpoint[:12]),
        "cycle": cycle,
        "list_index": list_index,
        "checkpoint_sha256": checkpoint,
        "parent_checkpoint_sha256": parent,
        "metadata_parent_sha256": parent,
        "approval_checkpoint_sha256": checkpoint,
        "approval_parent_sha256": parent,
        "accepted": True,
        "gate_accepted": True,
        "tarball_sha256": "tar-" + checkpoint[:12],
        "recorded_tarball_sha256": "tar-" + checkpoint[:12],
        "model_sha256": checkpoint,
    }
    record.update(overrides)
    return record


class ResumeParentLineageTest(unittest.TestCase):
    def test_rejects_same_cycle_sibling_with_broken_lineage(self):
        good = _release(60, "11" * 32, PIN, list_index=1)
        broken = _release(60, "22" * 32, "ff" * 32, list_index=0)
        chosen = select_training_parent([broken, good], PIN)
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen["checkpoint_sha256"], good["checkpoint_sha256"])
        self.assertNotEqual(chosen["checkpoint_sha256"], broken["checkpoint_sha256"])
        self.assertIsNone(select_training_parent([broken], PIN))

    def test_rejects_same_cycle_sibling_whose_tarball_or_model_sha_does_not_match(self):
        good = _release(60, "11" * 32, PIN, list_index=1)
        mismatched = _release(60, "33" * 32, PIN, list_index=0, model_sha256="44" * 32)
        tampered = _release(60, "55" * 32, PIN, list_index=0, tarball_sha256="other")
        self.assertEqual(select_training_parent([mismatched, tampered, good], PIN)["checkpoint_sha256"], good["checkpoint_sha256"])

    def test_rejects_same_cycle_sibling_whose_gate_did_not_accept_it(self):
        good = _release(60, "11" * 32, PIN, list_index=1)
        unaccepted = _release(60, "66" * 32, PIN, list_index=0, gate_accepted=False)
        self.assertEqual(select_training_parent([unaccepted, good], PIN)["checkpoint_sha256"], good["checkpoint_sha256"])

    def test_descendant_of_a_qualifying_parent_is_kept(self):
        parent = _release(60, "11" * 32, PIN, list_index=1)
        child = _release(61, "77" * 32, parent["checkpoint_sha256"], list_index=0)
        chosen = select_training_parent([child, parent], PIN)
        self.assertEqual(chosen["checkpoint_sha256"], child["checkpoint_sha256"])



class ResumeParentNotBehindPinTest(unittest.TestCase):
    """2026-11-19: a descendant whose own recorded A/B is worse than the pin's is not resumed."""
    PIN_SCORES = {"chat_a": 3.5074142569303515, "chat_b": 3.625876979827881}  # pin cycle 79, 4457415d

    def test_cycle_80_case_falls_back_to_the_pin(self):
        # cycle 80 (70aa7878): A 3.5204 / B 3.6389, approved against the previous pin's bar in run 43818870885
        c80 = _release(80, "70" * 32, PIN, list_index=0, chat_a_nll=3.5204297202825545, chat_b_nll=3.6388828480243682)
        self.assertIsNone(select_training_parent([c80], PIN, self.PIN_SCORES))
        self.assertEqual(select_training_parent([c80], PIN)["checkpoint_sha256"], c80["checkpoint_sha256"])  # no report: old rule

    def test_descendant_not_worse_is_kept(self):
        good = _release(80, "71" * 32, PIN, list_index=0, chat_a_nll=3.50, chat_b_nll=3.62)
        self.assertEqual(select_training_parent([good], PIN, self.PIN_SCORES)["checkpoint_sha256"], good["checkpoint_sha256"])

    def test_worse_on_b_only_or_missing_scores_is_skipped(self):
        b_worse = _release(80, "72" * 32, PIN, list_index=0, chat_a_nll=3.50, chat_b_nll=3.70)
        unknown = _release(80, "73" * 32, PIN, list_index=1)
        self.assertIsNone(select_training_parent([b_worse, unknown], PIN, self.PIN_SCORES))

    def test_better_child_of_a_worse_parent_is_kept(self):
        worse = _release(80, "74" * 32, PIN, list_index=1, chat_a_nll=3.52, chat_b_nll=3.64)
        child = _release(81, "75" * 32, worse["checkpoint_sha256"], list_index=0, chat_a_nll=3.49, chat_b_nll=3.60)
        self.assertEqual(select_training_parent([child, worse], PIN, self.PIN_SCORES)["checkpoint_sha256"], child["checkpoint_sha256"])

    def test_pin_scores_from_report(self):
        self.assertEqual(pin_scores_from_report({"recipe": {"chat_after_nll": 3.5, "chat_b_after_nll": 3.6}}), {"chat_a": 3.5, "chat_b": 3.6})
        self.assertIsNone(pin_scores_from_report({"recipe": {"chat_after_nll": None}}))
        self.assertIsNone(pin_scores_from_report({}))
        self.assertTrue(not_worse_than_pin({}, None))


if __name__ == "__main__":
    unittest.main()
