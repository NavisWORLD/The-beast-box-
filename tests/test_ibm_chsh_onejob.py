import math, sys, unittest
sys.path.insert(0, "scripts")
import ibm_chsh_onejob as M

def ideal(a, b, n=100000):
    E = math.cos(a - b); p = (1 + E) / 2
    return {"00": round(n * p / 2), "11": round(n * p / 2), "01": round(n * (1 - p) / 2), "10": round(n * (1 - p) / 2)}

class T(unittest.TestCase):
    def test_ideal_tsirelson(self):
        d = {f"{a}{b}": ideal(M.A[a], M.B[b]) for a, b in M.SETTINGS}
        self.assertAlmostEqual(M.chsh(d)["S"], 2 * math.sqrt(2), places=3)
    def test_local_bound(self):
        d = {k: {"00": 50, "11": 50, "01": 0, "10": 0} for k in ["a0b0", "a0b1", "a1b0"]}
        d["a1b1"] = {"00": 50, "11": 50, "01": 0, "10": 0}
        self.assertAlmostEqual(M.chsh(d)["S"], 2.0)
    def test_one_job_settings(self):
        self.assertEqual(len(M.SETTINGS), 4); self.assertLessEqual(M.SHOTS * 4, 8192); self.assertLessEqual(M.QPU_CAP, 60)
if __name__ == "__main__": unittest.main()
