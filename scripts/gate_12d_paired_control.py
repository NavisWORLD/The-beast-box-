"""Standalone 9th-gate verifier: does condition54 causally carry signal?

evaluate_12d_causal_gate runs three arms over the same eval batches:
true condition54, zero condition54, and shuffled condition54 (rows rolled by
one). delta_nll = min(nll_zero, nll_shuf) - nll_true; the gate passes when
delta_nll >= min_delta_nll (default 0.05) and mean JSD >= min_jsd (default
0.02). These defaults match the trainer's hardcoded gate-9 values in
scripts/zeref_continuation_006.py (mouth12_gate: delta_nll_12d >= 0.05 and
mean_jsd >= 0.02); there are no env vars for them (ZEREF_12D_MIN_DELTA_NLL /
ZEREF_12D_MIN_JSD do not exist in the trainer).

Corrections to the pasted draft, verified first-hand on main (2026-11-26):
  * model.forward returns a DICT, not a tuple: use out["logits"], never
    out[0] (models/rawrphos/architecture/model.py L339).
  * The model class is RawrphosLM(config), not RawrphosModel; checkpoints
    load through rawrphos.training.checkpoint.load_checkpoint, the same
    loader Engine uses (models/rawrphos/inference/engine.py).
  * main() is not a stub: it REQUIRES a real checkpoint (--checkpoint) and
    real eval batches (--eval JSONL, or --from-gate-sets plus --chain for the
    true condition54 vectors) and writes the real measured result. There is
    no synthetic "true" arm: without real state12 vectors the run fails
    loudly instead of inventing a passing gate.

Eval batch rows: {"prompt": str, "target": str, "condition54": [54 floats]}
(or {"input_ids": [...], "target_ids": [...], "condition54": [...]} for
pre-tokenized rows). --from-gate-sets builds rows from
scripts/zeref_gate_sets_v2.json (set_a_added + set_b_added, {user, assistant})
with condition54 cycled from the world chain's recorded state12 vectors.

Pure stdlib + torch-optional: the library functions (batch_nll_and_probs,
jensen_shannon_divergence, evaluate_12d_causal_gate) work on plain lists, so
unit tests run without torch; the real-model path imports torch lazily.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DEFAULT_MIN_DELTA_NLL = 0.05
DEFAULT_MIN_JSD = 0.02


def _as_list(x):
    """Torch tensor -> list; list stays a list."""
    if hasattr(x, "tolist"):
        return x.tolist()
    return x


def _softmax(logits: list[float]) -> list[float]:
    m = max(logits)
    exps = [math.exp(v - m) for v in logits]
    total = sum(exps)
    return [e / total for e in exps]


def jensen_shannon_divergence(p: list[float], q: list[float]) -> float:
    """JSD in nats between two discrete distributions (pure Python)."""
    if len(p) != len(q):
        raise ValueError("JSD inputs must have equal length")
    total_p = sum(p)
    total_q = sum(q)
    if total_p <= 0 or total_q <= 0:
        raise ValueError("JSD inputs must be non-negative with positive mass")
    p = [v / total_p for v in p]
    q = [v / total_q for v in q]
    m = [(a + b) / 2.0 for a, b in zip(p, q)]
    def _kl(a, b):
        return sum(x * math.log(x / y) for x, y in zip(a, b) if x > 0)
    return 0.5 * _kl(p, m) + 0.5 * _kl(q, m)


def _mean_probs_over_targets(logits_seq, target_mask) -> list[float]:
    """Mean next-token distribution over target positions.

    logits_seq: [T, V] logits (one row per sequence position); target_mask:
    positions whose next-token prediction counts. Returns the mean softmax
    distribution over the masked positions.
    """
    vocab = len(logits_seq[0])
    acc = [0.0] * vocab
    count = 0
    for t, keep in enumerate(target_mask):
        if not keep or t >= len(logits_seq):
            continue
        probs = _softmax([float(v) for v in logits_seq[t]])
        for i, v in enumerate(probs):
            acc[i] += v
        count += 1
    if count == 0:
        raise ValueError("no target positions in batch row")
    return [v / count for v in acc]


def _is_torch_model(model) -> bool:
    """True when the model is a real torch nn.Module (needs tensor inputs)."""
    try:
        import torch  # noqa: F401
    except ImportError:
        return False
    return hasattr(model, "parameters") and hasattr(model, "to")


def _to_model_inputs(model, input_ids: list[int], target_ids: list[int], cond: list[float]):
    """Convert lists to the shapes the model expects.

    Real RawrphosLM: rank-2 int64 tensors with a batch dim, condition54 as a
    float32 [1, 54] tensor (forward L273-308). Stub models take plain lists.
    """
    if _is_torch_model(model):
        import torch
        return (torch.tensor([input_ids], dtype=torch.long),
                torch.tensor([target_ids], dtype=torch.long),
                torch.tensor([list(cond)], dtype=torch.float32))
    return input_ids, target_ids, list(cond)


def batch_nll_and_probs(model, rows: list[dict], condition54_rows: list[list[float]],
                        tokenizer=None) -> tuple[float, list[list[float]]]:
    """Mean NLL + per-row mean target distributions for one conditioning arm.

    model: an object with forward(input_ids, targets=..., condition54=...)
    returning a dict with "logits" ([T, V], batch squeezed) and "loss" (float).
    Rows carry either text (prompt/target, tokenized here via tokenizer) or
    pre-tokenized input_ids/target_ids (the caller owns the shift for those).
    condition54_rows[i] is the 54-vector for rows[i].

    Target construction mirrors the trainer (scripts/zeref_continuation_006.py
    L884/910/1095): input = (prompt + target)[:-1], target =
    [-100]*(len(prompt)-1) + target, so logits[t] predicts target[t] and the
    loss covers exactly the target tokens.
    """
    if len(rows) != len(condition54_rows):
        raise ValueError("rows and condition54_rows must have equal length")
    total_nll = 0.0
    probs_rows: list[list[float]] = []
    for row, cond in zip(rows, condition54_rows):
        if "input_ids" in row:
            input_ids = list(row["input_ids"])
            target_ids = list(row["target_ids"])
        else:
            if tokenizer is None:
                raise ValueError("text rows need a tokenizer")
            prompt_ids = tokenizer.encode(row["prompt"], add_bos=True)
            target_full = tokenizer.encode(row["target"], add_bos=False)
            input_ids = (prompt_ids + target_full)[:-1]
            target_ids = [-100] * (len(prompt_ids) - 1) + target_full
        ids_t, tgt_t, cond_t = _to_model_inputs(model, input_ids, target_ids, cond)
        out = model(ids_t, targets=tgt_t, condition54=cond_t)
        logits = _as_list(out["logits"])
        if logits and isinstance(logits[0], list) and logits[0] and isinstance(logits[0][0], list):
            logits = logits[0]  # squeeze the batch dim: [1, T, V] -> [T, V]
        loss = out.get("loss")
        if loss is None:
            raise ValueError("model forward returned no loss; pass targets")
        loss = float(_as_list(loss)) if not isinstance(loss, (int, float)) else float(loss)
        total_nll += loss
        mask = [t != -100 for t in target_ids][:len(logits)]
        probs_rows.append(_mean_probs_over_targets(logits, mask))
    return total_nll / len(rows), probs_rows


def evaluate_12d_causal_gate(model, rows: list[dict], tokenizer=None,
                             min_delta_nll: float = DEFAULT_MIN_DELTA_NLL,
                             min_jsd: float = DEFAULT_MIN_JSD) -> dict:
    """True vs zero vs shuffled condition54. Returns the gate verdict dict."""
    true_conds = [list(r["condition54"]) for r in rows]
    zero_conds = [[0.0] * 54 for _ in rows]
    shuf_conds = [true_conds[(i + 1) % len(rows)] for i in range(len(rows))]
    nll_true, probs_true = batch_nll_and_probs(model, rows, true_conds, tokenizer)
    nll_zero, probs_zero = batch_nll_and_probs(model, rows, zero_conds, tokenizer)
    nll_shuf, probs_shuf = batch_nll_and_probs(model, rows, shuf_conds, tokenizer)
    jsds_zero = [jensen_shannon_divergence(p, q) for p, q in zip(probs_true, probs_zero)]
    jsds_shuf = [jensen_shannon_divergence(p, q) for p, q in zip(probs_true, probs_shuf)]
    mean_jsd = (sum(jsds_zero) + sum(jsds_shuf)) / (len(jsds_zero) + len(jsds_shuf)) if jsds_zero else 0.0
    delta_nll = min(nll_zero, nll_shuf) - nll_true
    passed = bool(delta_nll >= min_delta_nll and mean_jsd >= min_jsd)
    return {
        "schema": "zeref-12d-causal-gate-v1",
        "batches": len(rows),
        "nll_true": nll_true,
        "nll_zero": nll_zero,
        "nll_shuffled": nll_shuf,
        "delta_nll": delta_nll,
        "mean_jsd": mean_jsd,
        "min_delta_nll": min_delta_nll,
        "min_jsd": min_jsd,
        "passed": passed,
    }


def _load_eval_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    if not rows:
        raise ValueError(f"no eval rows in {path}")
    for r in rows:
        if "condition54" not in r or len(r["condition54"]) != 54:
            raise ValueError("every eval row needs a 54-float condition54")
    return rows


def _rows_from_gate_sets(gate_sets_path: Path, chain_path: Path) -> list[dict]:
    """Eval rows from the 006 gate sets with TRUE condition54 from the world chain.

    The gate sets give prompt/target pairs (set_a_added + set_b_added). The
    true condition54 vectors cycle deterministically through the recorded
    state12 vectors in the world chain. No chain -> no true arm -> fail loudly.
    """
    gate = json.loads(Path(gate_sets_path).read_text(encoding="utf-8"))
    pairs = list(gate.get("set_a_added", [])) + list(gate.get("set_b_added", []))
    if not pairs:
        raise ValueError(f"no prompt pairs in {gate_sets_path}")
    chain = [json.loads(ln) for ln in Path(chain_path).read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    state12s = [e["state12"] for e in chain if e.get("state12") and not e.get("genesis")]
    if not state12s:
        raise ValueError(f"no state12 vectors in {chain_path}; the true arm needs real recorded state12")
    rows = []
    for i, p in enumerate(pairs):
        cond = [0.0] * 54
        s12 = state12s[i % len(state12s)]
        cond[:12] = [float(x) for x in s12]
        rows.append({"prompt": f"user: {p['user']}\nassistant:",
                     "target": p["assistant"], "condition54": cond})
    return rows


def _load_checkpoint(checkpoint_path: Path):
    """Load a real checkpoint the same way Engine does. Returns (model, tokenizer, metadata)."""
    try:
        import torch  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("torch is required to load a real checkpoint") from exc
    from rawrphos.training.checkpoint import load_checkpoint
    loaded = load_checkpoint(str(checkpoint_path), load_training_state=False)
    return loaded["model"], loaded["tokenizer"], loaded["metadata"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", type=Path, required=True,
                    help="extracted accepted-checkpoint dir (required: no stub evaluation)")
    ap.add_argument("--eval", type=Path, default=None,
                    help="eval JSONL rows {prompt,target,condition54} (or input_ids/target_ids)")
    ap.add_argument("--from-gate-sets", type=Path, default=None,
                    help="scripts/zeref_gate_sets_v2.json for prompt/target pairs")
    ap.add_argument("--chain", type=Path, default=None,
                    help="world_chain.jsonl supplying true state12 vectors (required with --from-gate-sets)")
    ap.add_argument("--min-delta-nll", type=float, default=DEFAULT_MIN_DELTA_NLL)
    ap.add_argument("--min-jsd", type=float, default=DEFAULT_MIN_JSD)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    if args.eval is None and args.from_gate_sets is None:
        ap.error("supply --eval or --from-gate-sets (with --chain)")
    if args.from_gate_sets is not None and args.chain is None:
        ap.error("--from-gate-sets needs --chain for the true condition54 vectors")
    if args.eval is not None:
        rows = _load_eval_jsonl(args.eval)
    else:
        rows = _rows_from_gate_sets(args.from_gate_sets, args.chain)
    model, tokenizer, metadata = _load_checkpoint(args.checkpoint)
    model.eval()
    result = evaluate_12d_causal_gate(model, rows, tokenizer,
                                      min_delta_nll=args.min_delta_nll, min_jsd=args.min_jsd)
    result["checkpoint_sha256"] = metadata.get("checkpoint_sha256")
    result["training_steps"] = metadata.get("training_steps")
    result["eval_rows"] = len(rows)
    out = args.out or Path(f"gate12d-{metadata.get('checkpoint_sha256', 'unknown')[:12]}.json")
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
