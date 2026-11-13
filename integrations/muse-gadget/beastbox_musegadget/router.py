"""Route a Beast Box action to the best source.

1. The live browser beast, through the bridge, when a linked tab is connected.
2. The Beast Box connector (BEASTBOX_URL + token, MCP tools) when configured.
3. This gadget's own saved copy, seeded from an exported browser snapshot.

Every answer says which source it came from.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from beastbox_musegadget import HONESTY, beast as beastlib, companion, moves as movelib
from beastbox_musegadget.bridge import BridgeAdmin, BridgeError
from beastbox_musegadget.config import Config
from beastbox_musegadget.mcp_client import McpClient, McpError

log = logging.getLogger("beastbox_musegadget.router")

MCP_TOOLS = {
    "status": "get_beast",
    "feed": "feed_beast",
    "play": "play_with_beast",
    "talk": "talk_to_beast",
    "moves": "list_moves",
    "lost_cosmos": "get_lost_cosmos_progress",
}
SOURCE_LABELS = {
    "bridge": "live browser beast (linked through the Beast Box bridge)",
    "bridge-cached": "last state sent by the linked browser (no tab open right now)",
    "connector": "Beast Box connector",
    "local": "this gadget's saved copy (changes stay on the gadget)",
}


class Router:
    def __init__(self, cfg: Config, bridge: Optional[BridgeAdmin] = None, mcp: Optional[McpClient] = None) -> None:
        self.cfg = cfg
        self.bridge = bridge or BridgeAdmin(cfg.bridge_url, cfg.state_path)
        self.mcp = mcp if mcp is not None else (McpClient(cfg.beastbox_url, cfg.beastbox_token) if cfg.beastbox_url else None)
        self.local = beastlib.LocalStore(cfg.state_path, cfg.snapshot)
        self.notes: list = []

    def run(self, action: str, args: Optional[Dict[str, Any]] = None) -> dict:
        args = dict(args or {})
        self.notes = []
        for name, attempt in (("bridge", self._bridge), ("connector", self._connector), ("local", self._local)):
            try:
                result = attempt(action, args)
            except _Skip as skip:
                if skip.note:
                    self.notes.append(skip.note)
                continue
            result.setdefault("honesty", HONESTY)
            result["source"] = SOURCE_LABELS[result.pop("_source", name)]
            if self.notes:
                result["notes"] = self.notes
            return result
        raise beastlib.NoBeast(" ".join(self.notes) or "no beast is available")

    # -- 1. live browser ------------------------------------------------------

    def _bridge(self, action: str, args: dict) -> dict:
        if self.bridge.token() is None:
            raise _Skip()
        try:
            reply = self.bridge.command(action, args, self.cfg.bridge_timeout_s)
        except BridgeError as exc:
            if exc.status == 409 and action == "status":
                return self._bridge_cached()
            if exc.status in (409, 503):
                raise _Skip() from None
            raise _Skip(f"Linked browser did not answer ({exc}).") from None
        if not reply.get("ok", True):
            raise _Skip(f"Linked browser refused: {reply.get('error') or 'error'}.")
        out: dict = {"action": action, "result": reply.get("result")}
        if isinstance(reply.get("state"), dict):
            out["beast"] = reply["state"]
        return out

    def _bridge_cached(self) -> dict:
        """The last state a linked tab sent, when no tab is open right now."""
        try:
            cached = self.bridge.state()
        except BridgeError:
            raise _Skip() from None
        if not isinstance(cached.get("state"), dict):
            raise _Skip()
        self.notes.append("No Beast Box tab is open right now; this is the last state the linked browser sent.")
        return {"action": "status", "result": cached["state"], "beast": cached["state"],
                "state_at": cached.get("state_at"), "_source": "bridge-cached"}

    # -- 2. connector ---------------------------------------------------------

    def _connector(self, action: str, args: dict) -> dict:
        if self.mcp is None:
            raise _Skip()
        try:
            if action == "attack":
                listed = self.mcp.call_tool("list_moves", {})
                return {"action": action, "result": {"moves": listed,
                        "note": "The connector has no attack tool; link a browser tab to see the animation."}}
            tool = MCP_TOOLS[action]
            result = self.mcp.call_tool(tool, _mcp_args(action, args))
            out = {"action": action, "result": result}
            if action == "status":
                try:
                    out["care"] = self.mcp.call_tool("get_care_status", {})
                except McpError:
                    pass
            return out
        except McpError as exc:
            raise _Skip(f"Beast Box connector: {exc}.") from None

    # -- 3. gadget copy -------------------------------------------------------

    def _local(self, action: str, args: dict) -> dict:
        try:
            session = self.local.load()
        except beastlib.NoBeast as exc:
            raise _Skip(str(exc)) from None
        beast = session["beast"]
        out: dict = {"action": action}
        if action == "status":
            pass
        elif action == "feed":
            out["result"] = {**beastlib.care_action(session, "feed"), "food": str(args.get("food") or "a snack")[:60]}
        elif action == "play":
            game = str(args.get("game") or "spark").lower()
            if game == "train":
                out["result"] = beastlib.finish_training(session, int(args.get("hits", 3)))
            elif game in ("spark", "pet"):
                out["result"] = beastlib.care_action(session, game)
            else:
                raise ValueError("game must be spark, pet or train")
        elif action == "talk":
            message = str(args.get("message") or "").strip()
            if not message:
                raise ValueError("message is required")
            spoken = companion.reply(self.cfg, beastlib.summary(session), beast, message)
            growth = beastlib.remember_exchange(session, message, spoken["reply"])
            out["result"] = {**spoken, "growth": growth}
        elif action in ("moves", "attack"):
            moveset = movelib.build_moveset(beast.get("genome"))
            if action == "moves":
                out["result"] = {"element": moveset["element"], "temperament": moveset["temperament"],
                                 "moves": [{k: m[k] for k in ("id", "name", "style", "power")} for m in moveset["moves"]]}
            else:
                counter = int(beast.get("attacks", 0))
                move = movelib.find_move(moveset, str(args.get("move") or "")) or movelib.pick_attack(moveset, counter, "chat")
                beast["attacks"] = counter + 1
                out["result"] = {"move": {k: move[k] for k in ("id", "name", "style", "power")},
                                 "crit": bool(move.get("crit")),
                                 "note": "No browser tab is linked, so no animation played."}
        elif action == "lost_cosmos":
            progress = session.get("lost_cosmos")
            out["result"] = progress or {"available": False,
                                         "note": "Lost Cosmos progress lives in the browser's game save. Link a browser tab or include it in the snapshot."}
        else:
            raise ValueError(f"unknown action: {action}")
        if action not in ("status", "moves", "lost_cosmos"):
            self.local.save(session)
        out["beast"] = beastlib.summary(session)
        return out


class _Skip(Exception):
    def __init__(self, note: str = "") -> None:
        super().__init__(note)
        self.note = note


def _mcp_args(action: str, args: dict) -> dict:
    if action == "feed" and args.get("food"):
        return {"food": args["food"]}
    if action == "play":
        return {k: args[k] for k in ("game", "hits") if k in args}
    if action == "talk":
        return {"message": args.get("message", "")}
    return {}
