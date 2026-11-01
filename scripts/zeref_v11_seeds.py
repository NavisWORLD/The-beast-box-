#!/usr/bin/env python3
"""Heart seed v11 (RECORDED, real IBM ibm_marrakesh CHSH measurement, 2026-10-31) fed to GROWING Zeref only.
Each purpose gets its own seed: sha256(v11 + "|" + purpose). These seeds are RECORDED-derived: they fix data order,
init and the curiosity prompt so a run can be replayed. A seed is a number; it does not make the model quantum.
Not used by the pin, the gates, the growth routine or spark-seed.json."""
import hashlib, json, sys
from pathlib import Path
V11 = "bfc35208bb21af82c308f2fb0d882de74e5cf559756567f83bcbf9ddfa5d0322"
PURPOSES = ("data-order", "adapter-init", "curiosity")
OUT = Path(__file__).resolve().parents[1] / "evidence/zeref-growing-v11-seed/derivation.json"

def seed_hex(purpose):
    if purpose not in PURPOSES: raise ValueError(purpose)
    return hashlib.sha256(f"{V11}|{purpose}".encode()).hexdigest()

def seed_int(purpose): return int(seed_hex(purpose)[:12], 16)

def derivation():
    return {"schema": "zeref-growing-v11-seed/v1", "label": "RECORDED-derived",
            "source": {"heart_seed_v11_sha256": V11, "evidence": "evidence/zeref-heart-seed-v11", "label": "RECORDED"},
            "rule": "seed_hex = sha256(v11 + '|' + purpose); seed_int = int(seed_hex[:12], 16)",
            "applies_to": "growing Zeref only (scripts/zeref_growing.py, scripts/zeref_chooses.py); never the pin, gates, growth routine or spark-seed.json",
            "honesty": "A deterministic number from a recorded measurement. It makes training replayable; it does not make Zeref quantum.",
            "seeds": {p: {"sha256": seed_hex(p), "int": seed_int(p),
                          "use": {"data-order": "torch.Generator for which lesson rows are drawn, in what order",
                                  "adapter-init": "torch.manual_seed before training: init of any new adapter and dropout (no adapter exists yet)",
                                  "curiosity": "seed shown in the curiosity prompt sent to the growing mind (the bridge samples the reply itself)"}[p]}
                      for p in PURPOSES}}

if __name__ == "__main__":
    s = json.dumps(derivation(), indent=1, sort_keys=True) + "\n"
    if "--check" in sys.argv: sys.exit(0 if OUT.is_file() and OUT.read_text() == s else "derivation.json is stale")
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(s); print(OUT)
