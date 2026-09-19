"""Host smoke for the same adapter embedded by Chaquopy; no mock runtime."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app/src/main/python'))


class AndroidBridgeTests(unittest.TestCase):
    def test_bridge_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('beast_android'), 'Android adapter is missing')

    def test_restart_and_provider_swap_retain_actual_runtime(self):
        from beast_android import AndroidRuntime
        from beastbox.durable import DurableRuntime
        with tempfile.TemporaryDirectory() as root:
            app = AndroidRuntime(root)
            self.assertIsInstance(app.runtime, DurableRuntime)
            first = json.loads(app.send('Remember the cobalt lighthouse'))
            self.assertIn('deterministic fixture A', first['response'])
            before = json.loads(app.inspect())['inspection']
            app.close()
            app = AndroidRuntime(root)
            after = json.loads(app.inspect())['inspection']
            self.assertEqual(before, after)
            app.configure('reference-b', '', '')
            second = json.loads(app.send('Recall the cobalt lighthouse'))
            self.assertIn('deterministic fixture B', second['response'])
            self.assertTrue(any('cobalt lighthouse' in h['text'] for h in second['memory_hits']))
            self.assertEqual(before['system_id'], second['inspection']['system_id'])
            self.assertEqual(2, second['inspection']['turn'])
            app.restart()
            self.assertEqual(2, json.loads(app.inspect())['inspection']['turn'])
            self.assertEqual('reference-b', json.loads(app.inspect())['provider']['kind'])
            app.configure('reference-a', '', '')
            third = json.loads(app.send('Recall the cobalt lighthouse again'))
            self.assertIn('deterministic fixture A', third['response'])
            self.assertEqual(before['system_id'], third['inspection']['system_id'])
            self.assertEqual(3, third['inspection']['turn'])
            self.assertTrue(any('cobalt lighthouse' in h['text'] for h in third['memory_hits']))
            app.close()

    def test_provider_configuration_fails_closed_without_memory_changes(self):
        from beast_android import AndroidRuntime
        with tempfile.TemporaryDirectory() as root:
            app = AndroidRuntime(root)
            before = json.loads(app.inspect())
            for url in ('https://example.com', 'http://user:secret@localhost:11434',
                        'http://localhost:11434?key=secret', 'http://10.0.2.2:11434'):
                with self.assertRaises(ValueError):
                    app.configure('ollama', 'qwen2.5:3b', url)
                self.assertEqual(before, json.loads(app.inspect()))
            with self.assertRaises(ValueError):
                app.configure('remote', 'model', 'http://localhost:11434')
            app.configure('ollama', 'qwen2.5:3b', 'http://127.0.0.1:11434')
            self.assertEqual('LocalOllamaProvider', type(app.runtime.provider.delegate).__name__)
            self.assertEqual(before['inspection'], json.loads(app.inspect())['inspection'])
            app.close()


if __name__ == '__main__':
    unittest.main()
