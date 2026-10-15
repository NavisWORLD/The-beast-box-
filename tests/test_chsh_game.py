import json, math, random, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, "scripts/chsh_game"); sys.path.insert(0, "scripts")
import referee as R

class T(unittest.TestCase):
    def test_classical_control_75(self):
        rnd = random.Random(1); n = 40000
        x = [rnd.randint(0, 1) for _ in range(n)]; y = [rnd.randint(0, 1) for _ in range(n)]
        s = R.score(x, y, [0]*n, [0]*n); self.assertAlmostEqual(s["win_rate"], .75, delta=.01)
    def test_ideal_quantum_simulated(self):
        rnd = random.Random(2); n = 40000; x, y, a, b = [], [], [], []
        for _ in range(n):
            xi, yi = rnd.randint(0, 1), rnd.randint(0, 1); E = math.cos(R.A_ANG[xi] - R.B_ANG[yi])
            ai = rnd.randint(0, 1); bi = ai if rnd.random() < (1 + E) / 2 else 1 - ai
            x.append(xi); y.append(yi); a.append(ai); b.append(bi)
        self.assertAlmostEqual(R.score(x, y, a, b)["win_rate"], R.QUANTUM_IDEAL, delta=.01)
    def test_isolated_commit_roundtrip(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "alice"; R.party("commit", d, 64); q, _, _ = R.verify_commit(d)
            (d / "inbox_outcomes.json").write_text(json.dumps({"outcomes": q})); R.party("answer", d, "quantum")
            self.assertEqual(json.loads((d / "answers_quantum.json").read_text())["answers"], q)
    def test_budget(self):
        self.assertLessEqual(R.QPU_CAP, 30); self.assertEqual(R.RESERVE, 60)
    def test_publish_verifies_and_appends_once(self):
        import publish as P
        src = Path("apps/beastbox-cloud/public/spark/chsh-game/latest.json")
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(P.publish(src, Path(t))); self.assertFalse(P.publish(src, Path(t)))
            h = json.loads((Path(t) / "history.json").read_text()); self.assertEqual(len(h["entries"]), 1)
            bad = json.loads(src.read_text()); bad["questions"]["bob"] = "1" + bad["questions"]["bob"][1:] if bad["questions"]["bob"][0] == "0" else "0" + bad["questions"]["bob"][1:]
            (Path(t) / "bad.json").write_text(json.dumps(bad))
            with self.assertRaises(AssertionError): P.publish(Path(t) / "bad.json", Path(t) / "o2")
if __name__ == "__main__": unittest.main()
