"""Streamable HTTP JSON-RPC for the public Beast Box connector."""

from __future__ import annotations

from typing import Any

from .evidence import OWNER_TOOLS, RESEARCH, WORKFLOWS, SourceBook, call_tool
from .widget import DASHBOARD_URI, WIDGET_HTML

PROTOCOL_VERSIONS = ("2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_PROTOCOL = "2025-06-18"
SERVER_NAME = "beastbox-cosmos-connect"
SERVER_VERSION = "0.1.0"

INSTRUCTIONS = (
    "BEAST BOX // COSMOS CONNECT reads Cory Davis's existing public COSMOS evidence. "
    "MODEL ≠ MEMORY. MODEL ≠ STATE. MODEL ≠ AUTHORITY. "
    "A GitHub success is not live inference and not physical sensor capture. "
    "Owner tools are disabled and will not call the private bridge. "
    "Do not invent telemetry that a tool marks UNAVAILABLE or NOT YET VERIFIED."
)


def _schema(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required or [],
    }


_CLAIMS = {
    "claim_live_inference": {"type": "boolean"},
    "claim_physical_capture": {"type": "boolean"},
    "claim_ci_proves_inference": {"type": "boolean"},
}


def _tool(
    name: str,
    title: str,
    description: str,
    properties: dict,
    required: list[str] | None = None,
    read_only: bool = True,
    destructive: bool = False,
    meta: dict | None = None,
) -> dict:
    tool = {
        "name": name,
        "title": title,
        "description": description,
        "inputSchema": _schema({**properties, **_CLAIMS}, required),
        "annotations": {
            "readOnlyHint": read_only,
            "destructiveHint": destructive,
            "idempotentHint": read_only,
            "openWorldHint": True,
        },
    }
    if meta:
        tool["_meta"] = meta
    return tool


_RESULT_VIEW = {
    "ui": {"resourceUri": DASHBOARD_URI, "visibility": ["model", "app"]},
    "openai/outputTemplate": DASHBOARD_URI,
}
_DASHBOARD_VIEW = {
    **_RESULT_VIEW,
    "openai/ui": {"entrypoints": [{"type": "global"}]},
}
_MENTIONS = {
    "ui": {"visibility": ["app"]},
    "openai/extensions": {"mentions/search": {}},
}


def tool_definitions() -> list[dict]:
    experiment_enum = {"type": "string", "enum": list(RESEARCH)}
    workflow_enum = {"type": "string", "enum": list(WORKFLOWS)}
    tools = [
        _tool(
            "beastbox_get_status",
            "Beast Box public status",
            "Retrieve the public release marker, GitHub main revision, public website status, "
            "and separate frontend, backend-readiness, and backend-activation states. "
            "Bridge /healthz readiness is not live inference.",
            {},
            meta=_RESULT_VIEW,
        ),
        _tool(
            "beastbox_get_architecture",
            "COSMOS architecture",
            "Explain the repository-backed COSMOS architecture and module boundaries from the ecosystem manifest.",
            {"component": {"type": "string", "minLength": 1, "maxLength": 64}},
        ),
        _tool(
            "beastbox_list_models",
            "Model inventory",
            "List source-supported provider identities and separate fixtures, adapters, historical reports, and live production verification.",
            {"include_historical": {"type": "boolean"}},
        ),
        _tool(
            "beastbox_get_research",
            "Published research receipt",
            "Retrieve one published experiment file, including its original text, source revision, and evidence URL.",
            {"experiment": experiment_enum},
            ["experiment"],
            meta=_RESULT_VIEW,
        ),
        _tool(
            "beastbox_get_sensory_status",
            "Sensory status",
            "Show implemented sensory capabilities named by the public release, the proof scope, and hardware-test limits. "
            "This tool does not start a camera, microphone, or biometric capture.",
            {},
        ),
        _tool(
            "beastbox_get_ci",
            "GitHub verification runs",
            "Retrieve recent GitHub Actions runs and their head revisions. Success does not prove live inference or physical sensor capture.",
            {"workflow": workflow_enum, "limit": {"type": "integer", "minimum": 1, "maximum": 5}},
            ["workflow"],
        ),
        _tool(
            "beastbox_search_mentions",
            "COSMOS evidence mentions",
            "Search evidence pointers for composer at-mentions. Desktop clients can show this picker. "
            "Web and mobile clients should use the read-only tools directly.",
            {"query": {"type": "string", "maxLength": 80}},
            ["query"],
            meta=_MENTIONS,
        ),
        _tool(
            "beastbox_open_dashboard",
            "COSMOS dashboard",
            "Open the evidence dashboard. It shows live public status separately from historical research pointers.",
            {},
            meta=_DASHBOARD_VIEW,
        ),
    ]
    for name, spec in OWNER_TOOLS.items():
        tools.append(
            _tool(
                name,
                "DISABLED " + spec["title"],
                "DISABLED. The current production bridge has this route, but this connector has no delegated owner credential. "
                "Calling it returns OWNER_CONNECTION_DISABLED and does not contact the private bridge. "
                + (
                    "State-changing; it stays off until backup, isolated restoration, deployment, and live acceptance exist."
                    if spec["state_changing"]
                    else "Read-only on the bridge, still disabled here."
                ),
                {},
                read_only=not spec["state_changing"],
                destructive=spec["state_changing"],
            )
        )
    return tools


def resource_definitions() -> list[dict]:
    resources = [
        {
            "uri": DASHBOARD_URI,
            "name": "COSMOS dashboard",
            "description": "Interactive view of a COSMOS CONNECT tool result. Essential data remains in the tool text.",
            "mimeType": "text/html;profile=mcp-app",
        }
    ]
    pointers = [
        ("cosmos://evidence/status", "Deployment status", "beastbox_get_status"),
        ("cosmos://evidence/architecture", "COSMOS architecture", "beastbox_get_architecture"),
        ("cosmos://evidence/models", "Model inventory", "beastbox_list_models"),
        ("cosmos://evidence/senses", "Sensory status", "beastbox_get_sensory_status"),
        ("cosmos://evidence/ci", "GitHub verification", "beastbox_get_ci"),
    ]
    for uri, title, tool in pointers:
        resources.append(
            {
                "uri": uri,
                "name": title,
                "description": f"Pointer. Call {tool} for a live read. This resource is not a cached production measurement.",
                "mimeType": "application/json",
            }
        )
    for experiment in RESEARCH:
        resources.append(
            {
                "uri": f"cosmos://evidence/research/{experiment}",
                "name": experiment,
                "description": "Pointer. Call beastbox_get_research with this experiment id.",
                "mimeType": "application/json",
            }
        )
    return resources


def handle_message(message: object, book: SourceBook) -> dict | None:
    if not isinstance(message, dict):
        return _error(None, -32600, "invalid request")
    method = message.get("method")
    request_id = message.get("id")
    if not isinstance(method, str):
        return _error(request_id, -32600, "invalid request")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _error(request_id, -32602, "invalid params")
    if method == "notifications/initialized":
        return None
    if request_id is None and method.startswith("notifications/"):
        return None
    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in PROTOCOL_VERSIONS else DEFAULT_PROTOCOL
        return _result(
            request_id,
            {
                "protocolVersion": version,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": INSTRUCTIONS,
            },
        )
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": tool_definitions()})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            return _error(request_id, -32602, "tool name is required")
        if not isinstance(arguments, dict):
            return _error(request_id, -32602, "tool arguments must be an object")
        payload, is_error = call_tool(name, arguments, book)
        return _result(request_id, _tool_result(payload, is_error))
    if method == "resources/list":
        return _result(request_id, {"resources": resource_definitions()})
    if method == "resources/read":
        uri = params.get("uri")
        if not isinstance(uri, str):
            return _error(request_id, -32602, "resource uri is required")
        content = _read_resource(uri)
        if content is None:
            return _error(request_id, -32002, "resource not found")
        return _result(request_id, {"contents": [content]})
    return _error(request_id, -32601, "method not found")


def _tool_result(payload: dict, is_error: bool) -> dict:
    import json

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    result: dict[str, Any] = {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        "isError": is_error,
    }
    return result


def _read_resource(uri: str) -> dict | None:
    if uri == DASHBOARD_URI:
        return {
            "uri": uri,
            "mimeType": "text/html;profile=mcp-app",
            "text": WIDGET_HTML,
        }
    if uri.startswith("cosmos://"):
        import json

        tool = "beastbox_get_status"
        argument: dict[str, str] = {}
        mapping = {
            "cosmos://evidence/status": "beastbox_get_status",
            "cosmos://evidence/architecture": "beastbox_get_architecture",
            "cosmos://evidence/models": "beastbox_list_models",
            "cosmos://evidence/senses": "beastbox_get_sensory_status",
            "cosmos://evidence/ci": "beastbox_get_ci",
        }
        if uri in mapping:
            tool = mapping[uri]
        elif uri.startswith("cosmos://evidence/research/"):
            experiment = uri.removeprefix("cosmos://evidence/research/")
            if experiment not in RESEARCH:
                return None
            tool = "beastbox_get_research"
            argument = {"experiment": experiment}
        elif uri.startswith("cosmos://invariant/"):
            tool = "beastbox_get_status"
        else:
            return None
        body = {
            "pointer": True,
            "call": tool,
            "arguments": argument,
            "note": "This resource selects evidence. It is not a stored measurement.",
        }
        return {"uri": uri, "mimeType": "application/json", "text": json.dumps(body)}
    return None


def _result(request_id: object, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: object, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
