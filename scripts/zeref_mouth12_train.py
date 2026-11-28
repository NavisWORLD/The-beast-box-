"""12D into the mouth, training side (Cory, 2026-11-12 4:03 PM CT: "Yes, wire his 12D state into his mouth for real").

Behind ZEREF_12D_MOUTH, exactly "1" (default off: training is byte-identical).

The H1 probe (pin step 40304) found the tensor path dead: cond54 / control
vector ablations moved the next-token distribution by KL ~0, and only gain
slot 7 was non-zero (0.243), because the routed spark vector fills slot 7
only, so slots 0-11 never got a gradient. The text copy worked by surface only
(zeroed state KL 0.101, shuffled dims KL 0.0006). This module fixes the
training recipe, it does not touch the gate:

1. Pairing: every served-shape chat row is conditioned on THE SAME recorded
   state12 its descriptor text carries (condition54 = clip(state12) + 42 zeros).
   That pairing is the per-row conditioning receipt.
2. Conditioning dropout: with probability ZEREF_12D_TEXT_DROP (default 0.5)
   the descriptor message is removed from the row's text while the tensor stays,
   so the answer can only see the state through the tensor path.
3. Gain floor: cond_gain slots 0-11 are held at |g| >= ZEREF_12D_GAIN_FLOOR
   (default 0.25, sign kept, 0 -> +floor) at load and after every optimizer
   step, so the gain cannot collapse back to ~0.

Gate scoring stays unconditioned. Rows come from committed, recorded engine
traces (the same numbers the text already carries); no guest data, no owner
sensor feed. No RNG of its own: the caller passes a seeded torch.Generator.
"""
from __future__ import annotations

import json
import os

FLAG = "ZEREF_12D_MOUTH"
DESCRIPTOR_SCHEMA = "lived-state-descriptor-v1"


def enabled() -> bool:
    return os.environ.get("ZEREF_12D_MOUTH", "0") == "1"


def text_drop() -> float:
    return max(0.0, min(1.0, float(os.environ.get("ZEREF_12D_TEXT_DROP", "0.5"))))


def gain_floor() -> float:
    return max(0.0, float(os.environ.get("ZEREF_12D_GAIN_FLOOR", "0.25")))


def _is_descriptor(message) -> bool:
    return message.get("role") == "system" and DESCRIPTOR_SCHEMA in str(message.get("content") or "")


def descriptor_state(messages):
    """The state12 the row's descriptor text carries, or None."""
    for message in messages or []:
        if not _is_descriptor(message):
            continue
        try:
            body = json.loads(message["content"])
        except (ValueError, TypeError):
            return None
        state = body.get("state12")
        if isinstance(state, list) and len(state) == 12 and all(
                type(x) in (int, float) and not isinstance(x, bool) for x in state):
            return [float(x) for x in state]
        return None
    return None


def condition54(state12):
    return [max(-1.0, min(1.0, float(x))) for x in state12] + [0.0] * 42


def encode_row(encode, row, limit=None):
    """encode_chat_row plus, for a served row with a recorded state, the state and the text-hidden variant."""
    from zeref_served_shape import TOKEN_CAP, answer_example, encode_chat_row
    limit = TOKEN_CAP if limit is None else limit
    example = encode_chat_row(encode, row, limit)
    if example is None or not example.get("served_shape"):
        return example
    state = descriptor_state(example.get("messages"))
    if state is None:
        return example
    hidden_msgs = [m for m in example["messages"] if not _is_descriptor(m)]
    hidden = answer_example(encode, hidden_msgs, row.get("assistant") or "", limit) if hidden_msgs else None
    example["state12"] = state
    if hidden is not None:
        example["hidden"] = {"input": hidden["input"], "target": hidden["target"]}
    return example


def pool_entry(example):
    entry = {"input": example["input"], "target": example["target"], "source": example.get("source", "chat")}
    if example.get("state12") is not None:
        entry["state12"] = example["state12"]
        if example.get("hidden"):
            entry["hidden"] = example["hidden"]
    return entry


def apply_dropout(batch, generator, drop, tally):
    """Return the batch with text-hidden variants swapped in for dropped state rows (tensor stays)."""
    import torch
    out = []
    for row in batch:
        if row.get("state12") is None:
            out.append(row)
            continue
        tally["state_rows"] = tally.get("state_rows", 0) + 1
        if row.get("hidden") and float(torch.rand(1, generator=generator)) < drop:
            out.append({**row, "input": row["hidden"]["input"], "target": row["hidden"]["target"], "_text_hidden": True})
            tally["tensor_only_rows"] = tally.get("tensor_only_rows", 0) + 1
        else:
            out.append(row)
            tally["text_and_tensor_rows"] = tally.get("text_and_tensor_rows", 0) + 1
    return out


def condition_rows(batch, fallback):
    """Per-row condition54: the row's own state for state rows; fallback(j) (old behaviour) otherwise."""
    return [condition54(r["state12"]) if r.get("state12") is not None else fallback(j) for j, r in enumerate(batch)]


def floor_gain(model, floor):
    """Hold |cond_gain[0:12]| >= floor (sign kept; exact 0 -> +floor). Returns the slots after."""
    import torch
    gain = getattr(model, "cond_gain", None)
    if gain is None or floor <= 0:
        return None
    with torch.no_grad():
        head = gain.data[:12]
        sign = torch.where(head < 0, -torch.ones_like(head), torch.ones_like(head))
        head.copy_(torch.where(head.abs() < floor, sign * floor, head))
    return [round(float(x), 6) for x in gain.data[:12]]


def jsd_mean(logits_p, logits_q, targets):
    """Mean Jensen-Shannon divergence (nats) between two next-token distributions, over
    supervised positions (targets != -100). Differentiable: used by the CF-JS margin loss
    and, under no-grad, by the mouth12 gate probe."""
    import torch
    mask = (targets != -100)
    if not bool(mask.any()):
        return None
    p = torch.softmax(logits_p.float(), dim=-1)
    q = torch.softmax(logits_q.float(), dim=-1)
    m = 0.5 * (p + q)

    def kl(a, b):
        return (a * (a.clamp_min(1e-12).log() - b.clamp_min(1e-12).log())).sum(-1)

    return (0.5 * kl(p, m) + 0.5 * kl(q, m))[mask].mean()


def mouth12_probe(model, encode, rows):
    """Gate probe 9 (Step 5): does the 12D path carry signal the text does not?

    On text-hidden served rows (the descriptor text removed, so the answer is reachable
    only through the tensor): delta_nll_12d = NLL(unconditioned) - NLL(conditioned on the
    row's own recorded state12), and mean_jsd = mean JSD between the own-state and the
    rolled-state (row j conditioned on row j-1's state) distributions. Returns None when
    no usable rows exist (probe did not run: the gate treats that as not-applicable)."""
    import torch
    hidden = []
    conds = []
    for row in rows or []:
        example = encode_row(encode, row)
        if example is None or not example.get("served_shape"):
            continue
        state = descriptor_state(example.get("messages"))
        if state is None or not example.get("hidden"):
            continue
        hidden.append(example["hidden"])
        conds.append(condition54(state))
    if not hidden:
        return None
    was_training = model.training
    model.eval()
    try:
        with torch.inference_mode():
            cond_t = torch.tensor(conds, dtype=torch.float32)
            rolled = torch.roll(cond_t, shifts=1, dims=0)
            nll_c = 0.0
            nll_u = 0.0
            jsds = []
            for j, h in enumerate(hidden):
                x = torch.tensor([h["input"]])
                y = torch.tensor([h["target"]])
                nll_c += float(model(x, targets=y, condition54=cond_t[j:j + 1])["loss"])
                nll_u += float(model(x, targets=y)["loss"])
                lg_c = model(x, condition54=cond_t[j:j + 1])["logits"]
                lg_r = model(x, condition54=rolled[j:j + 1])["logits"]
                v = jsd_mean(lg_c, lg_r, y)
                if v is not None:
                    jsds.append(float(v))
        return {"rows": len(hidden),
                "delta_nll_12d": round(nll_u / len(hidden) - nll_c / len(hidden), 6),
                "mean_jsd": round(sum(jsds) / len(jsds), 6) if jsds else None}
    finally:
        if was_training:
            model.train()
