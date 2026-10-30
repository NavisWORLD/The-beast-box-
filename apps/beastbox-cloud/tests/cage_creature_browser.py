"""Creature switch acceptance (390 px and desktop): default ON, off hides the front creature, remembered, same state on / and /beast-cage.
Usage: python tests/cage_creature_browser.py [base]"""
import os, sys
from playwright.sync_api import sync_playwright, expect
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3100").rstrip("/")
failures = []
def check(c, m):
    if not c: failures.append(m); print("FAIL", m, flush=True)
KEY = "beastbox.cage.creature.v1"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("PW_CHROME") or os.environ.get("CHROME_PATH") or None, args=["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    for label, vp, mobile in (("phone", {"width": 390, "height": 844}, True), ("desktop", {"width": 1280, "height": 900}, False)):
        ctx = b.new_context(viewport=vp, is_mobile=mobile, has_touch=mobile, device_scale_factor=2 if mobile else 1)
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
        page = ctx.new_page(); errs = []
        page.on("pageerror", lambda e: errs.append(str(e)[:160]))
        page.goto(BASE + "/", wait_until="load", timeout=60000)
        sw = page.locator('[data-cage-creature-switch="home"] button'); expect(sw).to_have_count(1, timeout=20000)
        sw.scroll_into_view_if_needed(); page.wait_for_timeout(800)
        bb = sw.bounding_box(); check(bb["height"] >= 43.5, f"{label}: switch is 44 px tall")
        check(sw.get_attribute("role") == "switch", f"{label}: role=switch")
        check((sw.inner_text() or "").strip() == "Creature", f"{label}: visible word is Creature")
        check(sw.get_attribute("aria-checked") == "true", f"{label}: default ON")
        check((sw.get_attribute("aria-label") or "").startswith("Show ") and "front of the screen" in sw.get_attribute("aria-label"), f"{label}: aria label when on")
        check(page.evaluate("document.documentElement.dataset.cageCreature") == "on", f"{label}: html marker on")
        front = page.locator(".beast-landing-creature")
        check(front.is_visible(), f"{label}: front creature visible by default")
        state_on = page.locator('[data-cage-creature-switch="home"] .ccs-state').inner_text()
        check(state_on.endswith("is out front"), f"{label}: state line on: {state_on}")
        sw.click(); page.wait_for_timeout(500)
        check(sw.get_attribute("aria-checked") == "false", f"{label}: switch flips off")
        check((sw.get_attribute("aria-label") or "").startswith("Show "), f"{label}: aria label when off")
        check(not front.is_visible(), f"{label}: front creature hidden when off")
        check(page.evaluate(f"localStorage.getItem('{KEY}')") == "off", f"{label}: saved locally")
        check(page.locator('[data-cage-creature-switch="home"] .ccs-state').inner_text().endswith("is back inside the cage"), f"{label}: state line off")
        page.reload(wait_until="load"); page.wait_for_timeout(1500)
        check(page.locator('[data-cage-creature-switch="home"] button').get_attribute("aria-checked") == "false", f"{label}: remembered after reload")
        page.goto(BASE + "/beast-cage", wait_until="load", timeout=60000); page.wait_for_timeout(1500)
        cs = page.locator('[data-cage-creature-switch="cage"] button'); expect(cs).to_have_count(1, timeout=20000)
        check(cs.get_attribute("aria-checked") == "false", f"{label}: Beast Cage page shares the saved OFF")
        page.wait_for_function("document.documentElement.dataset.cageCreature==='off'", timeout=15000); page.wait_for_timeout(500)
        check(page.locator('.cage-habitat-visual [data-beast-arena]').count() == 0 or not page.locator('.cage-habitat-visual [data-beast-arena]').first.is_visible(), f"{label}: cage overlay creature hidden when off")
        cs.scroll_into_view_if_needed(); cs.click(); page.wait_for_timeout(400)
        check(page.evaluate(f"localStorage.getItem('{KEY}')") == "on", f"{label}: Beast Cage switch turns it back on")
        page.goto(BASE + "/", wait_until="load", timeout=60000); page.wait_for_timeout(1200)
        check(page.locator('.beast-landing-creature').is_visible(), f"{label}: creature back after on")
        check(not errs, f"{label}: page errors {errs}")
        ctx.close()
    b.close()
if failures: print(f"CAGE_CREATURE_BROWSER_FAIL {len(failures)}"); sys.exit(1)
print("CAGE_CREATURE_BROWSER_PASS default ON; off hides the front creature; remembered; same state on / and /beast-cage; 390px and desktop")
