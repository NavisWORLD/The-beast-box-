import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps/beastbox-cloud"


def test_public_bio_spark_is_a_fresh_numbers_only_build_of_the_evidence():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/build_bio_spark_public.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads((APP / "public/spark/zeref-bio-spark.json").read_text())
    assert d["labels"] == {"pulse": "MEASURED", "ibm": "RECORDED", "rigetti": "SIMULATED", "placement": "SEEDED"}
    ev = json.loads((ROOT / "evidence/zeref-bio-spark-001/heart-seed-v9.json").read_text())
    assert d["heart_seed_v9_sha256"] == ev["heart_seed_sha256"]
    text = json.dumps(d)
    for banned in ("envelope", "samples", "frames_b64", "audio_b64"):
        assert banned not in text


def test_loop_does_not_touch_the_pin_the_gate_or_the_growth_routine():
    # The loop only adds files; it must not be referenced from the growth routine, promotion or pin files.
    for f in ("scripts/zeref_continuation_006.py", ".github/workflows/zeref-bridge-pin-sync-check.yml", ".github/workflows/zeref-continuous-learning-006.yml"):
        t = (ROOT / f).read_text()
        assert "zeref-loop" not in t and "loop-chain" not in t, f


def test_loop_code_has_no_math_random():
    for p in (APP / "lib/loop").glob("*.mjs"):
        code = "\n".join(l for l in p.read_text().splitlines() if not l.lstrip().startswith(("*", "/*", "//")))
        assert "Math.random" not in code, p
