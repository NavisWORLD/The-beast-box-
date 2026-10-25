"""One-menu acceptance (real Chromium, software-rendered WebGL, touch emulated at phone width). Usage: python tests/world_menu_browser.py [base]
Home (pocket universe) and /beast-cage (habitat) each get ONE corner menu: 44px target inside the scene, nothing drawn over the creatures
(no pixel sprite overlay and no Look Closer pill by default), a sheet with every option, shared labels, phone and desktop without overflow."""
import json, os, sys
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3100").rstrip("/")
JS_RECT = "(sel) => { const e = document.querySelector(sel); if (!e) return null; const r = e.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height,hidden:!!e.hidden}; }"
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("FAIL", msg, flush=True)


def run(browser, route, ctx_key, vp, mobile):
    ctx = browser.new_context(viewport={"width": vp[0], "height": vp[1]}, is_mobile=mobile, has_touch=mobile)
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:160]))
    page.goto(BASE + route, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector(f'[data-world-menu="{ctx_key}"] [data-world-menu-button]', timeout=60000)
    tag = f"{route} @{vp[0]}"
    fab = page.evaluate(JS_RECT, "[data-world-menu-button]")
    check(fab and fab["w"] >= 44 and fab["h"] >= 44, f"{tag}: menu button is a 44px target {fab}")
    page.evaluate("document.querySelector('[data-world-menu-button]').scrollIntoView({block:'center',behavior:'instant'})")
    page.wait_for_timeout(1500)
    hit = page.evaluate("""() => {const f=document.querySelector('[data-world-menu-button]');const r=f.getBoundingClientRect();const e=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return !!e && f.contains(e)}""")
    check(hit, f"{tag}: nothing (sprite, canvas, chip) covers the menu button, so a real tap lands on it")
    clash = page.evaluate("""() => {const f=document.querySelector('[data-world-menu-button]').getBoundingClientRect();return [...document.querySelectorAll('[data-spark-beast] button, [aria-label="Show controls"]')].some(b=>{const r=b.getBoundingClientRect();return r.width>0&&r.x<f.right&&r.right>f.x&&r.y<f.bottom&&r.bottom>f.y})}""")
    check(not clash, f"{tag}: menu button does not overlap the creature's own controls")
    check(page.evaluate("document.querySelectorAll('.cage-look-pill').length") == 0, f"{tag}: no Look Closer pill on the scene")
    check(page.evaluate("document.querySelectorAll('[data-beast-arena]').length") == 0 or ctx_key == "cage", f"{tag}: no pixel sprite overlay by default")
    check(page.evaluate("document.querySelectorAll('.cage-view-toggle, [data-home-view-toggle]').length") == 0, f"{tag}: no loose view buttons")
    sheet = page.evaluate(JS_RECT, "[data-world-menu-sheet]")
    check(sheet and sheet["hidden"], f"{tag}: sheet is closed at first")
    page.evaluate("document.querySelector('[data-world-menu-button]').click()")
    page.wait_for_timeout(600)
    sheet = page.evaluate(JS_RECT, "[data-world-menu-sheet]")
    check(sheet and not sheet["hidden"] and sheet["x"] >= -1 and sheet["x"] + sheet["w"] <= vp[0] + 1, f"{tag}: sheet opens inside the viewport {sheet}")
    for sec in ["view", "place", "tools", "diary", "senses", "about"]:
        check(page.evaluate("(s) => !!document.querySelector(`[data-menu-section=\"${s}\"]`)", sec), f"{tag}: section {sec}")
    labels = page.evaluate("() => [...document.querySelectorAll('[data-world-menu-sheet] button, [data-world-menu-sheet] a')].filter(e => e.getBoundingClientRect().width > 0).map(e => [e.innerText.replace(/\\s+/g,' ').trim(), Math.round(e.getBoundingClientRect().height)])")
    check(any("Reset 3D camera" in l[0] for l in labels), f"{tag}: Reset 3D camera is in the menu")
    check(any("Diary" in l[0] for l in labels), f"{tag}: Diary is in the menu")
    check(any("Look Closer" in l[0] for l in labels), f"{tag}: Look Closer is in the menu")
    check(any("Pocket explorer" in l[0] for l in labels), f"{tag}: Pocket explorer view option")
    if mobile:
        small = [l for l in labels if l[1] < 40 and l[0] and l[0] != "✕"]
        check(not small, f"{tag}: touch targets under 40px {small[:4]}")
    ids = page.evaluate("() => [...document.querySelectorAll('[data-world-view]')].map(e => e.dataset.worldView)")
    check("pocket" in ids, f"{tag}: view options {ids}")
    check(("classic" in ids) == (ctx_key == "cage"), f"{tag}: Classic pixel sprite is a choice only in the habitat {ids}")
    # reset camera fires the shared event, the diary link points at the diary
    page.evaluate("window.__reset = 0; window.addEventListener('beastbox:pocket-3d-reset-camera', () => window.__reset++)")
    page.evaluate("document.querySelector('[data-menu-reset]').click()")
    check(page.evaluate("window.__reset") >= 1, f"{tag}: reset event")
    check("diary" in (page.evaluate("document.querySelector('[data-menu-diary]').getAttribute('href')") or ""), f"{tag}: diary link")
    # Escape closes
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    check(page.evaluate(JS_RECT, "[data-world-menu-sheet]")["hidden"], f"{tag}: Escape closes")
    if ctx_key == "cage":
        page.evaluate("document.querySelector('[data-world-menu-button]').click()")
        page.wait_for_timeout(300)
        page.evaluate("document.querySelector('[data-world-view=classic]').click()")
        page.wait_for_timeout(1500)
        check(page.evaluate("document.querySelectorAll('[data-beast-arena]').length") >= 1, f"{tag}: Classic view shows the sprite only because it was chosen")
        check(page.evaluate("localStorage.getItem('beastbox-cage-view-v1')") == "classic", f"{tag}: view choice saved")
        page.evaluate("document.querySelector('[data-world-view=pocket]').click()")
        page.wait_for_timeout(1500)
        check(page.evaluate("localStorage.getItem('beastbox-cage-view-v1')") == "pocket", f"{tag}: back to the pocket explorer is saved")
    sw = page.evaluate("({s:document.documentElement.scrollWidth,w:document.documentElement.clientWidth})")
    check(sw["s"] <= sw["w"] + 1, f"{tag}: no horizontal overflow {sw}")
    check(not errs, f"{tag}: page errors {errs[:2]}")
    ctx.close()


with sync_playwright() as p:
    exe = os.environ.get("BEAST_BROWSER_EXECUTABLE") or ("/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None)
    browser = p.chromium.launch(headless=True, **({"executable_path": exe} if exe else {}), args=["--no-sandbox", "--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    for route, key in [("/", "home"), ("/beast-cage", "cage")]:
        for vp, mob in [((390, 844), True), ((1100, 700), False)]:
            run(browser, route, key, vp, mob)
    browser.close()
print(json.dumps({"failures": failures}))
sys.exit(1 if failures else 0)
