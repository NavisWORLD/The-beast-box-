#!/usr/bin/env python3
"""Zeref public-promotion predicate (the "training gate" Cory loosened on 2026-11-12).

Owner decision, recorded verbatim (Thu 2026-11-12, 2:37 PM CT, Cory / NavisWORLD):
  "lol losten the gate up haha ... he's going be who he's gonna be lol"
  then, asked which gate: "Loosen both the training gate and the chat door"

What changed (and what did not):
- STRICT_2026_10_22 (old, kept intact below for a one-line revert):
    promote = chat_not_worse_vs_14000 AND set-A ref_nll <= pin_bar * (1 + 0.005)
  where chat_not_worse_vs_14000 = ref_nll not worse AND ok_replies not fewer AND
  game-action leaks not more, all versus the public 14000 baseline.
- LOOSE_2026_11_12 (new default):
    promote = set-A ref_nll <= pin_bar + 0.02 nats AND candidate game-action leaks == 0
  chat_not_worse is still computed and printed on every candidate; it no longer blocks.
- The leak screen stays HARD: it is an integrity check (game-key words leaking into chat
  replies), not a quality bar.
- Why 0.02 nats: the training gate already documents seed-to-seed noise on set A of about
  0.03 nats; the pin bar sits near 3.6 nats, so the old 0.5% relative tolerance was ~0.018
  nats. 0.02 nats keeps a promoted candidate inside the measured noise band of the pin
  (statistically indistinguishable, never clearly worse) while no longer letting a
  14000-baseline ok-reply count veto a candidate.
- Unchanged: eval sets, the pin re-score in every run (the bar), the training guard in
  scripts/zeref_continuation_006.py, the pin file (moves only through promotion), G1-G10,
  the fair gate, and the requirement that a candidate is a gate-approved release.

Revert in one line: set PROMOTION_RULE = STRICT_2026_10_22.
"""
from __future__ import annotations

import json
import math
import sys

STRICT_2026_10_22 = "strict-2026-10-22"
LOOSE_2026_11_12 = "loose-2026-11-12"
PROMOTION_RULE = LOOSE_2026_11_12  # one-line revert: PROMOTION_RULE = STRICT_2026_10_22

STRICT_RELATIVE_TOLERANCE = 0.005
LOOSE_NLL_TOLERANCE_NATS = 0.02

OWNER_DECISION = {
    "by": "Cory (NavisWORLD)",
    "at": "2026-11-12T14:37:00-06:00",
    "words": "Loosen both the training gate and the chat door",
    "context": "lol losten the gate up haha ... he's going be who he's gonna be lol",
}

RULE_TEXT = {
    STRICT_2026_10_22: "within 0.5% of pin on set A AND chat_not_worse vs 14000 AND fresh held-out set B not worse (training gate)",
    LOOSE_2026_11_12: "set A ref_nll not worse than the re-scored pin by more than 0.02 nats AND candidate game-action leaks == 0 (hard); chat_not_worse vs 14000 report-only; fresh held-out set B still in the training gate",
}


def pin_bar(pin: dict, report: dict, ev: dict) -> float:
    """The bar is the pin re-scored in THIS run by the training gate (unchanged since Gate v2)."""
    g = (report or {}).get("recipe") or {}
    return g.get("chat_before_nll") or ((pin or {}).get("promotion") or {}).get("candidate_ref_nll") or ev["baseline"]["ref_nll"]


def decide(ev: dict, bar: float, rule: str = None) -> dict:
    rule = PROMOTION_RULE if rule is None else rule
    c = ev["candidate"]["ref_nll"]
    leaks = ev["candidate"].get("action_leaks")
    chat_not_worse = bool(ev.get("chat_not_worse"))
    if not isinstance(c, (int, float)) or not math.isfinite(c) or not isinstance(bar, (int, float)) or not math.isfinite(bar):
        raise ValueError("ref_nll or bar is not a finite number")
    if rule == STRICT_2026_10_22:
        tol = STRICT_RELATIVE_TOLERANCE
        nll_ok = c <= bar * (1 + tol)
        leaks_ok = True  # inside chat_not_worse (not more than 14000)
        ok = bool(chat_not_worse and nll_ok)
        tolerance = {"relative": tol}
    elif rule == LOOSE_2026_11_12:
        nll_ok = c <= bar + LOOSE_NLL_TOLERANCE_NATS
        leaks_ok = type(leaks) is int and leaks == 0
        ok = bool(nll_ok and leaks_ok)
        tolerance = {"absolute_nats": LOOSE_NLL_TOLERANCE_NATS}
    else:
        raise ValueError(f"unknown promotion rule {rule!r}")
    return {
        "schema": "zeref-promotion-decision-v2",
        "promotion_rule": rule,
        "rule": RULE_TEXT[rule],
        "candidate_ref_nll": c,
        "pin_ref_nll_bar": bar,
        "delta_vs_pin_nats": c - bar,
        "tolerance": tolerance,
        "nll_within_tolerance": bool(nll_ok),
        "candidate_action_leaks": leaks,
        "leak_screen_hard_zero": bool(leaks_ok) if rule == LOOSE_2026_11_12 else None,
        "chat_not_worse_vs_14000": chat_not_worse,
        "chat_not_worse_blocking": rule == STRICT_2026_10_22,
        "chat_gate_detail_report_only": ev.get("gate"),
        "owner_decision": OWNER_DECISION if rule == LOOSE_2026_11_12 else None,
        "promote": ok,
    }


def main(argv: list[str]) -> int:
    """zeref_promotion_rule.py PIN_JSON REPORT_JSON CHAT_EVAL_JSON OUT_JSON [extra-json]"""
    pin_p, rep_p, ev_p, out_p = argv[:4]
    extra = json.loads(argv[4]) if len(argv) > 4 else {}
    pin = json.load(open(pin_p))
    rep = json.load(open(rep_p))
    ev = json.load(open(ev_p))
    d = decide(ev, pin_bar(pin, rep, ev))
    d.update(extra)
    json.dump(d, open(out_p, "w"), indent=1)
    key = "ZEREF_RECOVERY_PROMOTION_DECISION=" if d.get("report_only") else "ZEREF_PROMOTION_DECISION="
    print(key + json.dumps(d), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
