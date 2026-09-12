"""Exercise the standalone transport over HTTP, including its browser boundary."""
from __future__ import annotations

import http.client
import importlib.util
import json
from pathlib import Path
import threading

import pytest

from beastbox.cosmic_web import CosmicApp


# The client directory is intentionally not a package: ``html`` belongs to stdlib.
spec = importlib.util.spec_from_file_location(
    "beastbox_html_server", Path(__file__).resolve().parents[1] / "html" / "serve.py"
)
assert spec and spec.loader
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)


@pytest.fixture
def server(tmp_path):
    server = web.Server(("127.0.0.1", 0), web.Handler)
    server.app = CosmicApp(tmp_path / "state")
    server.session = "html-http-regression-session"
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def request(server, path, *, method="GET", body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_html_shell_returns_security_headers_and_session(server):
    status, headers, body = request(server, "/html/")

    assert status == 200
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert b'<script type="module" src="app.js">' in body
    assert "script-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Cache-Control"] == "no-store"
    assert "HttpOnly" in headers["Set-Cookie"]
    assert "SameSite=Strict" in headers["Set-Cookie"]


@pytest.mark.parametrize("path", ["/", "/html"])
def test_entry_aliases_redirect_to_directory_for_relative_assets(server, path):
    status, headers, _ = request(server, path)

    assert status in (301, 302, 307, 308)
    assert headers["Location"] == "/html/"


def test_direct_index_navigation_also_renews_session(server):
    status, headers, _ = request(server, "/html/index.html")

    assert status == 200
    assert "beastbox_session=html-http-regression-session" in headers["Set-Cookie"]


@pytest.mark.parametrize("path,content_type", [
    ("/html/app.js", "javascript"),
    ("/html/styles.css", "text/css"),
    ("/html/manifest.webmanifest", "manifest+json"),
    ("/html/sw.js", "javascript"),
])
def test_browser_assets_have_usable_content_types(server, path, content_type):
    status, headers, body = request(server, path)

    assert status == 200
    assert content_type in headers["Content-Type"]
    assert body


@pytest.mark.parametrize("path", [
    "/html/../pyproject.toml", "/html/%2e%2e/pyproject.toml", "/html/missing.js",
])
def test_missing_assets_and_traversal_do_not_expose_repository_files(server, path):
    status, _, body = request(server, path)

    assert status == 404
    assert json.loads(body) == {"error": "not found"}


@pytest.mark.parametrize("host", ["attacker.example", "127.0.0.1.attacker.example", "localhost@attacker.example", "localhost/path"])
@pytest.mark.parametrize("method,path", [("GET", "/html/"), ("GET", "/api/memory"), ("POST", "/api/chat")])
def test_untrusted_host_cannot_boot_or_read_or_mutate_runtime(server, host, method, path):
    status, headers, body = request(
        server, path, method=method, body='{"text":"must not be stored"}',
        headers={"Host": host, "Cookie": f"beastbox_session={server.session}"},
    )

    assert status == 400
    assert json.loads(body) == {"error": "invalid host"}
    assert "Set-Cookie" not in headers
    assert server.app.service.conversation_history() == []


@pytest.mark.parametrize("cookie", ["", "beastbox_session=wrong", 'beastbox_session="\\377"'])
def test_post_requires_the_current_process_session(server, cookie):
    status, _, body = request(
        server, "/api/chat", method="POST", body='{"text":"must not be stored"}',
        headers={"Cookie": cookie},
    )

    assert status == 403
    assert json.loads(body) == {"error": "invalid session"}
    assert server.app.service.conversation_history() == []


def test_browser_cookie_allows_real_chat_but_preserves_cloud_authority_boundary(server):
    _, headers, _ = request(server, "/html/")
    cookie = headers["Set-Cookie"].split(";", 1)[0]
    status, _, body = request(
        server, "/api/chat", method="POST", body='{"text":"durable html conversation"}',
        headers={"Cookie": cookie, "Content-Type": "application/json"},
    )
    assert status == 200
    assert json.loads(body)["substrate_preserved"] is True
    status, _, body = request(server, "/api/conversation")
    assert status == 200
    assert any(turn["text"] == "durable html conversation" for turn in json.loads(body)["turns"])

    status, _, body = request(
        server, "/api/provider", method="POST",
        body=json.dumps({"kind": "compatible", "model": "blocked-model", "base_url": "https://models.example.test/v1", "allow_remote": True}),
        headers={"Cookie": cookie, "Content-Type": "application/json"},
    )
    assert status == 403
    assert json.loads(body) == {"error": "cloud authority required"}
    assert not any(server.app.authority.snapshot().values())


@pytest.mark.parametrize("origin", ["null", "https://attacker.example", "http://127.0.0.1:1", "http://localhost:1"])
def test_cookie_cannot_authorize_cross_origin_mutations(server, origin):
    status, _, _ = request(
        server, "/api/chat", method="POST", body='{"text":"cross-origin injection"}',
        headers={"Cookie": f"beastbox_session={server.session}", "Content-Type": "application/json", "Origin": origin},
    )
    assert status == 403
    assert server.app.service.conversation_history() == []


@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data"])
def test_simple_form_requests_cannot_mutate_runtime_with_a_cookie(server, content_type):
    status, _, _ = request(
        server, "/api/chat", method="POST", body='{"text":"form injection"}',
        headers={"Cookie": f"beastbox_session={server.session}", "Content-Type": content_type},
    )
    assert status == 415
    assert server.app.service.conversation_history() == []
