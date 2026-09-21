"""Tests for a bounded *real-connectivity-subset* virtual walking simulation.
Do not construe any test as a validation of biological movement.
"""
import hashlib
import json
import pathlib
import sys
import unittest
import numpy as np

HERE=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import fly_movement as f

class TestMovingFly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=f.load_graph()

    def test_exact_source_derived_subgraph_fingerprint(self):
        src={k:self.data[k] for k in ('ids','roles','sides','edges')}
        raw=json.dumps(src,separators=(',',':')).encode('ascii')
        h=2166136261
        for b in raw:h=((h^b)*16777619)&0xffffffff
        self.assertEqual(hex(h),'0xa2b8f5fa')  # derived independently through GitHub connector
        self.assertEqual(len(self.data['ids']),42)
        self.assertEqual(len(self.data['edges']),95)
        self.assertTrue(all(i.startswith('720575') for i in self.data['ids']))
        self.assertIn('CC BY-NC 4.0',self.data['license'])

    def test_finite_neural_state_and_exact_dyn12_dimensions(self):
        r=f.simulate(self.data,'published_subset',2,ticks=14)
        for p in r['trace']:
            self.assertEqual(len(p['dyn12']),12)
            self.assertEqual(len(p['neural']),42)
            self.assertTrue(all(np.isfinite(p['neural'])))
            self.assertTrue(all(np.isfinite(p['dyn12'])))
            self.assertTrue(-4.16<p['x']<4.16)
            self.assertTrue(-2.41<p['y']<2.41)

    def test_lesions_disconnect_both_directions(self):
        W,damage=f.incoming_matrix(self.data,'25pct_lesion',3)
        self.assertEqual(len(damage),42//4)
        for k in damage:
            self.assertTrue(np.all(W[k,:]==0))
            self.assertTrue(np.all(W[:,k]==0))

    def test_matched_rewire_differs_from_original(self):
        a,_=f.incoming_matrix(self.data,'published_subset',0)
        b,_=f.incoming_matrix(self.data,'weight_matched_rewire',0)
        self.assertFalse(np.array_equal(a,b))
        self.assertTrue(np.isfinite(a).all())
        self.assertTrue(np.isfinite(b).all())

    def test_seed_is_deterministic_and_source_changes_state(self):
        a=f.simulate(self.data,'published_subset',1,ticks=18)
        b=f.simulate(self.data,'published_subset',1,ticks=18)
        c=f.simulate(self.data,'no_propagation',1,ticks=18)
        self.assertEqual(a,b)
        self.assertNotEqual(a['trace'][-1]['neural'],c['trace'][-1]['neural'])
        self.assertEqual(a['trace'][-1]['tick'],17)

    def test_video_and_trace_are_bound_to_source(self):
        evidence=HERE/'real_fly_demo'
        if not (evidence/'movement_traces.jsonl').exists() or not (evidence/'Cosmic_Fruit_Fly_Real_Wiring_Moving_Demo.mp4').exists():
            self.skipTest('Full historical movement trace/video are external to the source-only Git snapshot')
        manifest=json.loads((evidence/'results.json').read_text())
        video=json.loads((evidence/'video_manifest.json').read_text())
        self.assertEqual(manifest['data_sha256'],f.sha256(f.DATA))
        self.assertEqual(manifest['trace_sha256'],f.sha256(evidence/'movement_traces.jsonl'))
        self.assertEqual(video['source_data_sha256'],manifest['data_sha256'])
        self.assertEqual(video['sha256'],f.sha256(evidence/video['video']))
        self.assertIn('NOT BIOLOGICAL LOCOMOTION',manifest['classification'])

if __name__=='__main__': unittest.main()
