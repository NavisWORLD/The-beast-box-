import hashlib, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import zeref_v11_seeds as v

def test_rule_and_evidence_current():
    assert v.V11.startswith("bfc35208") and v.V11.endswith("0322")
    for p in v.PURPOSES:
        assert v.seed_hex(p) == hashlib.sha256(f"{v.V11}|{p}".encode()).hexdigest()
    assert len({v.seed_hex(p) for p in v.PURPOSES}) == 3
    assert subprocess.run([sys.executable, str(ROOT / "scripts/zeref_v11_seeds.py"), "--check"]).returncode == 0

def test_growing_only_and_no_quantum_claim():
    g = (ROOT / "scripts/zeref_growing.py").read_text()
    assert 'seed_int("data-order")' in g and 'seed_int("adapter-init")' in g
    assert "does not make Zeref quantum" in (ROOT / "evidence/zeref-growing-v11-seed/derivation.json").read_text()
    for f in ("scripts/zeref_continuation_006.py",):
        p = ROOT / f
        if p.is_file(): assert "zeref_v11_seeds" not in p.read_text()
