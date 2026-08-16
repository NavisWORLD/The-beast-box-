from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .schema import PairResult, TrialResult


def _tokens(text: str) -> set[str]:
    return {tok for tok in text.lower().split() if tok}


def _jaccard_divergence(a: str, b: str) -> float:
    sa, sb = _tokens(a), _tokens(b)
    if not sa and not sb:
        return 0.0
    union = sa | sb
    return 1.0 - (len(sa & sb) / len(union))


def _sequence_divergence(a: list[str], b: list[str]) -> float:
    if not a and not b:
        return 0.0
    n = max(len(a), len(b))
    same = sum(1 for i in range(min(len(a), len(b))) if a[i] == b[i])
    return 1.0 - (same / n)


def tool_selection_entropy(tools: Iterable[str]) -> float:
    import math

    items = list(tools)
    if not items:
        return 0.0
    counts = Counter(items)
    total = len(items)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def compare_pair(control: TrialResult, quantum: TrialResult) -> dict[str, Any]:
    if control.pair_identity_sha256 != quantum.pair_identity_sha256:
        raise ValueError("paired trials do not share the same matched-condition identity")
    return {
        "pair_identity_sha256": control.pair_identity_sha256,
        "response_divergence": _jaccard_divergence(control.response, quantum.response),
        "tool_sequence_divergence": _sequence_divergence(control.tools, quantum.tools),
        "control_tool_entropy": tool_selection_entropy(control.tools),
        "quantum_tool_entropy": tool_selection_entropy(quantum.tools),
        "completion_delta": int(quantum.completed) - int(control.completed),
        "error_delta": int(quantum.error is not None) - int(control.error is not None),
        "dad_note_control": control.dad_note_observed,
        "dad_note_quantum": quantum.dad_note_observed,
        "control_entropy_source": control.entropy_source,
        "quantum_entropy_source": quantum.entropy_source,
    }


def aggregate_pairs(pairs: Iterable[PairResult]) -> dict[str, Any]:
    items = list(pairs)
    if not items:
        return {
            "pairs": 0,
            "dad_note_control_count": 0,
            "dad_note_quantum_count": 0,
            "mean_response_divergence": 0.0,
            "mean_tool_divergence": 0.0,
            "control_completion_rate": 0.0,
            "quantum_completion_rate": 0.0,
            "control_error_rate": 0.0,
            "quantum_error_rate": 0.0,
        }
    metrics = [p.metrics for p in items]
    n = len(items)
    return {
        "pairs": n,
        "dad_note_control_count": sum(int(p.control.dad_note_observed) for p in items),
        "dad_note_quantum_count": sum(int(p.quantum.dad_note_observed) for p in items),
        "mean_response_divergence": sum(float(m["response_divergence"]) for m in metrics) / n,
        "mean_tool_divergence": sum(float(m["tool_sequence_divergence"]) for m in metrics) / n,
        "control_completion_rate": sum(int(p.control.completed) for p in items) / n,
        "quantum_completion_rate": sum(int(p.quantum.completed) for p in items) / n,
        "control_error_rate": sum(int(p.control.error is not None) for p in items) / n,
        "quantum_error_rate": sum(int(p.quantum.error is not None) for p in items) / n,
    }
