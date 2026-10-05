"""Minimal MCP client for the Beast Box connector (apps/beastbox-cloud /api/mcp).

Speaks JSON-RPC 2.0 over MCP Streamable HTTP: initialize, then tools/call. It
accepts a plain JSON reply or a text/event-stream reply. Tool names match the
connector: get_beast, get_care_status, get_lost_cosmos_progress, list_moves,
feed_beast, play_with_beast, talk_to_beast.
"""

from __future__ import annotations

import itertools
import json
import urllib.error
import urllib.request
from typing import Any, Optional

PROTOCOL_VERSION = "2025-06-18"


class McpError(Exception):
    pass


def endpoint(url: str) -> str:
    url = url.rstrip("/")
    return url if url.endswith("/api/mcp") or url.endswith("/mcp") else url + "/api/mcp"


class McpClient:
    def __init__(self, url: str, token: str = "", timeout: float = 20.0) -> None:
        self.url = endpoint(url)
        self.token = token
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self._ids = itertools.count(1)
        self._ready = False

    def _post(self, payload: dict) -> Optional[dict]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                self.session_id = response.headers.get("Mcp-Session-Id") or self.session_id
                body = response.read().decode("utf-8")
                kind = response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            raise McpError(f"Beast Box connector answered HTTP {exc.code}") from None
        except (OSError, urllib.error.URLError) as exc:
            raise McpError(f"Beast Box connector unreachable: {exc}") from None
        if "id" not in payload or not body.strip():
            return None
        return _parse(body, kind, payload["id"])

    def _ensure_ready(self) -> None:
        if self._ready:
            return
        self._post({"jsonrpc": "2.0", "id": next(self._ids), "method": "initialize", "params": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "beastbox-musegadget", "version": "0.1.0"},
        }})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self._ready = True

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> Any:
        self._ensure_ready()
        reply = self._post({"jsonrpc": "2.0", "id": next(self._ids), "method": "tools/call",
                            "params": {"name": name, "arguments": arguments or {}}})
        if reply is None:
            raise McpError("empty reply from the Beast Box connector")
        if "error" in reply:
            raise McpError(str((reply["error"] or {}).get("message") or reply["error"]))
        return tool_result(reply.get("result") or {})


def _parse(body: str, kind: str, want_id: Any) -> dict:
    if "text/event-stream" in kind:
        for block in body.split("\n\n"):
            data = "\n".join(line[5:].lstrip() for line in block.splitlines() if line.startswith("data:"))
            if not data:
                continue
            try:
                message = json.loads(data)
            except ValueError:
                continue
            if isinstance(message, dict) and message.get("id") == want_id:
                return message
        raise McpError("no reply in the connector's event stream")
    try:
        message = json.loads(body)
    except ValueError:
        raise McpError("the connector did not answer JSON") from None
    if isinstance(message, list):
        message = next((m for m in message if isinstance(m, dict) and m.get("id") == want_id), {})
    return message


def tool_result(result: dict) -> Any:
    """structuredContent if present, else JSON parsed from the text content, else the text."""
    if result.get("isError"):
        texts = [c.get("text", "") for c in result.get("content") or [] if isinstance(c, dict)]
        raise McpError(" ".join(t for t in texts if t) or "the connector reported an error")
    if isinstance(result.get("structuredContent"), dict):
        return result["structuredContent"]
    texts = [c.get("text", "") for c in result.get("content") or [] if isinstance(c, dict) and c.get("type") == "text"]
    text = "\n".join(t for t in texts if t)
    try:
        return json.loads(text)
    except ValueError:
        return {"text": text}
