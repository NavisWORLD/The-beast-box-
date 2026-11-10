"""Python port of Cory's ppg.mjs must agree with the original JS (run under node) on the same samples."""
import json
import shutil
import subprocess

import pytest

from conftest import PKG
from spark_brain.ppg import PPG_RULES, PpgWindow, analyse_ppg
from spark_brain.simulate import synth_ppg

PPG_MJS = PKG / "ref" / "repos" / "The-beast-box-" / "apps" / "beastbox-cloud" / "lib" / "bio" / "ppg.mjs"


def _tv(seconds=30, bpm=72.0, fs=25, **kw):
    v = synth_ppg(seconds, bpm=bpm, fs=fs, **kw)
    return [i * 1000.0 / fs for i in range(len(v))], v


def test_synthetic_72bpm_is_valid_estimate():
    t, v = _tv()
    r = analyse_ppg(t, v)
    assert r["valid"] and abs(r["bpm"] - 72) < 1.5 and r["label"] == "pulse = ESTIMATE, non-medical"


def test_no_finger_and_flat_and_short_are_rejected():
    t, v = _tv(dc=20000)
    assert analyse_ppg(t, v)["reason"] == "no_finger"
    t, v = _tv(seconds=10)
    assert analyse_ppg(t, v)["reason"] == "too_short"
    t = [i * 40.0 for i in range(750)]
    assert analyse_ppg(t, [80000.0] * 750)["reason"] == "flat_signal"


def test_window_resets_on_clock_jump():
    w = PpgWindow()
    w.push({"t0": 5000, "fs": 25, "ir": [1] * 25})
    w.push({"t0": 100, "fs": 25, "ir": [2] * 25})
    assert len(w.t) == 25 and w.v[0] == 2


@pytest.mark.skipif(not shutil.which("node") or not PPG_MJS.exists(), reason="node or Cory's ppg.mjs not available")
@pytest.mark.parametrize("bpm", [55.0, 72.0, 110.0])
def test_matches_corys_javascript(bpm):
    t, v = _tv(bpm=bpm, seed=3)
    rules = {k: PPG_RULES[k] for k in PPG_RULES if k != "min_ir_dc"}
    js_rules = {**rules, "min_red": 0, "min_red_minus_green": 0}
    script = (f"import {{analysePpg}} from {json.dumps(str(PPG_MJS))};"
              f"const r=analysePpg({{t:{json.dumps(t)},v:{json.dumps(v)}}},{json.dumps(js_rules)});"
              "console.log(JSON.stringify(r));")
    js = json.loads(subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True).stdout)
    py = analyse_ppg(t, v, {**rules, "min_ir_dc": 0})
    assert py["valid"] == js["valid"]
    for k in ("bpm", "sqi", "beats", "hrv_rmssd_ms", "ibi_cv", "duration_s"):
        assert py[k] == pytest.approx(js[k], abs=1e-4), k
