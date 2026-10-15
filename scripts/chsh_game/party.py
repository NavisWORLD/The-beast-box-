#!/usr/bin/env python3
"""One isolated half (Alice or Bob) of the CHSH game (Bell nonlocality).

Run as its OWN process. It reads and writes only inside its own directory:
  commit : draws fresh random questions from os.urandom, keeps them private, publishes only sha256(salt||questions)
  answer : reads ONLY its own measured outcome bits (dropped into its inbox by the referee) and answers
It never sees the other half's questions, outcomes or answers. Strategies:
  quantum   -> answer = own live measurement outcome (the measurement basis was set by its own question)
  classical -> optimal deterministic local strategy (always answer 0); best possible classical win rate is 75%
"""
import hashlib, json, os, secrets, sys
from pathlib import Path

def commit(d: Path, n: int):
    q = [b & 1 for b in os.urandom(n)]
    salt = secrets.token_hex(32)
    blob = salt + ":" + "".join(map(str, q))
    d.mkdir(parents=True, exist_ok=True)
    (d / "private_questions.json").write_text(json.dumps({"salt": salt, "questions": q}))
    h = hashlib.sha256(blob.encode()).hexdigest()
    (d / "commitment.txt").write_text(h + "\n")
    print(h)

def answer(d: Path, strategy: str):
    q = json.loads((d / "private_questions.json").read_text())["questions"]
    if strategy == "quantum":
        out = json.loads((d / "inbox_outcomes.json").read_text())["outcomes"]
        if len(out) != len(q): raise SystemExit("outcome length mismatch")
        ans = [int(o) for o in out]
    elif strategy == "classical":
        ans = [0] * len(q)
    else: raise SystemExit("unknown strategy")
    (d / f"answers_{strategy}.json").write_text(json.dumps({"answers": ans}))

if __name__ == "__main__":
    cmd, d = sys.argv[1], Path(sys.argv[2])
    commit(d, int(sys.argv[3])) if cmd == "commit" else answer(d, sys.argv[3])
