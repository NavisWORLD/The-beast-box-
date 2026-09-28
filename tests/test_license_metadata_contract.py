"""Dependency-free Apache-2.0 metadata contract regressions."""
import json
import unittest
from scripts.license_metadata_contract import ROOT, category, status_errors, verify

class ApacheMetadataContractTests(unittest.TestCase):
    def test_actual_checked_out_metadata_is_consistent(self):
        self.assertEqual(verify(ROOT), [])

    def test_detects_status_disagreement_without_touching_original(self):
        state = json.loads((ROOT / "PROJECT_STATUS.json").read_text(encoding="utf-8"))
        self.assertEqual(status_errors(state), [])
        state["license"] = "other-license"
        state["open_source"] = False
        self.assertEqual(len(status_errors(state)), 2)

    def test_restored_native_package_is_covered(self):
        manifest = ROOT / "models/rawrphos/pyproject.toml"
        if manifest.is_file():
            self.assertIn('license = "Apache-2.0"', manifest.read_text(encoding="utf-8"))
        self.assertEqual(verify(ROOT), [])

    def test_historical_and_external_licenses_remain_separate(self):
        for path in (
            "LICENSE_HISTORY.md", "Endsupdate/PROJECT_STATUS.json",
            "docs/closure/PREVIOUS_PRODUCT_STATUS.json",
            "apps/licenses/PyInstaller-COPYING.txt",
        ):
            self.assertEqual(category(path), "PRESERVED_HISTORY_OR_THIRD_PARTY")
        self.assertEqual(category("PROJECT_STATUS.json"), "CURRENT_OR_UNCLASSIFIED")

if __name__ == "__main__":
    unittest.main()
