"""Small contract tests of the collision risk head; actual outcomes tested in Actions."""
import importlib.util
import sys
import unittest
from pathlib import Path

if importlib.util.find_spec("rawrphos") is None or importlib.util.find_spec("torch") is None:
    raise unittest.SkipTest("Dedicated 012E CPU Actions workflow installs native model dependencies")
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import zeref_012e_collision_head as X

def observation():
    return {"row":2,"col":3,"step":9,"steps_left":31,"cells_visited":7,
            "known_rifts":2,"visits_here":1,"frontier":"RIGHT",
            "neighbors":{"UP":{"kind":"wall"},
                         "DOWN":{"kind":"rift-known"},
                         "LEFT":{"kind":"open","visits":3,"poi":None},
                         "RIGHT":{"kind":"open","visits":0,"poi":"plasma"}}}

class CollisionHeadContracts(unittest.TestCase):
    def test_no_oracle_only_visible_state(self):
        s=X.vector(observation(),"RIGHT")
        self.assertEqual(len(s),18)
        self.assertTrue(all(0<=v<=1 for v in s))
        with self.assertRaises(ValueError):
            X.vector(observation(),"UP")
        with self.assertRaises(ValueError):
            X.vector({}, "RIGHT")

    def test_torch_deterministic_safety_head(self):
        features=X.vector(observation(),"RIGHT")
        train=[(features,1) for _ in range(32)]
        lower=observation()
        lower["row"]=0
        other=X.vector(lower,"LEFT")
        train.extend((other,0) for _ in range(32))
        a,trace=X.train_head(train,123,16)
        b,_=X.train_head(train,123,16)
        self.assertTrue(trace)
        self.assertEqual(X.predict(a,[features,other]),X.predict(b,[features,other]))
        self.assertEqual(len(X.predict(a,[features,other])),2)

    def test_selection_uses_only_observation(self):
        state=observation()
        self.assertEqual(X.pick_action(state,None,0),"RIGHT")
        closed={**state,"neighbors":{k:{"kind":"wall"} for k in X.MOVES}}
        self.assertEqual(X.pick_action(closed,None,0),"WAIT")

if __name__=="__main__":
    unittest.main()
