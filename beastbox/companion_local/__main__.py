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
    sft = sub.add_parser("sft-data", help="Build the augmented SFT set for a real chat-model fine-tune.")
    sft.add_argument("--out", type=Path, default=Path("companion-run"))
    sft.add_argument("--profile", default="serene")
    sft.add_argument("--expect-creature", default=None, help="Fail unless the profile births this creature name.")
    tune = sub.add_parser("finetune", help="Real LoRA SFT on a Hugging Face chat model (CPU or CUDA), then merge.")
    tune.add_argument("--base", required=True, help="Local model directory or Hugging Face repo id.")
    tune.add_argument("--data", type=Path, default=Path("companion-run"))
    tune.add_argument("--out", type=Path, default=Path("companion-run"))
    tune.add_argument("--steps", type=int, default=200)
    tune.add_argument("--grad-accum", type=int, default=2)
    tune.add_argument("--max-len", type=int, default=384)
    tune.add_argument("--lr", type=float, default=2e-4)
    tune.add_argument("--rank", type=int, default=16)
    tune.add_argument("--alpha", type=int, default=32)
    tune.add_argument("--max-minutes", type=float, default=75.0)
    tuned_eval = sub.add_parser("eval-model", help="Generate replies to held-out prompts with a model and score them.")
    tuned_eval.add_argument("--model", required=True)
    tuned_eval.add_argument("--base", default=None, help="Optional base model for a side-by-side comparison.")
    tuned_eval.add_argument("--data", type=Path, default=Path("companion-run"))
    tuned_eval.add_argument("--out", type=Path, default=Path("companion-run"))
    tuned_eval.add_argument("--max-new-tokens", type=int, default=120)
    mfile = sub.add_parser("modelfile", help="Write an Ollama Modelfile (Qwen chat template) for a merged GGUF.")
    mfile.add_argument("--gguf", default="companion-glacecoil.gguf")
    mfile.add_argument("--out", type=Path, default=Path("Modelfile"))
    mfile.add_argument("--profile", default="serene")
    notes = sub.add_parser("release-notes", help="Write honest release notes from eval.json and the GGUF.")
    notes.add_argument("--eval", type=Path, required=True)
    notes.add_argument("--gguf", type=Path, required=True)
    notes.add_argument("--out", type=Path, required=True)
    notes.add_argument("--repo", required=True)
    notes.add_argument("--tag", required=True)
    notes.add_argument("--run-url", default="")
    notes.add_argument("--ollama-smoke", type=Path, default=None)
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
    if args.command in {"sft-data", "finetune", "eval-model", "modelfile", "release-notes"}:
        return _finetune_command(args)
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


def _finetune_command(args) -> int:
    from . import finetune as ft

    if args.command == "sft-data":
        print(json.dumps(ft.write_sft(args.out, profile_name=args.profile, expect_creature=args.expect_creature), indent=2))
    elif args.command == "finetune":
        report = ft.finetune(
            args.base, args.data, args.out, steps=args.steps, grad_accum=args.grad_accum, max_len=args.max_len,
            lr=args.lr, rank=args.rank, alpha=args.alpha, max_minutes=args.max_minutes,
        )
        print(json.dumps(report, indent=2))
    elif args.command == "eval-model":
        report = ft.evaluate_model(args.model, args.data, args.out, base=args.base, max_new_tokens=args.max_new_tokens)
        print(json.dumps({"scores": report["scores"], "base_scores": report["base_scores"], "passed": report["passed"]}, indent=2))
    elif args.command == "modelfile":
        ft.write_ollama_modelfile(args.out, birth(args.profile)["card"], args.gguf)
        print(args.out)
    else:
        ft.release_notes(args.eval, args.gguf, args.out, repo=args.repo, tag=args.tag, run_url=args.run_url, ollama_smoke=args.ollama_smoke)
        print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
