"""Regression coverage for conservative cgroup-v2 native model readiness."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from beastbox.cgroup_memory import available_bytes, MIN_HEADROOM_BYTES
from beastbox import rawrphos_local, rawrphos_experimental_local

class MemoryHeadroomTests(unittest.TestCase):
    def test_reclaimable_cache_is_discounted_without_ignoring_active_usage(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            (root / "memory.max").write_text("1073741824")
            (root / "memory.current").write_text("838860800")
            (root / "memory.stat").write_text("inactive_file 471859200\n")
            self.assertGreater(available_bytes(root), MIN_HEADROOM_BYTES)
            (root / "memory.stat").write_text("inactive_file 0\n")
            self.assertLess(available_bytes(root), MIN_HEADROOM_BYTES)
            (root / "memory.stat").write_text("inactive_file malformed\n")
            self.assertLess(available_bytes(root), MIN_HEADROOM_BYTES)
            (root / "memory.max").write_text("max")
            self.assertIsNone(available_bytes(root))

    def test_both_native_profiles_preserve_reserve_and_require_live_loopback(self):
        for model, setting in ((rawrphos_local, "RAWRPHOS_CHECKPOINT_PATH"),
                               (rawrphos_experimental_local, "RAWRPHOS_18K_CHECKPOINT_PATH")):
            with self.subTest(step=model.STEP), tempfile.TemporaryDirectory() as work:
                root = Path(work)
                (root / "metadata.json").write_text(json.dumps({"model_id": model.MODEL,
                    "lineage": "native-from-scratch", "training_steps": model.STEP,
                    "checkpoint_sha256": model.SHA}))
                (root / "manifest.json").write_text(json.dumps({"schema": "rawrphos-checkpoint-v1",
                    "files": {"model.safetensors": model.SHA}}))
                with patch.dict("os.environ", {setting: work, "RAWRPHOS_API_KEY": ""}):
                    with patch.object(model, "available_bytes", return_value=MIN_HEADROOM_BYTES - 1):
                        self.assertEqual(model.status()["readiness"], "INSUFFICIENT_RESOURCES")
                    with patch.object(model, "available_bytes", return_value=MIN_HEADROOM_BYTES + 1):
                        self.assertEqual(model.status()["readiness"], "OFFLINE_OR_DISCONNECTED")

if __name__ == "__main__":
    unittest.main()
