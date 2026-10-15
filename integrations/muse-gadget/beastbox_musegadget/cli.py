"""``musegadget-beastbox`` command line."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from beastbox_musegadget import __version__, beast as beastlib
from beastbox_musegadget.bridge import BridgeAdmin, BridgeError, serve
from beastbox_musegadget.commands import handle
from beastbox_musegadget.config import load
from beastbox_musegadget.specs import COMMAND_SPECS

MAX_STDIN = 256 * 1024


def _print(result: dict, as_json: bool) -> int:
    if as_json or not result.get("ok"):
        stream = sys.stdout if result.get("ok") else sys.stderr
        print(json.dumps(result if as_json else result.get("error"), indent=2, ensure_ascii=False), file=stream)
        return 0 if result.get("ok") else 1
    payload = result["payload"]
    beast = payload.get("beast") or {}
    if beast:
        stats = beast.get("stats") or {}
        print(f"{beast.get('name')} the {beast.get('species')} — stage {beast.get('stage')}, mood {beast.get('mood')}")
        if stats:
            print(f"  xp {stats.get('xp')}  bond {stats.get('bond')}  energy {stats.get('energy')}")
    if payload.get("result") is not None:
        res = payload["result"]
        if isinstance(res, dict) and "reply" in res:
            print(f"  {res['reply']}")
        else:
            print("  " + json.dumps(res, ensure_ascii=False))
    print(f"  source: {payload.get('source')}")
    for note in payload.get("notes") or []:
        print(f"  note: {note}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="musegadget-beastbox",
                                     description="Beast Box gadget for Meta Muse (community gadget, not made or endorsed by Meta).")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--json", action="store_true", help="print the full JSON result")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="check the beast")
    p = sub.add_parser("feed", help="feed the beast")
    p.add_argument("--food")
    p = sub.add_parser("play", help="play with the beast")
    p.add_argument("--game", choices=["spark", "pet", "train"])
    p.add_argument("--hits", type=int)
    p = sub.add_parser("talk", help="say something to the beast")
    p.add_argument("message", nargs="+")
    p = sub.add_parser("attack", help="make the beast use an attack move")
    p.add_argument("--move")
    sub.add_parser("moves", help="list attack moves")
    sub.add_parser("lost-cosmos", help="Lost Cosmos progress")
    p = sub.add_parser("muse-command", help="(used by the Muse SDK) run NAME with JSON params on stdin")
    p.add_argument("name")
    p = sub.add_parser("import-snapshot", help="copy an exported browser beast onto this gadget")
    p.add_argument("file", type=Path)
    p = sub.add_parser("bridge", help="the live browser bridge")
    bsub = p.add_subparsers(dest="bridge_cmd", required=True)
    s = bsub.add_parser("serve", help="run the bridge server")
    s.add_argument("--host")
    s.add_argument("--port", type=int)
    p = sub.add_parser("link", help="link the browser that shows CODE")
    p.add_argument("code")
    sub.add_parser("links", help="list linked browsers")
    p = sub.add_parser("unlink", help="revoke a linked browser")
    p.add_argument("link_id")
    sub.add_parser("specs", help="print the Muse command specs as JSON")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", stream=sys.stderr)
    cfg = load()

    if args.cmd == "muse-command":
        raw = sys.stdin.read(MAX_STDIN)
        try:
            params = json.loads(raw) if raw.strip() else {}
        except ValueError:
            params = None
        result = handle(args.name, params, cfg) if isinstance(params, dict) else {"ok": False, "error": "params must be a JSON object"}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    if args.cmd == "specs":
        print(json.dumps(COMMAND_SPECS, indent=2))
        return 0
    if args.cmd == "bridge":
        serve(cfg, args.host, args.port)
        return 0
    if args.cmd == "import-snapshot":
        try:
            session = beastlib.LocalStore(cfg.state_path).import_snapshot(args.file)
        except beastlib.NoBeast as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Saved {beastlib.shown_name(session['beast'])} on this gadget.")
        return 0
    if args.cmd in ("link", "links", "unlink"):
        admin = BridgeAdmin(cfg.bridge_url, cfg.state_path)
        try:
            if args.cmd == "link":
                linked = admin.link(args.code)
                print(f"Linked {linked['label']} ({linked['link_id']}). Muse commands now reach that browser beast.")
            elif args.cmd == "links":
                links = admin.links()
                for link in links:
                    state = "connected" if link["connected"] else "not connected"
                    print(f"{link['link_id']}  {link['label']}  {state}")
                if not links:
                    print("No linked browsers. Tap Pair in Beast Box, then run `musegadget-beastbox link CODE`.")
            else:
                admin.unlink(args.link_id)
                print(f"Revoked {args.link_id}.")
        except BridgeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    params: dict = {}
    if args.cmd == "feed" and args.food:
        params["food"] = args.food
    if args.cmd == "play":
        params.update({k: v for k, v in (("game", args.game), ("hits", args.hits)) if v is not None})
    if args.cmd == "talk":
        params["message"] = " ".join(args.message)
    if args.cmd == "attack" and args.move:
        params["move"] = args.move
    name = "beastbox." + args.cmd.replace("-", "_")
    return _print(handle(name, params, cfg), args.json)
