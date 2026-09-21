"""Regression gates for the new sensor-rich sandbox, without host authority."""
import copy
import json
import pathlib
import sys
import unittest

HERE=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import numpy as np
import sandbox_sensors as sns
import run_sensor_quest as q


class TestSensorQuest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=q.load_graph()

    def test_camera_pixels_not_reward_or_station_oracle(self):
        pos=(0,-2.2);stations=((-2.6,1.6),(2.6,1.6))
        a=sns.camera(pos,0.,stations)
        b=sns.camera(pos,0.,stations)
        self.assertTrue(np.array_equal(a,b))
        self.assertEqual(a.shape,(64,96,3))
        read=sns.interpret_camera(a)
        self.assertEqual(len(read),2)
        self.assertTrue(all(isinstance(v['seen'],bool) for v in read))

    def test_reward_label_does_not_feed_sensing_movement(self):
        t=next(q.trial_plan(4,(1,1,1)))
        W,_=q.incoming_matrix(self.data,'published_subset',4)
        a=q.run_episode(self.data,W,t,0,trace=True,max_ticks=36)
        b=q.run_episode(self.data,W,dict(t,rewarded_station=1-t['rewarded_station']),0,trace=True,max_ticks=36)
        self.assertEqual(a['trace'],b['trace'])
        self.assertEqual(a['arrived'],b['arrived'])
        # Only the terminal reward can depend on the concealed food assignment.
        self.assertNotIn('rewarded_station',a['trace'][0])

    def test_visual_fov_and_occlusion(self):
        target=(-1.2,-2.)
        obs=sns.interpret_camera(sns.camera((-2.4,-2.),0.,(target,(-3.6,-2.))))
        self.assertTrue(obs[0]['seen'])
        self.assertFalse(obs[1]['seen'])
        visible,_,_=sns.in_view((0,0),0,(1.5,0),((.7,0,.4),))
        self.assertFalse(visible)

    def test_touch_from_geometry(self):
        self.assertTrue(sns.collision((-.65,-.5),(-.65,0.3)))
        self.assertFalse(sns.collision((-3.0,-2.0),(-2.8,-2.0)))
        self.assertTrue(sns.collision((-3.75,-2.0),(-4.2,-2.0)))

    def test_deterministic_new_task(self):
        a=q.run_arm(self.data,'real_wiring_learning',2,counts=(3,2,2),trace=True)
        b=q.run_arm(self.data,'real_wiring_learning',2,counts=(3,2,2),trace=True)
        self.assertEqual(a,b)
        self.assertEqual(len(a['episodes']),7)
        self.assertTrue(all(len(p['neural'])==42 and len(p['dyn12'])==12 for e in a['episodes'] for p in e['trace']))

    def test_wiring_control_and_memory_ablation(self):
        a,_=q.incoming_matrix(self.data,'published_subset',0)
        b,_=q.incoming_matrix(self.data,'weight_matched_rewire',0)
        c,_=q.incoming_matrix(self.data,'no_propagation',0)
        self.assertFalse(np.array_equal(a,b))
        self.assertTrue(np.all(c==0))
        run=q.run_arm(self.data,'no_learning',0,counts=(3,2,2))
        self.assertTrue(all(e['q_before']==[[.5,.5],[.5,.5]] and e['q_after']==e['q_before'] for e in run['episodes']))

    def test_rendered_camera_matches_executed_trace(self):
        p=HERE/'sensor_quest_demo'/'seed-0.jsonl'
        if not p.is_file():self.skipTest('archived run absent')
        rows=[json.loads(line) for line in p.read_text().splitlines()]
        for r in rows:
            for e in r['episodes'][:3]:
                for t in e['trace'][::max(1,len(e['trace'])//4)]:
                    pose=t['sensor_pose']
                    rgb=sns.camera(pose[:2],pose[2],e['stations'])
                    self.assertEqual(sns.interpret_camera(rgb),t['vision'])

    def test_manifest_hashes(self):
        p=HERE/'sensor_quest_demo'/'results.json'
        if not p.is_file():self.skipTest('archived run absent')
        j=json.loads(p.read_text())
        self.assertEqual(j['source_hash'],q.sha256(q.DATA))
        self.assertEqual(j['episode_log_hash'],q.sha256(p.parent/'runs.jsonl'))
        self.assertEqual(j['code_hash'],q.sha256(HERE/'run_sensor_quest.py'))
        self.assertEqual(j['sensor_code_hash'],q.sha256(HERE/'sandbox_sensors.py'))


if __name__=='__main__':unittest.main()
