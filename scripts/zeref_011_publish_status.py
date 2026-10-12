#!/usr/bin/env python3
"""report.json (Experiment 011) -> apps/beastbox-cloud/public/spark/zeref-learning/status.json.
Copies measured numbers only; never edits or rounds results into claims."""
import json, sys
from pathlib import Path
rep = json.loads(Path(sys.argv[1]).read_text()); run_url = sys.argv[2] if len(sys.argv) > 2 else None
out = Path(sys.argv[3] if len(sys.argv) > 3 else "apps/beastbox-cloud/public/spark/zeref-learning/status.json")
R = rep["results"]
arm = lambda r: {"cells_visited": r["pocket"]["mean"]["cells_visited"], "blocked": r["pocket"]["mean"]["blocked"], "legal": r["pocket"]["legal_action_rate"]}
base = lambda k: {"cells_visited": R["baselines"][k]["mean"]["cells_visited"], "blocked": R["baselines"][k]["mean"]["blocked"]}
failed = [k for k, v in rep["gates"].items() if not v]
st = {"schema": "zeref-learning-status/v1", "experiment": "011", "qbeast_id": rep["qbeast_id"], "run_url": run_url,
      "parent_sha256": rep["parent_checkpoint_sha256"], "candidate_sha256": rep["candidate_checkpoint_sha256"], "accepted": rep["accepted"],
      "status": "accepted research descendant (not promoted to production)" if rep["accepted"] else "candidate REJECTED by predeclared gates; approved parent kept",
      "eval": {"layouts": rep["protocol"]["eval_layouts"], "random": base("random"), "pocket_learner": base("pocket-learner"),
               "greedy_frontier": base("greedy-frontier"), "parent": arm(R["neural"]["parent"]),
               "candidate_seeds": [arm(r) for r in R["neural"].get("candidate", [])],
               "no_memory_seeds": [arm(r) for r in R["neural"].get("no-memory", [])],
               "shuffled_seeds": [arm(r) for r in R["neural"].get("shuffled", [])]},
      "native": {"parent": f"{R['neural']['parent']['native']['legal']}/14 legal, {R['neural']['parent']['native']['teacher_matches']} teacher matches",
                 "candidate": (lambda c: f"{c['legal']}/14 legal, {c['teacher_matches']} teacher matches")(R["neural"]["candidate"][0]["native"]) if R["neural"].get("candidate") else None},
      "failed_gates": failed,
      "identity_note": "The neural model belongs to bb-deada969. The Moonwraith display id bb-7f9c2a03 is not associated with it (unverified), so neural results do not drive the Moonwraith rig.",
      "honesty": "Pocket results come from a deterministic simulation, not game progress. Native targets are a scripted teacher. No quantum training, no new IBM jobs."}
out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n"); print(out)
