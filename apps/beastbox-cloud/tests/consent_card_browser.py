"""390 px check of the world-signals consent card (five switches + one camera switch, all OFF by default, short text, confirm sheet, one-tap Stop).
Usage: python tests/consent_card_browser.py [base]   (emulated viewport in headless Chrome; this is NOT a real phone)"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3100").rstrip("/")
OUT = Path("browser-evidence/consent-card"); OUT.mkdir(parents=True, exist_ok=True)
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg); print("FAIL", msg, flush=True)


with sync_playwright() as p:
    import os
    exe = os.environ.get("PW_CHROME") or os.environ.get("CHROME_PATH")
    b = p.chromium.launch(executable_path=exe, args=["--no-sandbox", "--use-gl=swiftshader"]) if exe else p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
    page = ctx.new_page(); errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:160]))
    page.goto(BASE + "/", wait_until="load", timeout=60000); page.wait_for_timeout(2500)
    opener = page.locator("[data-open-environment]").first
    if not opener.count() or not opener.is_visible():
        for sel in ["[aria-label='Open menu']", "[aria-label*='menu' i]", "button:has-text('Menu')"]:
            m = page.locator(sel).first
            if m.count() and m.is_visible():
                m.click(); page.wait_for_timeout(500); break
    page.locator("[data-open-environment]").first.click(); page.wait_for_timeout(800)
    card = page.locator("[data-environment-consent]")
    check(card.count() == 1, "card opens")
    text = card.inner_text()
    for t in ["Give your universe more life", "Off until you turn it on. Stop any time.", "Share my world", "Time of day", "Device motion", "Light level", "Sound level", "Fingertip pulse", "Camera", "Stop sharing", "Stop sharing deletes your saved numbers."]:
        check(t in text, "card text has: " + t)
    rows = page.locator("[data-env-row]"); check(rows.count() == 6, "five switches + one camera switch (got %d)" % rows.count())
    sw = page.locator("[data-env-switch]")
    check(all(not sw.nth(i).is_checked() for i in range(sw.count())), "every switch is OFF by default")
    check(all(sw.nth(i).is_disabled() for i in range(sw.count())), "switches wait for the turn-on confirm")
    check(page.locator("[data-env-learn-more]").get_attribute("href") == "/privacy#labels-and-signals", "Learn more -> /privacy#labels-and-signals")
    lm = page.locator("[data-env-learn-more]").bounding_box(); check(lm and lm["width"] >= 119.5 and lm["height"] >= 43.5, "Learn more is a 120x44 target %s" % lm)
    check(page.locator("[data-env-chips]").count() == 0, "no honesty chips on the card (they live on /privacy)")
    ch = page.evaluate("() => {const c=document.querySelector('[data-environment-consent]');return [c.scrollHeight,c.clientHeight]}"); print('card content/visible height', ch)
    # nothing may overflow sideways on a 390 px phone
    ov = page.evaluate("() => {const c=document.querySelector('[data-environment-consent]');return [c.scrollWidth,c.clientWidth,[...c.querySelectorAll('[data-env-status],[data-env-row] label')].filter(e=>e.getBoundingClientRect().right>innerWidth+0.5||e.getBoundingClientRect().left<-0.5).length]}")
    check(ov[0] <= ov[1] + 1 and ov[2] == 0, "no horizontal overflow %s" % ov)
    small = page.evaluate("() => [...document.querySelectorAll('[data-environment-consent] button')].filter(b=>b.getBoundingClientRect().height<47.5).length")
    check(small == 0, "buttons are >=48 px tall")
    page.screenshot(path=str(OUT / "card-off-390.png"))
    # confirm sheet
    page.locator("[data-environment-consent-toggle]").click(); page.wait_for_timeout(300)
    check(page.locator("[data-env-confirm]").count() == 1 and "Turn on world signals?" in page.locator("[data-env-confirm]").inner_text(), "confirm sheet 'Turn on world signals?'")
    page.screenshot(path=str(OUT / "confirm-390.png"))
    page.locator("[data-env-confirm-no]").click(); page.wait_for_timeout(200)
    check(page.locator("[data-env-confirm]").count() == 0 and page.locator("[data-env-state]").count() == 0, "Not now leaves sharing off")
    page.locator("[data-environment-consent-toggle]").click(); page.locator("[data-env-confirm-yes]").click(); page.wait_for_timeout(500)
    check("Sharing my world" in page.locator("[data-env-state]").inner_text(), "Yes turns sharing on")
    check(not any(sw.nth(i).is_checked() for i in range(sw.count())), "turning sharing on does not turn any switch on")
    st = lambda k: page.locator("[data-env-status=%s]" % k).inner_text()
    check(all(st(k) == "Off" for k in ["time", "motion", "light", "sound", "camera"]), "row status Off before any switch")
    # a visitor cannot read a pulse (the IBM BIO page is owner-only): honest "Not available yet", switch disabled, hint matches
    check(st("pulse") == "Not available yet", "visitor pulse row: Not available yet (got %r)" % st("pulse"))
    check(page.locator("[data-env-switch=pulse]").is_disabled(), "visitor pulse switch is disabled")
    check("Not available here yet." in page.locator("[data-env-row=pulse]").inner_text() and "Uses the camera. Beats per minute." not in page.locator("[data-env-row=pulse]").inner_text(), "visitor pulse hint says not available")
    page.locator("[data-env-switch=light]").check(); page.wait_for_timeout(600)
    check(st("light") == "Needs camera switch", "light: Needs camera switch (got %r)" % st("light"))
    page.locator("[data-env-switch=time]").check(); page.wait_for_timeout(1500)
    check(st("time") == "On", "time of day On (uses the clock)")
    page.locator("[data-env-switch=camera]").check(); page.wait_for_timeout(1200)
    check(st("pulse") == "Not available yet", "pulse stays Not available yet for a visitor with the camera on (got %r)" % st("pulse"))
    check(st("light") != "Needs camera switch", "light no longer needs camera switch")
    page.screenshot(path=str(OUT / "card-on-390.png"))
    # Stop sharing: one tap, no confirm
    page.locator("[data-environment-revoke]").click(); page.wait_for_timeout(800)
    check(page.locator("[data-env-confirm]").count() == 0, "Stop sharing has no confirm step")
    check(page.locator("[data-env-state]").count() == 0 and all(not sw.nth(i).is_checked() for i in range(sw.count())), "Stop sharing switches everything off")
    srv = page.locator("[data-env-server]").inner_text()
    check(srv.startswith("Stopped"), "stop status line (got %r)" % srv)  # 127.0.0.1 vs localhost: the route's same-origin check can answer 403 locally; either way the card says Stopped
    check("noticed" not in page.locator("[data-env-notice]").inner_text() and "back to its own sky" in page.locator("[data-env-notice]").inner_text(), "stop notice")
    page.screenshot(path=str(OUT / "card-stopped-390.png"))
    check(not errs, "no page errors %s" % errs[:2])
    b.close()
print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
