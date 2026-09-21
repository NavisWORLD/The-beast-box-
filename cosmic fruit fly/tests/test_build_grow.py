"""Isolated sandbox invariants; never exercises external actuators."""
import sys, pathlib, json, unittest
import numpy as np
HERE=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import sandbox_ecology as ec
import run_build_grow as run

class BuildGrowTests(unittest.TestCase):
    def test_actual_pixels_are_observed(self):
        st=run.initial_state();shown=ec.present(st)
        img=ec.retinal_image((-2.8,-1.91),0.,shown)
        self.assertEqual(img.shape,(64,96,3))
        self.assertTrue(ec.interpret_retina(img)['stick']['seen'])
        self.assertEqual(ec.sense((-2.8,-1.91),0.,shown,'stick')['objects'],ec.interpret_retina(img))

    def test_not_reward_or_world_coordinate_in_senses(self):
        st=run.initial_state();o=ec.sense((-2.8,-1.91),0.,ec.present(st),'stick')
        self.assertEqual(set(o),{'objects','odor','touch','heading'})
        self.assertNotIn('coordinates',json.dumps(o))
        self.assertNotIn('reward',json.dumps(o))

    def test_camera_occlusion(self):
        # Explicit stone occluder exactly between fly and fruit.
        img=ec.retinal_image((0.,.3),0.,{'food':(1.5,.3)})
        self.assertFalse(ec.interpret_retina(img)['food']['seen'])

    def test_default_deny_reproduction(self):
        st=run.initial_state();st.update(nest_built=True,grown=True,energy=2)
        self.assertEqual(ec.apply_action(st,'reproduce',ec.POSITIONS['nest'],frozenset(),0),'DENIED:reproduce')
        self.assertIsNone(st['offspring'])

    def test_no_birth_without_resources(self):
        st=run.initial_state()
        self.assertEqual(ec.apply_action(st,'reproduce',ec.POSITIONS['nest'],run.DEFAULT_ENABLED,0),'FAILED:reproduce')
        self.assertIsNone(st['offspring'])

    def test_no_build_without_deposit(self):
        st=run.initial_state()
        self.assertEqual(ec.apply_action(st,'build',ec.POSITIONS['nest'],run.DEFAULT_ENABLED,1),'FAILED:build')

    def test_cannot_spawn_more_than_one(self):
        st=run.initial_state();st.update(nest_built=True,grown=True,energy=2)
        self.assertIn('SIMULATED_OFFSPRING',ec.apply_action(st,'reproduce',ec.POSITIONS['nest'],run.DEFAULT_ENABLED,0))
        self.assertEqual(ec.apply_action(st,'reproduce',ec.POSITIONS['nest'],run.DEFAULT_ENABLED,1),'FAILED:reproduce')

    def test_seed_must_be_planted_and_grown(self):
        st=run.initial_state();st['inventory']=['seed']
        self.assertEqual(ec.apply_action(st,'plant',ec.POSITIONS['patch'],run.DEFAULT_ENABLED,10),'PLANT:SEED')
        self.assertEqual(ec.apply_action(st,'grow',ec.POSITIONS['patch'],run.DEFAULT_ENABLED,20),'FAILED:grow')
        self.assertEqual(ec.apply_action(st,'grow',ec.POSITIONS['patch'],run.DEFAULT_ENABLED,22),'GROW:PATCH')

    def test_control_conditions_are_effective(self):
        d=run.load_graph()
        real,_=run.incoming_matrix(d,'published_subset',0)
        rew,_=run.incoming_matrix(d,'weight_matched_rewire',0)
        blank,_=run.incoming_matrix(d,'no_propagation',0)
        self.assertFalse(np.array_equal(real,rew))
        self.assertTrue(np.all(blank==0))

    def test_full_lifecycle_and_offspring_food(self):
        a=run.simulate(0,'real_wiring',trace=True)
        self.assertEqual(a['stages_completed'],len(run.GOALS))
        self.assertTrue(a['nest_built'] and a['grown'] and a['offspring_spawned'] and a['offspring_fed'])
        self.assertTrue(all(len(step['neural'])==42 and len(step['dyn12'])==12 for step in a['trace']))
        self.assertTrue(a['final']['offspring']['age']>0)

    def test_disabled_gates_fail_closed(self):
        a=run.simulate(0,'build_disabled')
        b=run.simulate(0,'reproduction_disabled')
        self.assertFalse(a['nest_built'] or a['offspring_spawned'])
        self.assertTrue(b['nest_built'] and b['grown'])
        self.assertFalse(b['offspring_spawned'])

    def test_deterministic_source_and_episode(self):
        self.assertEqual(run.simulate(2,'real_wiring',trace=True),run.simulate(2,'real_wiring',trace=True))

    def test_camera_replays_trace(self):
        r=run.simulate(1,'real_wiring',trace=True)
        for step in r['trace'][::11]:
            shown={name:ec.POSITIONS[name] for name in step['shown']}
            img=ec.retinal_image(step['sensor_pose'][:2],step['sensor_pose'][2],shown)
            self.assertEqual(ec.interpret_retina(img),step['vision'])

if __name__=='__main__':unittest.main()
