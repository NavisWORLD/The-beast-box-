"""Regression check for the COSMIC rail on short desktop viewports."""
from __future__ import annotations

import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scripts.smoke.html_browser import start_server, stop_server


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        server, thread = start_server(Path(temporary) / "state")
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(viewport={"width": 1200, "height": 500})
                    page.goto(f"http://127.0.0.1:{server.server_port}/html/")
                    expect(page.locator("#runtimePill")).to_have_text("RUNTIME: ONLINE")

                    nav = page.locator("#nav").bounding_box()
                    footer = page.locator(".rail-foot").bounding_box()
                    assert nav is not None and footer is not None
                    nav_bottom = nav["y"] + nav["height"]
                    assert nav_bottom <= footer["y"], (
                        f"sidebar footer overlaps navigation at 1200x500: "
                        f"nav bottom={nav_bottom:.1f}, footer top={footer['y']:.1f}"
                    )

                    settings = page.locator('#nav button[data-view="settings"]')
                    settings.click()
                    expect(page.locator("#view-settings")).to_have_class("view active")
                finally:
                    browser.close()
        finally:
            stop_server(server, thread)


if __name__ == "__main__":
    main()
