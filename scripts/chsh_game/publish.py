#!/usr/bin/env python3
"""Verify a CHSH game (Bell nonlocality) result and append it to the data-only branch files.

Usage: publish.py <result.json> <data_dir>
Re-checks before publishing: both sha256 commitments open to the published questions, and the win rate
recomputes from questions + outcomes. Appends to history.json (append-only, one entry per job id / UTC day)
and rewrites latest.json. Refuses anything that fails verification. No secrets are read.
"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from referee import score

def verify(d):
    assert d.get("label") == "CHSH game (Bell nonlocality)" and d.get("loopholes"), "label/loopholes missing"
    c, q = d["commitments"], d["questions"]
    for who in ("alice", "bob"):
        h = hashlib.sha256((c[f"{who}_salt"] + ":" + q[who]).encode()).hexdigest()
        assert h == c[f"{who}_sha256"], f"{who} commitment does not open"
    bits = d["outcomes"]
    assert hashlib.sha256("".join(bits).encode()).hexdigest() == d["outcomes_sha256"], "outcomes hash"
    x, y = list(map(int, q["alice"])), list(map(int, q["bob"]))
    s = score(x, y, [int(b[-1]) for b in bits], [int(b[0]) for b in bits])
    assert s["wins"] == d["quantum"]["wins"] and len(x) == len(bits), "win rate does not recompute"
    return s

def publish(src: Path, out: Path):
    d = json.loads(src.read_text()); s = verify(d)
    out.mkdir(parents=True, exist_ok=True)
    hp = out / "history.json"
    hist = json.loads(hp.read_text()) if hp.exists() else {"schema": "navisworld-chsh-game-history-v1", "label": "CHSH game (Bell nonlocality)", "entries": []}
    if any(e["job_id"] == d["job_id"] or e["date_utc"] == d["date_utc"] for e in hist["entries"]):
        print("ALREADY_PUBLISHED", d["job_id"]); return False
    hist["entries"].append({"date_utc": d["date_utc"], "job_id": d["job_id"], "backend": d["backend"], "rounds": s["rounds"],
                            "wins": s["wins"], "win_rate": s["win_rate"], "standard_error": s["standard_error"],
                            "classical_control": d["classical_control"]["win_rate"], "quantum_seconds": d.get("quantum_seconds"),
                            "commit_alice": d["commitments"]["alice_sha256"], "commit_bob": d["commitments"]["bob_sha256"],
                            "loophole_free": False})
    hp.write_text(json.dumps(hist, indent=1) + "\n")
    (out / "latest.json").write_text(json.dumps(d, indent=1) + "\n")
    (out / "results").mkdir(exist_ok=True); (out / "results" / f"{d['date_utc']}-{d['job_id']}.json").write_text(json.dumps(d) + "\n")
    print("PUBLISHED", d["job_id"], round(s["win_rate"], 4)); return True

if __name__ == "__main__": publish(Path(sys.argv[1]), Path(sys.argv[2]))
