"""Real Chromium checks for the standalone HTML client and canonical runtime."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import secrets
import statistics
import tempfile
import threading
import time
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from beastbox.cosmic_web import CosmicApp


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("beastbox_html_server", ROOT / "html" / "serve.py")
assert spec and spec.loader
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)


def start_server(directory: Path, port: int = 0):
    server = web.Server(("127.0.0.1", port), web.Handler)
    server.app = CosmicApp(directory)
    server.session = secrets.token_urlsafe(32)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    return server, thread


def stop_server(server, thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join()


def send(page, text: str) -> None:
    page.locator("#chatInput").fill(text)
    with page.expect_response(lambda response: urlsplit(response.url).path == "/api/chat" and response.request.method == "POST") as pending:
        page.locator("#chatForm button").click()
    assert pending.value.status == 200, pending.value.text()
    expect(page.locator("#chatForm button")).to_be_enabled()


def measure(playwright, server) -> dict:
    # Isolate client request fan-out from the service worker; full smoke covers it.
    for number in range(12):
        assert server.app.dispatch("POST", "/api/chat", {"text": f"Reference history entry {number}"})[0] == 200
    browser = playwright.chromium.launch()
    try:
        page = browser.new_page(service_workers="block", viewport={"width": 800, "height": 1000})
        responses = []

        def received(response):
            path = urlsplit(response.url).path
            if response.request.method == "GET" and (path.startswith("/api/") or path == "/healthz"):
                responses.append(response)

        def summary():
            return {
                "get_count": len(responses),
                "get_paths": sorted(urlsplit(response.url).path for response in responses),
                "get_response_bytes": sum(len(response.body()) for response in responses),
            }

        page.on("response", received)
        page.goto(f"http://127.0.0.1:{server.server_port}/html/")
        expect(page.locator("#runtimePill")).to_have_text("RUNTIME: ONLINE")
        initial_load = summary()
        samples = []
        for number in range(5):
            responses.clear()
            started = time.perf_counter()
            send(page, f"Measured reference message {number}")
            elapsed = time.perf_counter() - started
            samples.append({
                **summary(),
                "chat_to_render_ms": round(elapsed * 1000, 3),
            })
        return {
            "browser_version": browser.version,
            "methodology": "Fixed current HTTP transport and backend; selected old/new client assets; service workers blocked; response body bytes exclude headers and POST; UI wall times include automation and are secondary.",
            "seeded_chats": 12,
            "initial_load": initial_load,
            "samples": samples,
            "median_get_response_bytes": statistics.median(s["get_response_bytes"] for s in samples),
            "median_chat_to_render_ms": statistics.median(s["chat_to_render_ms"] for s in samples),
        }
    finally:
        browser.close()


def smoke(playwright, directory: Path, output: Path, server, thread) -> tuple[dict, object, object]:
    browser = playwright.chromium.launch()
    try:
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        url = f"http://127.0.0.1:{server.server_port}/html/"
        page.goto(url)
        expect(page.locator("#runtimePill")).to_have_text("RUNTIME: ONLINE")
        page.evaluate("navigator.serviceWorker.ready")
        page.wait_for_function("navigator.serviceWorker.controller !== null")
        # Populate a previous live snapshot before testing mutations under SW control.
        page.reload()
        expect(page.locator("#runtimePill")).to_have_text("RUNTIME: ONLINE")
        identity = page.locator("#systemId").inner_text()
        send(page, "Remember the observatory code is marigold")
        expect(page.locator("#chatlog")).to_contain_text("observatory code is marigold")
        expect(page.locator("#turnCount")).to_have_text("2")
        expect(page.locator(".msg.user")).to_have_count(1)
        assert len(server.app.service.conversation_history()) == 2

        def nav(name: str) -> None:
            page.locator(f'#nav button[data-view="{name}"]').click()

        nav("memory")
        expect(page.locator("#memoryList")).to_contain_text("observatory code is marigold")
        nav("trace")
        expect(page.locator("#traceList")).to_contain_text("checkpoint_sha256")
        nav("storage")
        expect(page.locator("#storageInfo")).to_contain_text(identity)
        nav("brain")
        page.locator("#providerModel").fill("Reference Browser B")
        page.locator("#saveProvider").click()
        expect(page.locator("#notice")).to_contain_text("Brain configuration saved")
        expect(page.locator("#mapBrain")).to_have_text("Reference Browser B")
        expect(page.locator("#systemId")).to_have_text(identity)
        assert not any(server.app.authority.snapshot().values())

        page.locator('[data-provider="compatible"]').click()
        page.locator("#providerModel").fill("permission-test-model")
        page.locator("#providerUrl").fill("https://models.example.test/v1")
        page.locator("#saveProvider").click()
        expect(page.locator("#notice")).to_contain_text("cloud authority required")
        assert server.app.profile.kind == "reference"
        assert not any(server.app.authority.snapshot().values())

        # A server restart keeps the story, revokes process authority, and renews the cookie.
        port = server.server_port
        old_session = server.session
        stop_server(server, thread)
        server, thread = start_server(directory, port)
        assert server.session != old_session
        page.reload()
        expect(page.locator("#runtimePill")).to_have_text("RUNTIME: ONLINE")
        expect(page.locator("#systemId")).to_have_text(identity)
        expect(page.locator("#chatlog")).to_contain_text("observatory code is marigold")
        send(page, "What is the observatory code?")
        expect(page.locator("#turnCount")).to_have_text("4")
        assert len(server.app.service.conversation_history()) == 4
        assert not any(server.app.authority.snapshot().values())

        nav("orbit")
        # Delay a genuine pre-mutation history response. It must not overwrite
        # the committed turn returned by a newer chat and history request.
        held = []

        def delay_first_history(route):
            if not held:
                held.append((route, route.fetch()))
                page.locator("#chatlog").evaluate("node => node.dataset.oldHistoryHeld = 'true'")
            else:
                route.continue_()

        page.route("**/api/conversation", delay_first_history)
        page.locator("#refreshChat").click()
        expect(page.locator("#chatlog")).to_have_attribute("data-old-history-held", "true")
        send(page, "Retain this newer history during a delayed refresh")
        expect(page.locator("#turnCount")).to_have_text("6")
        with page.expect_response(lambda response: urlsplit(response.url).path == "/api/conversation"):
            held[0][0].fulfill(response=held[0][1])
        page.evaluate("() => new Promise(requestAnimationFrame)")
        expect(page.locator("#turnCount")).to_have_text("6")
        expect(page.locator("#chatlog")).to_contain_text("Retain this newer history")
        page.unroute("**/api/conversation", delay_first_history)

        # A refused write leaves retained history intact and removes the pending
        # bubble while restoring the input for an explicit owner retry.
        server.session = secrets.token_urlsafe(32)
        page.locator("#chatInput").fill("This rejected turn must not appear in memory")
        with page.expect_response(lambda response: urlsplit(response.url).path == "/api/chat") as denied:
            page.locator("#chatForm button").click()
        assert denied.value.status == 403
        expect(page.locator("#notice")).to_contain_text("invalid session")
        expect(page.locator("#chatForm button")).to_be_enabled()
        expect(page.locator("#turnCount")).to_have_text("6")
        expect(page.locator("#chatlog")).not_to_contain_text("This rejected turn")
        expect(page.locator("#chatInput")).to_have_value("This rejected turn must not appear in memory")
        assert len(server.app.service.conversation_history()) == 6
        page.reload()
        expect(page.locator("#runtimePill")).to_have_text("RUNTIME: ONLINE")

        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=str(output / "orbit-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.evaluate("scrollTo(0, 0)")
        page.screenshot(path=str(output / "orbit-mobile.png"), full_page=True)
        context.set_offline(True)
        page.reload()
        expect(page.locator("#app")).to_be_visible()
        expect(page.locator("#runtimePill")).to_have_text("RUNTIME: OFFLINE")
        expect(page.locator("#notice")).to_contain_text("CANONICAL RUNTIME UNAVAILABLE")
        assert not errors, errors
        return {"passed": True, "browser_version": browser.version, "flows": ["service worker freshness", "durable chat", "memory", "trace", "storage", "provider change", "cloud permission denial", "server restart and session renewal", "delayed refresh race", "denied write recovery", "offline honesty", "390px layout"], "physical_devices_validated": False}, server, thread
    except Exception:
        page.screenshot(path=str(output / "failure.png"), full_page=True)
        raise
    finally:
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ROOT / "html", help="Client assets to compare; transport stays current")
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "html-browser")
    parser.add_argument("--measure-only", action="store_true")
    args = parser.parse_args()
    web.ROOT = args.assets.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary) / "state"
        server, thread = start_server(directory)
        try:
            with sync_playwright() as playwright:
                if args.measure_only:
                    result = measure(playwright, server)
                else:
                    result, server, thread = smoke(playwright, directory, args.output, server, thread)
            result["assets"] = str(web.ROOT)
            result["asset_sha256"] = {name: hashlib.sha256((web.ROOT / name).read_bytes()).hexdigest() for name in ("app.js", "sw.js", "index.html", "styles.css")}
            result["driver_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            result["backend_sha256"] = {
                str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted([ROOT / "html" / "serve.py", *(ROOT / "beastbox").rglob("*.py")])
            }
            result["environment"] = {"python": platform.python_version(), "platform": platform.platform(), "playwright": importlib.metadata.version("playwright")}
            (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result, indent=2))
        finally:
            stop_server(server, thread)


if __name__ == "__main__":
    main()
