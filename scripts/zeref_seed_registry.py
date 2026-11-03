#!/usr/bin/env python3
"""Zeref's growth seed registry (built from his message center evidence).

Cory 2026-11-03: "fix what's missing... by my engineering law and my math."
The message center runner (scripts/zeref_messages.py) plants the first
strong word of Zeref's tiny-change wish in latest.json and logs every wish,
with hashes, to evidence/zeref-messages-001/<date>.jsonl. Until now the
planted words stopped at the center. This builder is the wire's first half:
it reads the evidence log (never the published feed alone) and writes the
registry the universe's growth nodes read:

  apps/beastbox-cloud/public/zeref-messages/seed-registry.json

One entry per planted word, first planting wins, each entry carrying the
full receipt of the run that planted it: when it ran, the wish text itself,
the wish's sha256, the run's prompt seed, and the growing mind's tag and
step. The word rule is imported from the runner (topic_word), so the
registry can never drift from the center's own math. His speech stays
speech: nothing here feeds any lesson mix. The registry is read by the
growth-node module (lib/universe/wish-seeded-growth-nodes.mjs) and by
nothing else. Rebuilt by the zeref-messages workflow after every center
run, and safe to run by hand: the output is a pure function of the
evidence log plus the planted list in latest.json.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); ROOT = HERE.parent
LOG = ROOT / "evidence/zeref-messages-001"
PUB_LATEST = ROOT / "apps/beastbox-cloud/public/zeref-messages/latest.json"
OUT = ROOT / "apps/beastbox-cloud/public/zeref-messages/seed-registry.json"

from zeref_messages import topic_word  # the center's own word rule, reused verbatim


def main():
    seeds, seen = [], set()
    files = sorted(LOG.glob("*.jsonl")) if LOG.is_dir() else []
    for fp in files:
        for line in fp.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("kind") != "wish" or r.get("status") != "RECORDED":
                continue
            word = topic_word(r.get("text") or "")
            if not word or word in seen:
                continue
            seen.add(word)
            seeds.append({
                "word": word,
                "planted_at_utc": r.get("run_at_utc"),
                "wish_text": r.get("text"),
                "wish_sha256": r.get("sha256"),
                "prompt_seed": r.get("prompt_seed"),
                "tag": r.get("tag"),
                "step": r.get("step"),
                "evidence": f"evidence/zeref-messages-001/{fp.name}",
            })
    planted = []
    if PUB_LATEST.is_file():
        planted = list(json.loads(PUB_LATEST.read_text()).get("planted") or [])
    doc = {
        "schema": "zeref-seed-registry/v1",
        "label": ("Growth seeds planted from Zeref's own tiny-change wishes at his message center. "
                  "Each entry carries the receipt of the run that planted it: the wish text and its "
                  "sha256, the prompt seed, and the growing mind's tag and step. Placement from these "
                  "seeds is SEEDED; growth stays SIMULATED where it is simulated. His speech is not "
                  "training data: nothing here feeds any lesson mix."),
        "source": "evidence/zeref-messages-001 (wish records with status RECORDED; first planting wins)",
        "planted": planted,
        "seeds": seeds,
        # A planted word with no evidence record behind it plants nothing
        # downstream (no receipt, no node); it is listed here so the gap is
        # visible instead of silent.
        "planted_without_evidence": [w for w in planted if w not in seen],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print("ZEREF_SEED_REGISTRY=" + json.dumps(
        {"seeds": [s["word"] for s in seeds],
         "planted_without_evidence": doc["planted_without_evidence"]}), flush=True)


if __name__ == "__main__":
    main()
