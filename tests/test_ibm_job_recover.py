import importlib.util, json, math, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ibm_job_recover", ROOT / "scripts/ibm_job_recover.py")
rec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rec)


def test_score_matches_referee_rule():
    x = [0, 0, 1, 1]; y = [0, 1, 0, 1]
    # win = (a xor b) == (x and y)
    assert rec.score(x, y, [0, 0, 0, 0], [0, 0, 0, 1])["wins"] == 4
    assert rec.score(x, y, [0, 0, 0, 0], [0, 0, 0, 0])["wins"] == 3


def test_build_result_shape_and_privacy():
    bits = ["00", "01", "10", "11"]
    r = rec.build_result("jobx", "ibm_test", "t", bits, [0, 0, 1, 1], [0, 1, 0, 1], 7.0, {"alice_sha256": "a" * 64})
    assert r["source_class"] == "RECORDED_IBM_HARDWARE" and r["commitments_verified"] is False
    assert sum(r["counts"].values()) == 4 and len(r["counts_sha256"]) == 64
    assert "questions" not in r and "outcomes" not in r and "alice_salt" not in json.dumps(r)
    with pytest.raises(ValueError):
        rec.build_result("j", "b", "t", ["00"], [0, 1], [0, 1], 1.0)


def test_questions_round_trip_through_a_real_pub():
    pytest.importorskip("qiskit")
    import numpy as np
    from qiskit.primitives import StatevectorSampler
    sys.path.insert(0, str(ROOT))
    spec2 = importlib.util.spec_from_file_location("referee", ROOT / "scripts/chsh_game/referee.py")
    ref = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(ref)
    x = [0, 1, 1, 0, 1, 0, 0, 1] * 100
    y = [1, 1, 0, 0, 1, 0, 1, 0] * 100
    qc = ref.circuit()
    order = [p.name for p in qc.parameters]
    vals = [[{"ta": ref.A_ANG[xi], "tb": ref.B_ANG[yi]}[n] for n in order] for xi, yi in zip(x, y)]
    pub = (qc, vals)
    x2, y2 = rec.questions_from_inputs(pub)
    assert (x2, y2) == (x, y)
    res = StatevectorSampler().run([pub], shots=1).result()
    bits = res[0].data.meas.get_bitstrings()
    r = rec.build_result("jobx", "sim_only_test", "t", bits, x2, y2, None)
    assert r["quantum"]["rounds"] == 800 and r["quantum"]["win_rate"] > 0.7  # ideal 0.854, classical 0.75
    # same win rate as scoring with the referee's own function
    a = [int(b[-1]) for b in bits]; b_ = [int(b[0]) for b in bits]
    assert ref.score(x, y, a, b_)["win_rate"] == r["quantum"]["win_rate"]


def test_bad_angle_is_rejected():
    pytest.importorskip("qiskit")
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter
    ta, tb = Parameter("ta"), Parameter("tb")
    qc = QuantumCircuit(1); qc.rx(ta, 0); qc.rx(tb, 0)
    with pytest.raises(ValueError):
        rec.questions_from_inputs((qc, [[0.3, 0.1]]))
