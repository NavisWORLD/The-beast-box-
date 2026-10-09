"""No QPU job or credential needed: prove 8 fixed Bell/CHSH circuits and controls."""
import importlib.util
import math
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("long_chsh", ROOT / "scripts" / "ibm_beast_long_chsh_probe.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def parity(probabilities):
    return sum((1 if bits.count("1") % 2 == 0 else -1) * p for bits, p in probabilities.items())


class BellChshDesignTests(unittest.TestCase):
    def test_fixed_eight_distinct_circuits_and_safe_limit(self):
        circuits = probe.circuits()
        self.assertEqual([name for name, _ in circuits], probe.EXPECTED_CIRCUITS)
        self.assertEqual(len(circuits), 8)
        self.assertEqual(probe.SHOTS_PER_CIRCUIT, 4096)
        self.assertEqual(probe.QPU_HARD_CAP, 180)
        self.assertTrue(0 < probe.QPU_HARD_CAP < 300)
        self.assertEqual(len(set(probe.EXPECTED_CIRCUITS)), 8)

    def test_ideal_bell_correlations_and_classical_control(self):
        from qiskit.quantum_info import Statevector
        raw = {}
        for name, circuit in probe.circuits():
            qc = circuit.remove_final_measurements(inplace=False)
            raw[name] = parity(Statevector.from_instruction(qc).probabilities_dict())
        for group in ("bell", "control"):
            r = {f"a{a}b{b}": raw[f"{group}_a{a}b{b}"] for a in (0, 1) for b in (0, 1)}
            s = r["a0b0"] + r["a0b1"] + r["a1b0"] - r["a1b1"]
            if group == "bell":
                self.assertAlmostEqual(s, 2 * math.sqrt(2), places=6)
            else:
                self.assertLessEqual(abs(s), 2)

if __name__ == "__main__":
    unittest.main()
