"""Synthetic negative controls for the source-identity gate."""
import unittest

from verify_source_snapshot import BASELINE_BLOBS, parse_ls_tree, verify


class SourceIntegrityTest(unittest.TestCase):
    def test_parse_tree_with_null_separators(self):
        parsed = parse_ls_tree(b"100644 blob abc\tREADME.md\x00100644 blob def\tevidence/log.jsonl\x00")
        self.assertEqual(parsed["README.md"], ("100644", "abc"))
        self.assertEqual(parsed["evidence/log.jsonl"], ("100644", "def"))

    def test_tamper_protected_source_rejected(self):
        baseline = {f"docs/d{i}.md": ("100644", f"{i:040x}") for i in range(BASELINE_BLOBS)}
        current = dict(baseline)
        current.update({"Endsupdate/" + key: val for key, val in baseline.items()})
        current["Endsupdate/research_note.md"] = ("100644", "f" * 40)
        report = verify(baseline=baseline, current=current)
        self.assertTrue(all(report["checks"].values()))
        current["Endsupdate/docs/d5.md"] = ("100644", "e" * 40)
        report = verify(baseline=baseline, current=current)
        self.assertFalse(report["checks"]["copied_baseline_unchanged_outside_declared_overlays"])
        self.assertEqual(report["unapproved_copied_changes"], ["docs/d5.md"])

    def test_root_change_and_missing_copy_rejected(self):
        baseline = {f"evidence/e{i}": ("100644", f"{i:040x}") for i in range(BASELINE_BLOBS)}
        current = dict(baseline)
        current.update({"Endsupdate/" + key: val for key, val in baseline.items()})
        current["Endsupdate/research_note.md"] = ("100644", "f" * 40)
        current["evidence/e7"] = ("100644", "e" * 40)
        del current["Endsupdate/evidence/e8"]
        report = verify(baseline=baseline, current=current)
        self.assertFalse(report["checks"]["root_baseline_unchanged"])
        self.assertFalse(report["checks"]["baseline_paths_present"])

    def test_declared_overlay_must_preserve_mode(self):
        baseline = {f"docs/d{i}.md": ("100644", f"{i:040x}") for i in range(BASELINE_BLOBS)}
        baseline["scripts/productization_receipt.py"] = ("100644", "a" * 40)
        current = dict(baseline)
        current.update({"Endsupdate/" + key: val for key, val in baseline.items()})
        current["Endsupdate/new.py"] = ("100644", "b" * 40)
        current["Endsupdate/scripts/productization_receipt.py"] = ("100644", "c" * 40)
        self.assertTrue(all(verify(baseline=baseline, current=current)["checks"].values()))
        current["Endsupdate/scripts/productization_receipt.py"] = ("100755", "c" * 40)
        self.assertFalse(verify(baseline=baseline, current=current)["checks"]["overlay_modes_unchanged"])


if __name__ == "__main__":
    unittest.main()
