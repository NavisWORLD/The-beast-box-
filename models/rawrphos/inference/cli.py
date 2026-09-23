"""Offline CLI for the verified native checkpoint; never provisions a provider."""
import argparse
import json

from rawrphos.inference.engine import Engine

FINAL_SHA256 = "35476cc6a6a40eb3f22c0a990f9a6e93aa82af79eaa64ecd9bd3df2719648606"


def main(argv=None):
    parser = argparse.ArgumentParser(description="RAWRPHØS local PyTorch inference")
    parser.add_argument("--checkpoint", required=True, help="Extracted step-00006000 directory")
    parser.add_argument("--expected-sha256", default=FINAL_SHA256, help="Expected model.safetensors hash")
    parser.add_argument("--threads", type=int, default=4)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("info", help="Verify checkpoint manifest and print model identity")
    prompt = sub.add_parser("prompt", help="Generate text without remote calls or tool grants")
    prompt.add_argument("text", help="Prompt text")
    prompt.add_argument("--max-tokens", type=int, default=64)
    prompt.add_argument("--temperature", type=float, default=0)
    prompt.add_argument("--seed", type=int, default=67)
    prompt.add_argument("--no-cache", action="store_true")
    args = parser.parse_args(argv)
    if args.threads < 1 or args.threads > 32:
        parser.error("--threads must be between 1 and 32")
    if args.command == "prompt":
        if not 1 <= args.max_tokens <= 256:
            parser.error("--max-tokens must be between 1 and 256")
        if not 0 <= args.seed < 2**63:
            parser.error("--seed must be in [0, 2**63)")
    engine = Engine(args.checkpoint, max_new_tokens=256, threads=args.threads,
                    expected_sha256=args.expected_sha256)
    if args.command == "info":
        print(json.dumps(engine.info(), sort_keys=True, indent=2, ensure_ascii=False))
    else:
        output = engine.complete(args.text, max_tokens=args.max_tokens,
                                 temperature=args.temperature, seed=args.seed,
                                 use_cache=not args.no_cache)
        print(output)
        print(json.dumps(engine.last_metrics, sort_keys=True), file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
