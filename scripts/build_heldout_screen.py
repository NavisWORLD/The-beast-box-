"""Build apps/beastbox-cloud/lib/zeref/heldout-screen.json: a HASHED view of every held-out gate item, for the
self-memory fail-closed screen. Read only: it imports nothing that trains and edits no gate, eval or threshold.

Sources (read as literals, no torch import): scripts/rawrphos_chat_eval.py PAIRS + CHAT (set A + chat),
scripts/zeref_heldout_b.py PAIRS_B (set B), scripts/zeref_gate_sets_v2.json (set_a_added, set_b_added, chat_added).
No held-out text is written: only sha256 prefixes of normalised prompts/answers and of their word bigrams.
"""
from __future__ import annotations
import ast, hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps/beastbox-cloud/lib/zeref/heldout-screen.json"


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def bigrams(n: str) -> list[str]:
    w = n.split(); return sorted({h(w[i] + " " + w[i + 1]) for i in range(len(w) - 1)})


def literal(path: Path, name: str):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit(f"{name} not found in {path}")


def items() -> list[tuple[str, str | None]]:
    out = [(p, a) for p, a in literal(ROOT / "scripts/rawrphos_chat_eval.py", "PAIRS")]
    out += [(p, None) for p in literal(ROOT / "scripts/rawrphos_chat_eval.py", "CHAT")]
    out += [(p, a) for p, a in literal(ROOT / "scripts/zeref_heldout_b.py", "PAIRS_B")]
    v2 = json.loads((ROOT / "scripts/zeref_gate_sets_v2.json").read_text())
    for k in ("set_a_added", "set_b_added", "chat_added"):
        out += [(r["user"], r.get("assistant")) for r in v2[k]]
    return out


def build() -> dict:
    rows = []
    for p, a in items():
        np_ = norm(p); na = norm(a) if isinstance(a, str) else ""
        rows.append({"p": h(np_), "a": h(na) if len(na.split()) >= 3 else None, "pb": bigrams(np_)})
    rows.sort(key=lambda r: (r["p"], r["a"] or ""))
    return {"schema": "zeref-heldout-screen/v1", "items": len(rows),
            "label": "Hashed held-out gate items (sha256[:16] of normalised text and word bigrams). No held-out text.",
            "sources": ["scripts/rawrphos_chat_eval.py:PAIRS,CHAT", "scripts/zeref_heldout_b.py:PAIRS_B",
                        "scripts/zeref_gate_sets_v2.json:set_a_added,set_b_added,chat_added"],
            "rows": rows}


if __name__ == "__main__":
    text = json.dumps(build(), separators=(",", ":"), sort_keys=True) + "\n"
    if "--check" in sys.argv:
        sys.exit(0 if OUT.read_text() == text else "heldout-screen.json is stale: run scripts/build_heldout_screen.py")
    OUT.write_text(text); print(OUT, len(text))
