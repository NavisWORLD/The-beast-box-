from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch

from beastbox.models.phos_reference import PHOSReferenceLM


def main() -> int:
    p = argparse.ArgumentParser(description="Train the independent PHOS/dyn12 reference character LM")
    p.add_argument("text", type=Path)
    p.add_argument("--steps", type=int, default=500)
    p.add_argument("--seq", type=int, default=128)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--seed", type=int, default=1337)
    p.add_argument("--out", type=Path, default=Path("runs/phos_reference.pt"))
    args = p.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    text = args.text.read_text(encoding="utf-8")
    chars = sorted(set(text))
    if len(text) < args.seq + 2:
        raise SystemExit("training text is too short")
    stoi = {c: i for i, c in enumerate(chars)}
    data = torch.tensor([stoi[c] for c in text], dtype=torch.long)
    model = PHOSReferenceLM(vocab_size=len(chars), max_seq_len=args.seq)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)

    def batch():
        starts = torch.randint(0, len(data) - args.seq - 1, (args.batch,))
        x = torch.stack([data[i : i + args.seq] for i in starts])
        y = torch.stack([data[i + 1 : i + args.seq + 1] for i in starts])
        return x, y

    history = []
    for step in range(1, args.steps + 1):
        x, y = batch()
        out = model(x, y)
        loss = out["loss"]
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step == 1 or step % 50 == 0 or step == args.steps:
            gates = [float(t["gate"]) for t in out["telemetry"]]
            sigmas = [float(t["sigma"]) for t in out["telemetry"]]
            row = {"step": step, "loss": float(loss.detach()), "gates": gates, "sigmas": sigmas}
            history.append(row)
            print(json.dumps(row))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "vocab": chars, "config": {"max_seq_len": args.seq}, "history": history}, args.out)
    args.out.with_suffix(".json").write_text(json.dumps({"vocab": chars, "history": history}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
