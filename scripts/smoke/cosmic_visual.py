"""Real-browser layout checks for both clients; reference data is temporary."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import threading

from playwright.sync_api import expect, sync_playwright

from beastbox.cosmic_web import CosmicApp, CosmicHTTPServer, _CosmicHandler
from html_browser import start_server, stop_server


OUTPUT = Path("build/cosmic-visual")
SIZES = [(1440, 1), (768, 1), (390, 1), (320, 1), (1440, 2), (390, 2), (320, 2)]


def check_layout(page, client: str, width: int, scale: int, checks: list) -> None:
    page.set_viewport_size({"width": width, "height": 1000})
    page.evaluate("(scale) => document.documentElement.style.fontSize = (100 * scale) + '%'", scale)
    views = page.locator("#nav button").evaluate_all("(nodes) => nodes.map(n => n.dataset.view)")
    for view in views:
        button = page.locator(f'#nav button[data-view="{view}"]')
        button.click()
        panel = page.locator(f"#{view}" if client == "console" else f"#view-{view}")
        expect(panel).to_be_visible()
        expect(button).to_have_attribute("aria-current", "page")
        expect(page.locator('#nav [aria-current="page"]')).to_have_count(1)
        size = page.evaluate("({width: innerWidth, scroll: document.documentElement.scrollWidth})")
        if size["scroll"] > size["width"]:
            offenders = page.locator("main *").evaluate_all("""(nodes) => nodes.filter(n => {
                const r=n.getBoundingClientRect(); return r.width && (r.right > innerWidth + 1 || r.left < -1);
            }).slice(0,12).map(n => ({tag:n.tagName,id:n.id,cls:n.className,
                rect:n.getBoundingClientRect().toJSON()}))""")
            raise AssertionError((client, width, scale, view, size, offenders))
        if client == "console" and view == "orbit":
            core = page.locator(".map-core").bounding_box()
            caption = page.locator(".map-caption").bounding_box()
            assert core and caption and caption["y"] >= core["y"] + core["height"], (
                "Checkpoint caption overlaps core", width, scale, core, caption
            )
            for node in page.locator(".map-node, .map-caption").all():
                assert node.evaluate("(n) => n.scrollWidth <= n.clientWidth + 1"), (
                    "Map content clipped", width, scale, node.inner_text()
                )
        if view == "orbit" and (width, scale) in [(1440, 1), (390, 1), (320, 2)]:
            page.evaluate("scrollTo(0, 0)")
            page.mouse.click(1, 1)
            page.screenshot(path=str(OUTPUT / f"{client}-{width}-{scale}.png"), full_page=True)
            page.screenshot(
                path=str(OUTPUT / f"{client}-{width}-{scale}.jpg"),
                type="jpeg", quality=65, full_page=False,
            )
        checks.append({"client": client, "width": width, "text_scale": scale, "view": view, "passed": True})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inline-previews", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        console = CosmicHTTPServer(("127.0.0.1", 0), _CosmicHandler)
        console.cosmic_app = CosmicApp(root / "console")
        console.session_token = "visual-regression-session"
        thread = threading.Thread(target=console.serve_forever, daemon=True)
        thread.start()
        standalone, standalone_thread = start_server(root / "standalone")
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    for client, url, ready in [
                        ("console", f"http://127.0.0.1:{console.server_port}", "SUBSTRATE VERIFIED"),
                        ("standalone", f"http://127.0.0.1:{standalone.server_port}/html/", "RUNTIME: ONLINE"),
                    ]:
                        page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
                        errors: list[str] = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto(url)
                        expect(page.locator("#runtimePill")).to_have_text(ready)
                        for width, scale in SIZES:
                            check_layout(page, client, width, scale, checks)
                        if client == "console":
                            page.route("**/api/orbit", lambda route: route.abort())
                            expect(page.locator("#runtimePill")).to_have_text("RUNTIME UNAVAILABLE", timeout=10000)
                            expect(page.locator("#runtimeFreshness")).to_contain_text("Last observed")
                            expect(page.locator("#checkpointHelp")).to_contain_text("not reverified")
                            page.unroute("**/api/orbit")
                            page.reload()
                            expect(page.locator("#runtimePill")).to_have_text(ready)
                            expect(page.locator("#runtimeFreshness")).to_contain_text("Last checked")
                            page.set_viewport_size({"width": 390, "height": 844})
                            page.locator('#nav button[data-view="settings"]').click()
                            page.locator("#snapshotHash").fill("invalid")
                            page.locator("#verifySnapshot").click()
                            expect(page.locator("#notice")).to_have_class("notice error")
                            page.evaluate("scrollTo(0, 800)")
                            message = page.locator("#noticeText").bounding_box()
                            rail = page.locator(".rail").bounding_box()
                            assert message and rail and message["y"] >= max(0, rail["y"] + rail["height"]), (
                                "Verification error is obscured", message, rail
                            )
                        assert not errors, errors
                        page.close()
                finally:
                    browser.close()
        finally:
            console.shutdown()
            console.server_close()
            thread.join()
            stop_server(standalone, standalone_thread)
    files = ("beastbox/cosmic_ui.py", "beastbox/ui_theme.css", "beastbox/cosmic_layout.css",
             "html/index.html", "html/app.js", "html/styles.css", "html/standalone.html")
    result = {
        "passed": True,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_sha256": {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in files},
        "checks": checks,
        "additional_checks": ["connection loss and recovery", "mobile verification error visibility"],
        "capture": "Real Chromium and CosmicApp; temporary deterministic reference runtime",
        "physical_devices_validated": False,
        "screenshots": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUTPUT.glob("*.png"))},
    }
    (OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"{len(checks)} responsive checks passed across both clients; 320–1440px and 200% text.")
    if args.inline_previews:
        for name in ("console-1440-1.jpg", "console-390-1.jpg", "console-320-2.jpg", "standalone-1440-1.jpg"):
            data = base64.b64encode((OUTPUT / name).read_bytes()).decode("ascii")
            print(f"BEAST_PREVIEW {name} {data}")


if __name__ == "__main__":
    main()
