"""Isolated engineering acceptance tests; never evidence of fly behavior."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fly_harness', HERE / 'harness.py')
h = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = h
spec.loader.exec_module(h)


class TestFruitFly(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = pathlib.Path(self.temp.name) / 'synthetic.csv'
        h.fixture(self.path)
        self.meta = self.path.with_suffix('.metadata.json')

    def graph(self):
        return h.load_graph(self.path, self.meta)

    def test_provenance_hash_rejects_mutated_bytes(self):
        self.path.write_text(self.path.read_text() + 'tampering\n')
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            self.graph()

    def test_missing_provenance_is_fail_closed(self):
        with self.assertRaises(FileNotFoundError):
            h.load_graph(self.path, self.path.with_name('missing.json'))

    def test_graph_and_arms_and_model_separation(self):
        g = self.graph()
        self.assertEqual(len(g.ids), 24)
        self.assertGreater(len(g.edges), 8)
        r = h.experiment(g, (0, 1), ntrain=12, ntest=8)
        self.assertEqual(r['classification'], 'synthetic_engineering_only')
        self.assertEqual({run['arm'] for run in r['runs']}, set(h.ARMS))
        self.assertEqual(len(r['runs']), len(h.ARMS) * 2)
        self.assertTrue(all(run['total'] == {'train': 12, 'test': 8} for run in r['runs']))
        self.assertTrue(all(run['steps'] == 12 * 5 + 8 * 8 for run in r['runs']))
        self.assertTrue(all(0 <= run['test_accuracy'] <= 1 for run in r['runs']))
        self.assertTrue(all(run['memory_entries'] == 0 for run in r['runs'] if 'memory_off' in run['arm']))
        self.assertTrue(all(run['plasticity_l1'] == 0 for run in r['runs'] if run['arm'] == 'plasticity_off'))
        self.assertTrue(all(run['neural_edge_ops'] == 0 for run in r['runs'] if run['arm'] == 'baseline'))
        self.assertTrue(all(run['lesion_neurons'] > 0 for run in r['runs'] if run['arm'] == 'lesion'))

    def test_seed_replay_is_deterministic_except_runtime(self):
        g = self.graph()
        a = h.run_arm(g, 'connectome', 2, 12, 8)
        b = h.run_arm(g, 'connectome', 2, 12, 8)
        a.pop('elapsed_ms')
        b.pop('elapsed_ms')
        self.assertEqual(a, b)

    def test_rewire_preserves_weight_multiset_and_count(self):
        g = self.graph()
        x = h.rewired(g, 2)
        self.assertEqual(sorted(w for _, _, w in g.edges), sorted(w for _, _, w in x.edges))
        self.assertEqual(len(g.edges), len(x.edges))
        self.assertNotEqual(g.edges, x.edges)

    def test_actual_dyn12_is_loaded_and_has_12_dimensions(self):
        self.assertEqual(len(h.canonical_dyn12([0.0]*12, [0.1], 4)), 12)
        with self.assertRaises(ValueError):
            h.canonical_dyn12([0.0]*11, [0.1], 4)

    def test_graph_size_is_bounded(self):
        g = h.load_graph(self.path, self.meta, max_neurons=8, max_edges=15)
        self.assertLessEqual(len(g.ids), 8)
        self.assertLessEqual(len(g.edges), 15)


if __name__ == '__main__':
    unittest.main()
