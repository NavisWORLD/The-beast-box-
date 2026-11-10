"""Lineage check for the Zeref 006 training parent.

A same-cycle sibling whose recorded parent sha does not lead back to the pin
must not be resumed, even when it is newer than a sibling that does.
"""
from __future__ import annotations

import unittest

from scripts.zeref_resume_parent import select_training_parent


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


if __name__ == "__main__":
    unittest.main()
