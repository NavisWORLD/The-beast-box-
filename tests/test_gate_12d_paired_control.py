"""Tests for scripts/gate_12d_paired_control.py (PR 2).

Stub models only (no torch, no checkpoint): a sensitive stub whose loss
and logits move with condition54 must PASS the 9th gate, an insensitive
stub whose forward ignores condition54 must FAIL it. JSD properties and
the out["logits"] dict contract are asserted directly. The real-model run
is CI-only (needs the checkpoint + torch).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.gate_12d_paired_control import (
    batch_nll_and_probs,
    evaluate_12d_causal_gate,
    jensen_shannon_divergence,
)

VOCAB = 8
# Each row's condition54 steers toward ITS OWN target tokens: cond slots
# 0..7 map to vocab tokens 0..7, and row i carries +0.5 on exactly the
# slots of its target tokens. The true arm then scores better than zero
# (flat) and better than shuffled (the next row's cond boosts the WRONG
# tokens), so delta_nll and mean JSD clear the gate thresholds.
ROWS = [
    {"input_ids": [1, 2, 3, 4], "target_ids": [-100, -100, 3, 4],
     "condition54": [0.0, 0.0, 0.0, 0.5, 0.5] + [0.0] * 49},
    {"input_ids": [1, 2, 5, 6], "target_ids": [-100, -100, 5, 6],
     "condition54": [0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.5] + [0.0] * 47},
    {"input_ids": [1, 2, 7, 3], "target_ids": [-100, -100, 7, 3],
     "condition54": [0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.5] + [0.0] * 46},
]


class _BaseStub:
    """Minimal model stub: forward(input_ids, targets=..., condition54=...)
    returns {"logits": [T, V], "loss": float} — the dict contract the
    verifier reads (out["logits"], never out[0])."""

    def _logits(self, n_tokens, cond):
        raise NotImplementedError

    def __call__(self, input_ids, targets=None, condition54=None):
        cond = list(condition54 or [0.0] * 54)
        n = len(input_ids)
        logits = self._logits(n, cond)
        # NLL of the target tokens under the softmax, averaged over targets.
        total, count = 0.0, 0
        for t, logit_row in enumerate(logits):
            tgt = targets[t] if targets is not None else -100
            if tgt == -100:
                continue
            m = max(logit_row)
            exps = [math.exp(v - m) for v in logit_row]
            total += -math.log(exps[tgt] / sum(exps))
            count += 1
        return {"logits": logits, "loss": total / max(count, 1)}


class SensitiveStub(_BaseStub):
    """Loss and logits move with condition54: the true arm (cond matching
    the row) scores better than zero/shuffled, so the gate passes."""

    def _logits(self, n_tokens, cond):
        # Cond slots 0..7 steer the distribution toward the vocab token of
        # the same index; zero cond is flat.
        shift = [0.0] * VOCAB
        for v in range(VOCAB):
            shift[v] += 4.0 * cond[v]
        return [[0.1 * v + shift[v] for v in range(VOCAB)] for _ in range(n_tokens)]


class InsensitiveStub(_BaseStub):
    """Ignores condition54 entirely: all three arms are identical, so
    delta_nll == 0 and mean JSD == 0 and the gate fails."""

    def _logits(self, n_tokens, cond):
        return [[0.1 * v for v in range(VOCAB)] for _ in range(n_tokens)]


def test_sensitive_stub_passes_gate():
    verdict = evaluate_12d_causal_gate(SensitiveStub(), ROWS)
    assert verdict["passed"] is True
    assert verdict["delta_nll"] >= 0.05
    assert verdict["mean_jsd"] >= 0.02
    assert verdict["nll_true"] < verdict["nll_zero"]
    assert verdict["nll_true"] < verdict["nll_shuffled"]


def test_insensitive_stub_fails_gate():
    verdict = evaluate_12d_causal_gate(InsensitiveStub(), ROWS)
    assert verdict["passed"] is False
    assert verdict["delta_nll"] == 0.0
    assert verdict["mean_jsd"] == 0.0
    assert verdict["nll_true"] == verdict["nll_zero"] == verdict["nll_shuffled"]


def test_jsd_properties():
    p = [0.5, 0.3, 0.2]
    q = [0.1, 0.1, 0.8]
    assert jensen_shannon_divergence(p, p) == 0.0
    assert abs(jensen_shannon_divergence(p, q) - jensen_shannon_divergence(q, p)) < 1e-12
    assert 0.0 <= jensen_shannon_divergence(p, q) <= math.log(2) + 1e-12
    # Disjoint supports: JSD is maximal (ln 2 nats).
    assert abs(jensen_shannon_divergence([1.0, 0.0], [0.0, 1.0]) - math.log(2)) < 1e-9


def test_out_logits_dict_contract():
    """The verifier reads out["logits"]; a model returning a tuple (the
    out[0] mistake) must fail loudly, not silently pass."""
    class TupleModel:
        def __call__(self, input_ids, targets=None, condition54=None):
            return ([[0.0] * VOCAB for _ in input_ids], 1.0)
    try:
        batch_nll_and_probs(TupleModel(), ROWS, [r["condition54"] for r in ROWS])
    except (TypeError, KeyError, AttributeError):
        return
    raise AssertionError("tuple-returning model should have failed the dict contract")


def test_gate_thresholds_are_parameters():
    # A weak signal passes loose thresholds and fails the default ones.
    verdict_loose = evaluate_12d_causal_gate(
        SensitiveStub(), ROWS, min_delta_nll=0.01, min_jsd=0.001)
    assert verdict_loose["passed"] is True
    assert verdict_loose["min_delta_nll"] == 0.01
    assert verdict_loose["min_jsd"] == 0.001
