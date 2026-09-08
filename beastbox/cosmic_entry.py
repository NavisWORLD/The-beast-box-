"""Packaged launch adapter for the loopback COSMIC.CYPHER owner UI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .cosmic_web import CosmicApp, serve, validate_bind_host


def default_data_dir() -> Path:
    return Path.home() / ".beastbox" / "data"


def smoke(root: Path) -> dict[str, object]:
    """Headless package proof: initialize and inspect the real durable substrate."""
    app = CosmicApp(root)
    orbit = app.service.orbit_snapshot()
    runtime = orbit["runtime"]
    authority = orbit["authority"]
    return {
        "schema": "cosmic-ui-smoke-v1",
        "valid": bool(runtime["valid"]),
        "system_id": str(runtime["system_id"]),
        "turn": int(runtime["turn"]),
        "checkpoint_sha256": str(runtime["checkpoint_sha256"]),
        "authority_grants": sum(1 for granted in authority.values() if granted),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="beastbox-cosmic",
        description="Launch the local-only COSMIC.CYPHER product surface over Beast Box durable state.",
    )
    parser.add_argument("--data-dir", type=Path, help="substrate directory; --demo requires a new destination")
    parser.add_argument("--host", default="127.0.0.1", help="loopback host only")
    parser.add_argument("--port", type=int, default=8081)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true", help="headless installed-package/runtime integrity check")
    mode.add_argument("--demo", action="store_true", help="run the real deterministic reference demo in a new directory")
    args = parser.parse_args(argv)
    root = (args.data_dir or default_data_dir()).expanduser().absolute()
    try:
        validate_bind_host(args.host)
        if args.demo:
            if args.data_dir is None:
                raise ValueError("--demo needs --data-dir pointing to a new directory")
            from .cosmic_demo import run_reference_demo
            print(json.dumps(run_reference_demo(root), sort_keys=True))
            return 0
        if args.smoke:
            print(json.dumps(smoke(root), sort_keys=True))
            return 0
        serve(root, host=args.host, port=args.port)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Beast Box COSMIC.CYPHER: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
