"""Candidate launch path invariants; not an OS isolation assessment."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import isolated_runtime


class IsolatedRuntimeTest(unittest.TestCase):
    def test_only_allowed_actions_and_reference_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            command = isolated_runtime.build_command("chat", "Hello", base=root)
            self.assertEqual(command[:4], [
                isolated_runtime.sys.executable, "-m", "beastbox", "runtime",
            ])
            self.assertEqual(command[4], "chat")
            self.assertEqual(command[-3:], ["--provider", "reference", "Hello"])
            self.assertIn(str(root / ".endsupdate-data"), command)
            with self.assertRaises(ValueError):
                isolated_runtime.build_command("quantum-input", base=root)
            with self.assertRaises(ValueError):
                isolated_runtime.build_command("chat", "", base=root)

    def test_rejects_symlink_and_file_data_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "source"
            root.mkdir()
            data = root / ".endsupdate-data"
            data.write_text("not a directory")
            with self.assertRaises(ValueError):
                isolated_runtime.dedicated_data_dir(root)
            data.unlink()
            other = Path(temp) / "shared"
            other.mkdir()
            try:
                data.symlink_to(other, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks not supported by this platform")
            with self.assertRaises(ValueError):
                isolated_runtime.dedicated_data_dir(root)

    def test_launch_does_not_forward_credential_like_environment(self):
        class Completed:
            returncode = 0

        with patch.dict(isolated_runtime.os.environ, {"BEASTBOX_SEAL_PASSPHRASE": "secret",
                                                      "IBM_QUANTUM_TOKEN": "secret",
                                                      "PATH": "/tmp"}, clear=True):
            with patch.object(isolated_runtime.subprocess, "run", return_value=Completed()) as run:
                result = isolated_runtime.main(["init"])
        self.assertEqual(result, 0)
        env = run.call_args.kwargs["env"]
        self.assertNotIn("BEASTBOX_SEAL_PASSPHRASE", env)
        self.assertNotIn("IBM_QUANTUM_TOKEN", env)
        self.assertEqual(env["PYTHONNOUSERSITE"], "1")


if __name__ == "__main__":
    unittest.main()
