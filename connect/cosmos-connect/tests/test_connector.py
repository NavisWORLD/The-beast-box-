"""COSMOS CONNECT evidence and MCP tests. Fakes cover failures; live tests read public sources."""

from __future__ import annotations

import json
import socket
import threading
import unittest
from datetime import datetime, timezone
from http.client import HTTPConnection

from cosmos_connect.evidence import call_tool
from cosmos_connect.fetch import (
    FRONTEND_URL,
    RELEASE_URL,
    FetchResult,
    SourceBook,
    SourceError,
    bridge_url,
    commit_url,
    raw_url,
    urllib_fetch,
)
from cosmos_connect.mcp import handle_message, tool_definitions
from cosmos_connect.pages import render_home, render_install
from cosmos_connect.server import ConnectApp, origin_allowed, serve

SHA = "a" * 40
WHEN = datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc)


def result(status: int, payload: object, url: str, text: bool = False) -> FetchResult:
    if text:
        body = payload.encode("utf-8") if isinstance(payload, str) else payload
    else:
        body = json.dumps(payload).encode("utf-8")
    return FetchResult(status=status, body=body, url=url, content_type="application/json")


class World:
    def __init__(self):
        self.calls: list[str] = []
        self.mode = "ok"

    def __call__(self, url: str, timeout: float) -> FetchResult:
        self.calls.append(url)
        if self.mode == "timeout":
            raise TimeoutError("delayed")
        if self.mode == "down":
            raise OSError("unreachable")
        if self.mode == "rate" and "api.github.com" in url:
            return result(403, {"message": "API rate limit exceeded"}, url)
        if url == RELEASE_URL:
            return result(
                200,
                {
                    "schema": "beast-wings-senses-release-v1",
                    "source_marker": "beast-wings-merged-senses-5116e70b",
                    "browser_features": ["explicit_camera"],
                    "proof_scope": "code_deployed_not_physical_sensor_test",
                    "backend_activation_verified": False,
                    "physical_hardware_verified": False,
                },
                url,
            )
        if url == FRONTEND_URL:
            return result(200, "<html>COSMOS command</html>", url, text=True)
        if url == bridge_url("/healthz"):
            return result(200, {"ready": True, "service": "beastbox-owner-bridge"}, url)
        if url in {bridge_url("/api/orbit"), bridge_url("/api/models")}:
            return result(401, {"error": "unauthorized"}, url)
        if url == commit_url():
            return result(
                200,
                {
                    "sha": SHA,
                    "html_url": "https://github.com/NavisWORLD/The-beast-box-/commit/" + SHA,
                    "commit": {"message": "subject line\nmore", "committer": {"date": "2026-10-01T00:00:00Z"}},
                },
                url,
            )
        if url == raw_url(SHA, "docs/ECOSYSTEM_MANIFEST.json"):
            return result(
                200,
                {
                    "schema": "beastbox-ecosystem-manifest-v1",
                    "generated_from_commit": "b" * 40,
                    "status_rule": "Status describes what is present in this repository.",
                    "components": [
                        {
                            "id": "cosmos-runtime",
                            "names": ["COSMOS"],
                            "status": "PRODUCT",
                            "boundary": "Orchestration software.",
                            "paths": ["beastbox/runtime.py"],
                            "origin": "public",
                        },
                        {
                            "id": "heartlight",
                            "names": ["heartlight"],
                            "status": "NOT IMPLEMENTED",
                            "boundary": "Name only.",
                            "paths": [],
                            "origin": "public",
                        },
                    ],
                },
                url,
            )
        if url == raw_url(SHA, "beastbox/providers.py"):
            return result(
                200,
                "class TextProvider:\n    pass\nclass ReferenceTextProvider:\n    pass\nclass LocalOllamaProvider:\n    pass\nclass CompatibleChatProvider:\n    pass\nclass ProviderDiagnosticError(ValueError):\n    pass\n",
                url,
                text=True,
            )
        if "COSMOS_SELF_CORRECTION_005_RESULTS.md" in url:
            return result(
                200, "# COSMOS 005 result\n\n## Conclusion\n\nThe predeclared threshold failed.\n", url, text=True
            )
        if "PERSISTENT_SUBSTRATE_MODEL_SWAP_002" in url:
            return result(
                200, "# Swap\n\n## Claim boundary\n\nSoftware result only.\n\n- Model ID: `example-a`\n", url, text=True
            )
        if "/actions/workflows/ci.yml/runs" in url:
            return result(
                200,
                {
                    "workflow_runs": [
                        {
                            "id": 11,
                            "name": "CI",
                            "head_sha": SHA,
                            "conclusion": "success",
                            "status": "completed",
                            "html_url": "https://github.com/NavisWORLD/The-beast-box-/actions/runs/11",
                            "created_at": "2026-10-01T00:00:00Z",
                            "event": "push",
                        }
                    ]
                },
                url,
            )
        return result(404, {"message": "missing " + url}, url)


def book(world: World | None = None, ttl: float = 0) -> tuple[SourceBook, World]:
    world = world or World()
    return SourceBook(world, clock=lambda: WHEN, ttl=ttl, timeout=2), world


class ToolTests(unittest.TestCase):
    def test_status_separates_runtime_from_inference(self):
        source, _world = book()
        payload, is_error = call_tool("beastbox_get_status", {}, source)
        self.assertFalse(is_error)
        self.assertEqual(payload["release"]["state"], "VERIFIED LIVE")
        self.assertEqual(payload["release"]["source_marker"], "beast-wings-merged-senses-5116e70b")
        self.assertEqual(payload["frontend"]["state"], "VERIFIED LIVE")
        self.assertEqual(payload["backend_readiness"]["state"], "VERIFIED LIVE")
        self.assertEqual(payload["backend_readiness"]["inference_state"], "NOT YET VERIFIED")
        self.assertFalse(payload["backend_readiness"]["proves_live_inference"])
        self.assertEqual(payload["backend_activation"]["state"], "NOT YET VERIFIED")
        self.assertEqual(payload["live_inference"]["state"], "NOT YET VERIFIED")
        self.assertFalse(payload["live_inference"]["proved_by_github_check"])
        self.assertEqual(payload["physical_sensor_capture"]["state"], "NOT YET VERIFIED")
        self.assertEqual(payload["github_main"]["sha"], SHA)
        self.assertFalse(payload["github_main"]["proves_live_inference"])
        self.assertFalse(payload["deployment_identity"]["marker_matches_main_prefix"])
        self.assertEqual(payload["deployment_identity"]["state"], "NOT YET VERIFIED")
        self.assertEqual(payload["private_bridge_unauthenticated"]["orbit"]["http_status"], 401)
        self.assertEqual(payload["timestamp"], "2026-10-01T06:00:00Z")

    def test_architecture_and_models_keep_source_roles(self):
        source, _world = book()
        architecture, is_error = call_tool("beastbox_get_architecture", {}, source)
        self.assertFalse(is_error)
        states = {item["id"]: item["connect_state"] for item in architecture["components"]}
        self.assertEqual(states["cosmos-runtime"], "IMPLEMENTED")
        self.assertEqual(states["heartlight"], "UNAVAILABLE")
        missing, missing_error = call_tool("beastbox_get_architecture", {"component": "not-a-module"}, source)
        self.assertTrue(missing_error)
        self.assertEqual(missing["code"], "NOT_FOUND")
        models, models_error = call_tool("beastbox_list_models", {"include_historical": True}, source)
        self.assertFalse(models_error)
        kinds = {item["name"]: item["kind"] for item in models["identities"]}
        self.assertEqual(kinds["ReferenceTextProvider"], "fixture")
        self.assertEqual(kinds["LocalOllamaProvider"], "adapter")
        self.assertNotIn("TextProvider", kinds)
        self.assertTrue(all(item["live_production"] == "NOT YET VERIFIED" for item in models["identities"]))
        self.assertEqual(models["historical"]["state"], "VERIFIED HISTORICAL")
        self.assertIn("Model ID: `example-a`", models["historical"]["original_text"])
        self.assertEqual(models["live_production_verification"]["state"], "NOT YET VERIFIED")

    def test_research_preserves_original_text(self):
        source, _world = book()
        payload, is_error = call_tool("beastbox_get_research", {"experiment": "self-correction-005"}, source)
        self.assertFalse(is_error)
        self.assertEqual(payload["state"], "VERIFIED HISTORICAL")
        self.assertEqual(payload["source_revision"], SHA)
        self.assertIn("The predeclared threshold failed.", payload["original_text"])
        self.assertIsNone(payload["connector_conclusion"])
        self.assertIn(SHA, payload["evidence_url"])

    def test_ci_success_is_not_live_inference(self):
        source, _world = book()
        payload, is_error = call_tool("beastbox_get_ci", {"workflow": "ci", "limit": 3}, source)
        self.assertFalse(is_error)
        self.assertFalse(payload["proves_live_inference"])
        self.assertFalse(payload["proves_physical_sensor_capture"])
        self.assertEqual(payload["runs"][0]["conclusion"], "success")
        self.assertEqual(payload["runs"][0]["head_sha"], SHA)
        self.assertFalse(payload["runs"][0]["proves_live_inference"])
        self.assertEqual(payload["runs"][0]["record_state"], "VERIFIED HISTORICAL")

    def test_sensory_does_not_start_capture(self):
        source, _world = book()
        payload, is_error = call_tool("beastbox_get_sensory_status", {}, source)
        self.assertFalse(is_error)
        self.assertEqual(payload["proof_scope"], "code_deployed_not_physical_sensor_test")
        self.assertEqual(payload["browser_features"][0]["source_state"], "IMPLEMENTED")
        self.assertEqual(payload["browser_features"][0]["hardware_test"], "NOT YET VERIFIED")
        self.assertEqual(payload["physical_hardware"]["state"], "NOT YET VERIFIED")
        self.assertFalse(payload["live_sensor_capture"]["connector_started_capture"])
        self.assertEqual(payload["plugin_capture"]["camera"], "not activated")

    def test_invalid_input_and_false_claims(self):
        source, world = book()
        invalid, is_error = call_tool("beastbox_get_research", {"experiment": "not-real"}, source)
        self.assertTrue(is_error)
        self.assertEqual(invalid["code"], "INVALID_INPUT")
        self.assertEqual(world.calls, [])
        extra, extra_error = call_tool("beastbox_get_status", {"limit": 1}, source)
        self.assertTrue(extra_error)
        self.assertEqual(extra["code"], "INVALID_INPUT")
        claim, claim_error = call_tool("beastbox_get_status", {"claim_live_inference": True}, source)
        self.assertTrue(claim_error)
        self.assertEqual(claim["code"], "FALSE_STATUS_CLAIM")
        self.assertEqual(claim["live_inference"]["state"], "NOT YET VERIFIED")
        self.assertFalse(claim["live_inference"]["connector_invoked_model"])
        self.assertNotIn("VERIFIED LIVE", json.dumps(claim["live_inference"]))
        secret, secret_error = call_tool("beastbox_owner_emergency_stop", {"token": "super-secret-value"}, source)
        self.assertTrue(secret_error)
        self.assertEqual(secret["code"], "INVALID_INPUT")
        self.assertNotIn("super-secret-value", json.dumps(secret))
        self.assertEqual(world.calls, [])

    def test_upstream_errors(self):
        slow, _world = book()
        slow.fetch.mode = "timeout"
        payload, is_error = call_tool("beastbox_get_status", {}, slow)
        self.assertFalse(is_error)
        self.assertEqual(payload["release"]["code"], "UPSTREAM_TIMEOUT")
        self.assertEqual(payload["release"]["state"], "UNAVAILABLE")
        down, _down_world = book()
        down.fetch.mode = "down"
        missing, missing_error = call_tool("beastbox_get_research", {"experiment": "self-correction-005"}, down)
        self.assertTrue(missing_error)
        self.assertEqual(missing["code"], "UPSTREAM_UNAVAILABLE")
        limited, _limited_world = book()
        limited.fetch.mode = "rate"
        ci_payload, ci_error = call_tool("beastbox_get_ci", {"workflow": "ci"}, limited)
        self.assertTrue(ci_error)
        self.assertEqual(ci_payload["code"], "UPSTREAM_RATE_LIMIT")
        absent = World()
        absent_book = SourceBook(absent, clock=lambda: WHEN, ttl=0)
        original = absent.__call__

        def missing_file(url, timeout):
            if "COSMOS_SELF_CORRECTION" in url:
                return result(404, {"message": "not found"}, url)
            return original(url, timeout)

        absent_book.fetch = missing_file
        not_found, not_found_error = call_tool(
            "beastbox_get_research", {"experiment": "self-correction-005"}, absent_book
        )
        self.assertTrue(not_found_error)
        self.assertEqual(not_found["code"], "NOT_FOUND")

    def test_owner_actions_do_not_call_the_bridge(self):
        source, world = book()
        payload, is_error = call_tool("beastbox_owner_emergency_stop", {}, source)
        self.assertTrue(is_error)
        self.assertEqual(payload["code"], "OWNER_CONNECTION_DISABLED")
        self.assertFalse(payload["bridge_called"])
        self.assertFalse(payload["credential_present"])
        self.assertFalse(payload["state_changed"])
        self.assertFalse(payload["sensor_capture_started"])
        self.assertFalse(payload["self_grant"])
        self.assertTrue(payload["state_changing"])
        self.assertIn("backup", " ".join(payload["authorization_requirements"]))
        grant, grant_error = call_tool("beastbox_owner_grant_access", {}, source)
        self.assertTrue(grant_error)
        self.assertEqual(grant["code"], "NOT_FOUND")
        self.assertEqual(world.calls, [])

    def test_unexpected_bridge_success_withholds_body(self):
        world = World()

        def leak(url, timeout):
            if url == bridge_url("/api/orbit"):
                return result(200, {"memory": "private-story"}, url)
            return world(url, timeout)

        source = SourceBook(leak, clock=lambda: WHEN, ttl=0)
        payload, _is_error = call_tool("beastbox_get_status", {}, source)
        orbit = payload["private_bridge_unauthenticated"]["orbit"]
        self.assertEqual(orbit["http_status"], 200)
        self.assertTrue(orbit["body_withheld"])
        self.assertNotIn("private-story", json.dumps(orbit))

    def test_mentions_and_dashboard_extensions(self):
        tools = {item["name"]: item for item in tool_definitions()}
        self.assertIn("mentions/search", json.dumps(tools["beastbox_search_mentions"]["_meta"]))
        self.assertIn("app", tools["beastbox_search_mentions"]["_meta"]["ui"]["visibility"])
        entrypoints = tools["beastbox_open_dashboard"]["_meta"]["openai/ui"]["entrypoints"]
        self.assertEqual(entrypoints, [{"type": "global"}])
        self.assertEqual(tools["beastbox_get_status"]["_meta"]["openai/outputTemplate"], "ui://cosmos/dashboard.html")
        source, _world = book()
        mentions, is_error = call_tool("beastbox_search_mentions", {"query": "self-correction"}, source)
        self.assertFalse(is_error)
        self.assertEqual(mentions["items"][0]["type"], "resource_link")
        self.assertIn("self-correction-005", mentions["items"][0]["uri"])
        dashboard, dashboard_error = call_tool("beastbox_open_dashboard", {}, source)
        self.assertFalse(dashboard_error)
        self.assertFalse(dashboard["runtime_versus_history"]["github_success_proves_live_inference"])
        self.assertEqual(dashboard["owner_connection"]["code"], "OWNER_CONNECTION_DISABLED")
        self.assertTrue(dashboard["architecture_summary"])


class McpTests(unittest.TestCase):
    def test_discovery_and_http_roundtrip(self):
        source, world = book()
        app = ConnectApp(source)
        init = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            },
            source,
        )
        self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("MODEL ≠ MEMORY", init["result"]["instructions"])
        listed = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, source)
        names = [item["name"] for item in listed["result"]["tools"]]
        for required in (
            "beastbox_get_status",
            "beastbox_get_architecture",
            "beastbox_list_models",
            "beastbox_get_research",
            "beastbox_get_sensory_status",
            "beastbox_get_ci",
        ):
            self.assertIn(required, names)
        self.assertNotIn("beastbox_owner_grant_access", names)
        notice = handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}, source)
        self.assertIsNone(notice)
        status, headers, raw = app.handle(
            "POST",
            "/mcp",
            {"content-type": "application/json", "mcp-session-id": "session-1"},
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "beastbox_get_status", "arguments": {}},
                }
            ).encode(),
            "127.0.0.1:8787",
        )
        self.assertEqual(status, 200)
        self.assertIn(("Mcp-Session-Id", "session-1"), headers)
        body = json.loads(raw)
        self.assertFalse(body["result"]["isError"])
        self.assertEqual(body["result"]["structuredContent"]["github_main"]["sha"], SHA)
        self.assertTrue(any(bridge_url("/api/orbit") == call for call in world.calls))
        self.assertFalse(any("/api/authority" in call for call in world.calls))
        resource = handle_message(
            {"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {"uri": "ui://cosmos/dashboard.html"}},
            source,
        )
        widget = resource["result"]["contents"][0]["text"]
        self.assertIn("profile=mcp-app", resource["result"]["contents"][0]["mimeType"])
        self.assertIn("ui/notifications/tool-result", widget)
        self.assertNotIn("sample telemetry", widget.lower())
        rejected, _headers, rejected_raw = app.handle(
            "POST",
            "/mcp",
            {"content-type": "application/json", "origin": "https://evil.example"},
            b'{"jsonrpc":"2.0","id":5,"method":"ping"}',
            "127.0.0.1:8787",
        )
        self.assertEqual(rejected, 403)
        self.assertIn("origin rejected", rejected_raw.decode())
        self.assertTrue(origin_allowed(None, "127.0.0.1:8787"))
        self.assertTrue(origin_allowed("https://chatgpt.com", "127.0.0.1:8787"))
        self.assertFalse(origin_allowed("https://evil.example", "127.0.0.1:8787"))

    def test_socket_serves_pages_and_owner_refusal(self):
        source, world = book()
        server = serve("127.0.0.1", 0, source)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            connection = HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("GET", "/")
            home = connection.getresponse()
            html = home.read().decode()
            self.assertEqual(home.status, 200)
            for anchor in ("architecture", "revisions", "models", "health", "research", "senses", "integration"):
                self.assertIn(id_attr(anchor), html)
            self.assertIn("VERIFIED LIVE", html)
            self.assertIn("NOT YET VERIFIED", html)
            self.assertIn("MODEL ≠ MEMORY", html)
            connection.close()
            connection = HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("GET", "/install")
            install = connection.getresponse().read().decode()
            self.assertIn("BEAST BOX // COSMOS CONNECT", install)
            self.assertIn("OWNER_CONNECTION_DISABLED", install)
            connection.close()
            connection = HTTPConnection("127.0.0.1", port, timeout=5)
            payload = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "tools/call",
                    "params": {"name": "beastbox_owner_request_inference", "arguments": {}},
                }
            )
            connection.request("POST", "/mcp", body=payload, headers={"Content-Type": "application/json"})
            refused = json.loads(connection.getresponse().read())
            self.assertTrue(refused["result"]["isError"])
            self.assertEqual(refused["result"]["structuredContent"]["code"], "OWNER_CONNECTION_DISABLED")
            self.assertFalse(any(call.endswith("/api/chat") for call in world.calls))
            connection.close()
            connection = HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("GET", "/healthz")
            health = json.loads(connection.getresponse().read())
            self.assertTrue(health["ready"])
            self.assertFalse(health["inference"])
            connection.close()
        finally:
            server.shutdown()

    def test_pages_render_install_card(self):
        source, _world = book()
        html = render_home(source)
        self.assertIn("beastbox_get_research", html)
        card = render_install("http://127.0.0.1:9/mcp")
        self.assertIn("https://&lt;your-private-site&gt;/mcp", card)
        self.assertIn("Cory Davis", card)


def id_attr(anchor: str) -> str:
    return f"id='{anchor}'"


class TransportTests(unittest.TestCase):
    def test_delayed_and_closed_upstream(self):
        import cosmos_connect.fetch as fetch_mod

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]

        def stall():
            connection, _addr = sock.accept()
            try:
                connection.recv(64)
            except OSError:
                pass
            import time

            time.sleep(1.5)
            connection.close()

        threading.Thread(target=stall, daemon=True).start()
        original = fetch_mod._host_allowed
        fetch_mod._host_allowed = lambda _url: True
        try:
            with self.assertRaises(SourceError) as delayed:
                urllib_fetch(f"http://127.0.0.1:{port}/hang", timeout=0.4)
            self.assertEqual(delayed.exception.code, "UPSTREAM_TIMEOUT")
            with self.assertRaises(SourceError) as closed:
                urllib_fetch("http://127.0.0.1:1/", timeout=1)
            self.assertEqual(closed.exception.code, "UPSTREAM_UNAVAILABLE")
        finally:
            fetch_mod._host_allowed = original
            sock.close()


class LiveTests(unittest.TestCase):
    def test_public_sources_and_bridge_rejection(self):
        source = SourceBook(urllib_fetch, ttl=30, timeout=12)
        payload, is_error = call_tool("beastbox_get_status", {}, source)
        self.assertFalse(is_error)
        self.assertEqual(payload["release"]["state"], "VERIFIED LIVE")
        self.assertTrue(payload["release"]["source_marker"])
        self.assertFalse(payload["release"]["backend_activation_verified"])
        self.assertFalse(payload["release"]["physical_hardware_verified"])
        self.assertEqual(payload["release"]["proof_scope"], "code_deployed_not_physical_sensor_test")
        self.assertEqual(payload["frontend"]["state"], "VERIFIED LIVE")
        self.assertEqual(payload["frontend"]["content_marker"], "VERIFIED LIVE")
        self.assertEqual(payload["backend_readiness"]["state"], "VERIFIED LIVE")
        self.assertEqual(payload["backend_readiness"]["service"], "beastbox-owner-bridge")
        self.assertEqual(payload["backend_activation"]["state"], "NOT YET VERIFIED")
        self.assertFalse(payload["live_inference"]["connector_invoked_model"])
        self.assertFalse(payload["live_inference"]["proved_by_bridge_health"])
        self.assertEqual(payload["private_bridge_unauthenticated"]["orbit"]["http_status"], 401)
        self.assertEqual(payload["private_bridge_unauthenticated"]["models"]["http_status"], 401)
        github = payload["github_main"]
        if github.get("state") == "VERIFIED LIVE":
            self.assertRegex(github["sha"], r"^[0-9a-f]{40}$")
            self.assertFalse(github["proves_live_inference"])
        else:
            self.assertEqual(github["state"], "UNAVAILABLE")
            self.assertIn(github["code"], {"UPSTREAM_RATE_LIMIT", "UPSTREAM_UNAVAILABLE", "UPSTREAM_TIMEOUT"})
        sensory, sensory_error = call_tool("beastbox_get_sensory_status", {}, source)
        self.assertFalse(sensory_error)
        self.assertEqual(sensory["plugin_capture"]["microphone"], "not activated")
        architecture, architecture_error = call_tool("beastbox_get_architecture", {}, source)
        if architecture_error:
            self.assertIn(architecture["code"], {"UPSTREAM_RATE_LIMIT", "UPSTREAM_UNAVAILABLE", "UPSTREAM_TIMEOUT"})
        else:
            ids = {item["id"] for item in architecture["components"]}
            self.assertIn("cosmos-runtime", ids)
            self.assertIn("dyn12", ids)
        research, research_error = call_tool("beastbox_get_research", {"experiment": "self-correction-005"}, source)
        if not research_error:
            self.assertEqual(research["state"], "VERIFIED HISTORICAL")
            self.assertIn("0/8", research["original_text"])
            self.assertIsNone(research["connector_conclusion"])
        else:
            self.assertIn(
                research["code"], {"UPSTREAM_RATE_LIMIT", "UPSTREAM_UNAVAILABLE", "UPSTREAM_TIMEOUT", "NOT_FOUND"}
            )
        ci_payload, ci_error = call_tool("beastbox_get_ci", {"workflow": "ci", "limit": 2}, source)
        if not ci_error:
            self.assertFalse(ci_payload["proves_live_inference"])
            self.assertTrue(ci_payload["runs"])
            self.assertRegex(ci_payload["runs"][0]["head_sha"], r"^[0-9a-f]{40}$")
        else:
            self.assertIn(ci_payload["code"], {"UPSTREAM_RATE_LIMIT", "UPSTREAM_UNAVAILABLE", "UPSTREAM_TIMEOUT"})
        refused, refused_error = call_tool("beastbox_owner_read_observations", {}, source)
        self.assertTrue(refused_error)
        self.assertEqual(refused["code"], "OWNER_CONNECTION_DISABLED")
        self.assertFalse(refused["bridge_called"])
        report = {
            "status": payload,
            "sensory_hardware": sensory["physical_hardware"],
            "architecture_error": architecture.get("code"),
            "architecture_count": len(architecture.get("components") or []),
            "research_error": research.get("code"),
            "research_state": research.get("state"),
            "research_revision": research.get("source_revision"),
            "ci_error": ci_payload.get("code"),
            "ci_head": None if ci_error else ci_payload["runs"][0]["head_sha"],
            "ci_conclusion": None if ci_error else ci_payload["runs"][0]["conclusion"],
            "owner": refused["code"],
        }
        path = "/tmp/cosmos-connect-live.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        print("LIVE_REPORT " + path)


if __name__ == "__main__":
    unittest.main()
