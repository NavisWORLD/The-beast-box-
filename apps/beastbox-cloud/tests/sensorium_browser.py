"""App-shell sensorium stays off for anyone who is not the consented owner.

Default behavior: no capture chrome on the shell, Share World still present,
and this script never types into chat. Physical iPhone capture, a second-tab
election, and a live owner consent session are not claimed here.
"""
import os
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3100"
ROUTES = ("/", "/beast-cage/world", "/workspace", "/beast-cage/field")
VIEWPORTS = ((1280, 800), (390, 844))


def main():
    launch = {"headless": True, "args": ["--no-sandbox"]}
    if os.environ.get("SUPPORT_BROWSER_EXECUTABLE"):
        launch["executable_path"] = os.environ["SUPPORT_BROWSER_EXECUTABLE"]
    else:
        launch["channel"] = "chrome"
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**launch)
        try:
            for width, height in VIEWPORTS:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                    is_mobile=width < 500,
                    has_touch=width < 500,
                )
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                for route in ROUTES:
                    response = page.goto(BASE + route, wait_until="domcontentloaded")
                    assert response is not None and response.status == 200, (route, None if response is None else response.status)
                    page.wait_for_timeout(300)
                    assert page.locator("[data-sensorium]").count() == 0, f"{route} showed the sensorium at {width}"
                    assert page.locator("[data-sensorium-indicator]").count() == 0
                    assert page.locator("[data-share-world]").count() == 1, route
                    assert page.locator("[data-share-toggle]").count() == 1, route
                context.close()
        finally:
            browser.close()
    assert not errors, errors
    print("sensorium shell stays dark on home, world, workspace, and field")


if __name__ == "__main__":
    main()
