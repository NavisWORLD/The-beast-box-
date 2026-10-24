"""OFFLINE ONLY: model-side 42D conditioning and A/B on a checkpoint. Never promotes.

The served model accepts a 12-value external state (x12) and hardcodes zero external
input to x42. This script adds 42D conditioning WITHOUT editing the model: a forward
hook on state_init42 adds the routed 42D drive to the pre-tanh x42 logits, exactly the
way control_vector enters x12. Drive comes from beastbox.routing (Rigetti SIMULATED
counts into the quantum band; any other band without a fresh measurement is masked to
exact 0.0 and receipted 'missing'). No LLM, no paid inference, no live endpoint.

Arms: none | zero (explicit zeros, must equal none) | routed | matched_control (same
values, permuted + sign-flipped across the same unmasked slots).
"""
from __future__ import annotations
import json, math, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "models"), str(ROOT / "scripts")]
import torch
from beastbox.routing import rigetti_source, route
from beastbox.hashutil import sha256_obj
from rawrphos.training.checkpoint import load_checkpoint
from rawrphos_chat_eval import PAIRS, fmt


def matched(vec, mask):
    idx = [i for i, m in enumerate(mask) if m]
    vals = [vec[i] for i in idx]
    out = [0.0] * len(vec)
    for k, i in enumerate(idx):
        out[i] = (-1.0 if k % 2 == 0 else 1.0) * vals[(k * 5 + 3) % len(vals)] if vals else 0.0
    return out


def main(ckpt: str, out_path: str, records_json: str):
    rec = json.loads(Path(records_json).read_text())["scenario_records"]
    batches = [b for r in rec for b in r["batches"]]
    now = time.time()
    routed = [route({"quantum_rigetti": rigetti_source(b, now - 1)}, now=now) for b in batches]
    L = load_checkpoint(ckpt, load_training_state=False)
    m, tok = L["model"].eval(), L["tokenizer"]
    assert m.config.state_mode == "tri"
    cur = {"v42": None}

    def hook(_mod, _inp, out):
        if cur["v42"] is None:
            return out
        return out + cur["v42"].to(out)[None, None, :]
    h = m.state_init42.register_forward_hook(hook)

    def run(v12, v42):
        cur["v42"] = None if v42 is None else torch.tensor(v42, dtype=torch.float32)
        cv = None if v12 is None else torch.tensor([v12], dtype=torch.float32)
        nll, logps = [], []
        for q, a in PAIRS:
            f = tok.encode(fmt(q), add_bos=True); t = tok.encode(" " + a, add_eos=True)
            ids = torch.tensor([f + t])
            with torch.no_grad():
                lg = m(ids[:, :-1], control_vector=cv)["logits"][0, len(f) - 1:].float()
            nll.append(torch.nn.functional.cross_entropy(lg, ids[0, len(f):]).item())
            logps.append(torch.log_softmax(lg, -1))
        return sum(nll) / len(nll), logps

    base, base_lp = run(None, None)
    def kl(lp):
        return sum((b.exp() * (b - x)).sum(-1).mean().item() for b, x in zip(base_lp, lp)) / len(lp)
    arms = {"none": {"ref_nll": base, "kl_vs_none": 0.0}}
    z, zlp = run([0.0] * 12, [0.0] * 42); arms["zero"] = {"ref_nll": z, "kl_vs_none": kl(zlp)}
    per = []
    for r in routed:
        a, alp = run(r["d12"], r["d42"])
        c, clp = run(matched(r["d12"], r["mask12"]), matched(r["d42"], r["mask42"]))
        per.append({"receipt_sha256": r["receipt_sha256"], "tally": r["tally"],
                    "routed": {"ref_nll": a, "kl_vs_none": kl(alp)},
                    "matched_control": {"ref_nll": c, "kl_vs_none": kl(clp)}})
    h.remove()
    mean = lambda k, f: sum(p[k][f] for p in per) / len(per)
    arms["routed_mean"] = {"ref_nll": mean("routed", "ref_nll"), "kl_vs_none": mean("routed", "kl_vs_none")}
    arms["matched_control_mean"] = {"ref_nll": mean("matched_control", "ref_nll"), "kl_vs_none": mean("matched_control", "kl_vs_none")}
    pairing = [p["routed"]["kl_vs_none"] != p["matched_control"]["kl_vs_none"] for p in per]
    report = {"schema": "zeref-cond42-offline-ab-v1", "checkpoint_training_steps": int(L.get("metadata", {}).get("training_steps", 0) or 0) or None,
              "prompts": len(PAIRS), "rigetti_batches": len(batches), "label": "Rigetti SIMULATED (rigetti.sim.qvm, not QPU)",
              "arms": arms, "per_batch": per, "zero_equals_none": abs(z - base) < 1e-9,
              "routed_differs_from_control": all(pairing),
              "promoted": False, "claim_boundary": "Offline association test only. Not served, not gated, not promoted. Only the quantum band and D8 carry signal; other bands are missing (masked 0.0)."}
    report["report_sha256"] = sha256_obj(report)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(arms))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else str(ROOT / "apps/beastbox-cloud/public/spark/rigetti-qvm-sim.json"))
