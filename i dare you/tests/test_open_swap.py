"""Credential-free checks for the hash chain and external-memory isolation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "open_swap.py"
spec = importlib.util.spec_from_file_location("open_swap", SOURCE)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class ExperimentTests(unittest.TestCase):
    def test_chain_verifies(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger = subject.Ledger(root)
            ledger.emit("A0", "conversation_input", provider=subject.A_ID, prompt="hello")
            ledger.emit("B0", "blocked", reason="missing model")
            ledger.close()
            count, digest = subject.verify(root / "events.jsonl")
            self.assertEqual(count, 2)
            self.assertEqual(len(digest), 64)

    def test_tampering_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger = subject.Ledger(root)
            ledger.emit("A0", "conversation_output", response="real")
            ledger.close()
            path = root / "events.jsonl"
            path.write_text(path.read_text().replace('"real"', '"fake"'))
            with self.assertRaises(ValueError):
                subject.verify(path)

    def test_never_overwrite_existing_run(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = subject.Ledger(Path(td))
            ledger.close()
            with self.assertRaises(FileExistsError):
                subject.Ledger(Path(td))

    def test_memory_is_separate_from_provider(self):
        memory = [{"id": 1, "text": "mango goose 47"}]
        output = subject.contextualize("Tell me the marker", memory)
        self.assertIn("mango goose 47", output)
        self.assertIn("not model weights", output)


if __name__ == "__main__":
    unittest.main()
