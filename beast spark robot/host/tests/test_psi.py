"""Optional psi layer: off by default, DERIVED, never changes state or hardware commands."""
import itertools
import math

from spark_brain.brain import SparkBrain
from spark_brain.psi import PHI, PsiLayer, SOURCE
from spark_brain import simulate

NOW = 1_800_000_000.0


def _run(tmp_path, psi):
    c = itertools.count()
    b = SparkBrain(tmp_path, clock=lambda: NOW + next(c) * 0.25, psi=psi)
    b.bridge.sim_drive = True
    outs = []
    for f in simulate.frames(8):
        b.on_frame(f)
        outs.append(b.tick())
    return outs


def test_off_by_default(tmp_path):
    step, _ = _run(tmp_path, False)[-1]
    assert "psi" not in step


def test_psi_does_not_drive_anything(tmp_path):
    off = _run(tmp_path / "a", False)
    on = _run(tmp_path / "b", True)
    for (s0, c0), (s1, c1) in zip(off, on):
        assert c0 == c1                                  # identical LED / tone commands
        assert s0["state_sha256"] == s1["state_sha256"]  # identical Beast Box state
    p = on[-1][0]["psi"]
    assert p["drives_hardware"] is False and p["label"].startswith("DERIVED")
    assert "ver.4.20 README.md:78" in p["source"] == SOURCE


def test_terms_match_formula():
    L = PsiLayer()
    x0, x1 = [0.0] * 12, [0.1] * 12
    d12 = [0.0] * 10 + [0.5, 0.0]
    L.update(x0, d12, [True] * 12)
    r = L.update(x1, d12, [True] * 12)
    ec = 0.01
    assert math.isclose(r["terms"]["phi_energy"], PHI * ec)
    assert math.isclose(r["terms"]["path"], math.sqrt(12 * 0.01))
    assert math.isclose(r["terms"]["omega_energy"], 0.75 * ec)
    assert r["terms"]["u_grav"] == 0.0
    assert math.isclose(r["psi"], sum(r["terms"].values()))
    masked = PsiLayer().update(x1, d12, [True] * 10 + [False, True])
    assert masked["omega"] == 0.0                        # masked D11 contributes nothing
