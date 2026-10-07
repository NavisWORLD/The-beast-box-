import pytest

import fakes

from beastbox_musegadget import commands
from beastbox_musegadget.mcp_client import McpClient, McpError, endpoint

BEAST = {"name": "Glacecoil", "species": "serpent", "mood": "happy", "stage": 2}


def tools(log):
    def tool(name, data):
        def call(args):
            log.append((name, args))
            return data
        return call
    return {
        "get_beast": tool("get_beast", BEAST),
        "get_care_status": tool("get_care_status", {"hunger": "full"}),
        "feed_beast": tool("feed_beast", {"ok": True, "beast": {**BEAST, "mood": "evolve"}}),
        "play_with_beast": tool("play_with_beast", {"ok": True}),
        "talk_to_beast": tool("talk_to_beast", {"reply": "rim? hi"}),
        "list_moves": tool("list_moves", {"moves": [{"name": "Rime Lance"}]}),
        "get_lost_cosmos_progress": tool("get_lost_cosmos_progress", {"chapter": 3}),
    }


def test_endpoint_normalization():
    assert endpoint("https://x.example") == "https://x.example/api/mcp"
    assert endpoint("https://x.example/api/mcp/") == "https://x.example/api/mcp"


@pytest.mark.parametrize("sse", [False, True])
def test_client_initializes_then_calls_tools(sse):
    log = []
    with fakes.mcp(tools(log), sse=sse) as server:
        client = McpClient(server.url, "secret-token")
        assert client.call_tool("get_beast") == BEAST
        assert client.call_tool("talk_to_beast", {"message": "hi"}) == {"reply": "rim? hi"}
        methods = [c.get("method") for c in server.calls]
    assert methods[:3] == ["initialize", "notifications/initialized", "tools/call"]
    assert client.session_id == "sess-1"
    assert log == [("get_beast", {}), ("talk_to_beast", {"message": "hi"})]


def test_client_errors():
    with fakes.mcp({}) as server:
        with pytest.raises(McpError, match="401"):
            McpClient(server.url, "wrong").call_tool("get_beast")
        with pytest.raises(McpError, match="unknown tool"):
            McpClient(server.url, "secret-token").call_tool("get_beast")


def test_router_prefers_the_connector_over_the_gadget_copy(cfg):
    log = []
    with fakes.mcp(tools(log)) as server:
        cfg.beastbox_url, cfg.beastbox_token = server.url, "secret-token"
        status = commands.handle("beastbox.status", {}, cfg)
        fed = commands.handle("beastbox.feed", {"food": "kelp"}, cfg)
        attack = commands.handle("beastbox.attack", {}, cfg)
    assert status["payload"]["source"] == "Beast Box connector"
    assert status["payload"]["result"] == BEAST and status["payload"]["care"] == {"hunger": "full"}
    assert fed["payload"]["result"]["beast"]["mood"] == "evolve"
    assert ("feed_beast", {"food": "kelp"}) in log
    assert "no attack tool" in attack["payload"]["result"]["note"]


def test_router_falls_back_when_the_connector_is_down(cfg):
    with fakes.mcp({}) as server:
        cfg.beastbox_url, cfg.beastbox_token = server.url, "wrong-token"
        out = commands.handle("beastbox.status", {}, cfg)
    assert out["ok"] and "saved copy" in out["payload"]["source"]
    assert any("401" in note for note in out["payload"]["notes"])
