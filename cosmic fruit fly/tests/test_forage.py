"""Isolated measured-software-learning acceptance checks, not biological validation."""
import pathlib
import sys
import unittest
import copy
import numpy as np

HERE=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import learn_to_forage as f

class TestForage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=f.load_graph()

    def test_hidden_reward_does_not_feed_brain_or_navigation(self):
        tr=f.trial_plan(2,(2,2,2))[0]
        altered=dict(tr,correct=1-tr['correct'])
        w,_=f.incoming_matrix(self.data,'published_subset',2)
        a=f.run_episode(self.data,w,tr,0,True)
        b=f.run_episode(self.data,w,altered,0,True)
        self.assertEqual(a['trace'],b['trace'])
        self.assertNotEqual(a['reward'],b['reward'])

    def test_heldout_layout_disjoint_and_reward_rule_preserved(self):
        v=f.trial_plan(2,(2,2,2))
        self.assertNotEqual(v[0]['stations'],v[2]['stations'])
        self.assertNotEqual(v[2]['stations'],v[4]['stations'])
        for a in v[:2]:
            for b in v[2:4]:
                if a['cue']==b['cue']:self.assertEqual(a['correct'],b['correct'])
        for a in v[:2]:
            for b in v[4:]:
                if a['cue']==b['cue']:self.assertNotEqual(a['correct'],b['correct'])

    def test_seed_deterministic(self):
        x=f.run_arm(self.data,'real_wiring_learning',3,counts=(4,2,3),collect_trace=False)
        y=f.run_arm(self.data,'real_wiring_learning',3,counts=(4,2,3),collect_trace=False)
        self.assertEqual(x,y)

    def test_memory_frozen_and_no_learning(self):
        fr=f.run_arm(self.data,'frozen_after_training',1,counts=(25,8,12))
        rev=[e for e in fr['episodes'] if e['phase']=='reversal']
        self.assertTrue(all(e['q_after']==rev[0]['q_before'] for e in rev))
        nl=f.run_arm(self.data,'no_learning',1,counts=(25,8,12))
        self.assertTrue(all(e['q_after']==[[.5,.5],[.5,.5]] for e in nl['episodes']))

    def test_wiring_affects_motor_not_reward_label(self):
        tr=f.trial_plan(0,(2,1,1))[0]
        a,_=f.incoming_matrix(self.data,'published_subset',0)
        b,_=f.incoming_matrix(self.data,'no_propagation',0)
        one=f.run_episode(self.data,a,tr,0,True)
        two=f.run_episode(self.data,b,tr,0,True)
        self.assertNotEqual([x['motor'] for x in one['trace']],[x['motor'] for x in two['trace']])
        self.assertEqual(one['reward'],two['reward'])

    def test_real_subset_and_dyn12(self):
        self.assertEqual(len(self.data['ids']),42)
        self.assertEqual(len(self.data['edges']),95)
        tr=f.trial_plan(2,(1,1,1))[0]
        w,_=f.incoming_matrix(self.data,'published_subset',2)
        result=f.run_episode(self.data,w,tr,0,True)
        self.assertTrue(result['arrived'])
        self.assertTrue(all(len(x['dyn12'])==12 and len(x['neural'])==42 for x in result['trace']))
        self.assertTrue(all(np.isfinite(x['neural']).all() for x in result['trace']))

    def test_observed_evidence_manifest(self):
        ev=HERE/'learning_demo'
        if not (ev/'results.json').exists():self.skipTest('no archived experiment')
        import json
        report=json.loads((ev/'results.json').read_text())
        self.assertEqual(report['episode_log_sha256'],f.sha256(ev/'all_runs.jsonl'))
        self.assertEqual(report['source_data_sha256'],f.sha256(f.DATA))
        self.assertEqual(report['dyn12_sha256'],f.sha256(HERE.parent/'beastbox'/'dyn12.py'))

if __name__=='__main__':unittest.main()
