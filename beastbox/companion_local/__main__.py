"""Local companion commands. Nothing here deploys or merges a pull request."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .personality import birth, reply
from .pipeline import prepare
from .senses import accept_hearing, accept_vision, simulate_live
from .train import FULL_RUN_COMMAND


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train and run a local companion personality.")
    sub = parser.add_subparsers(dest="command", required=True)
    train = sub.add_parser("train", help="Build the dataset, smoke-train, export, evaluate, and register.")
    train.add_argument("--out", type=Path, default=Path("companion-run"))
    train.add_argument("--opt-in-chat", type=Path, default=None)
    train.add_argument("--full", action="store_true", help="Also try QLoRA when CUDA and a local base model exist.")
    train.add_argument("--base", type=Path, default=None, help="Local Qwen2.5 or Llama 3.2 directory. Never downloaded.")
    show = sub.add_parser("birth", help="Print the seeded personality card.")
    show.add_argument("--profile", default="serene")
    chat = sub.add_parser("chat", help="One local personality reply. Not a claim of model omniscience.")
    chat.add_argument("text")
    chat.add_argument("--card", type=Path, default=None)
    sim = sub.add_parser("simulate", help="One simulated mood step from a text event.")
    sim.add_argument("--scene", default="")
    args = parser.parse_args(argv)
    if args.command == "train":
        report = prepare(args.out, chat_export=args.opt_in_chat, full=args.full, base=args.base)
        print(json.dumps({key: report[key] for key in ("creature", "eval", "full", "accelerator")}, indent=2))
        print(FULL_RUN_COMMAND)
        return 0
    if args.command == "birth":
        print(json.dumps(birth(args.profile)["card"], indent=2))
        return 0
    if args.command == "chat":
        card = json.loads(args.card.read_text(encoding="utf-8")) if args.card else birth()["card"]
        print(reply(card, args.text))
        return 0
    born = birth()
    events = []
    if args.scene:
        events.append(accept_vision({"schema": "companion-vision-event-v1", "text": args.scene, "model": "moondream"}))
    events.append(accept_hearing({
        "schema": "companion-hearing-event-v1",
        "transcript": "",
        "loudness": 0.2,
        "onset": True,
        "engine": "loudness-only",
    }))
    print(json.dumps(simulate_live(born["traits"], events), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
