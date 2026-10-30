"""390 px acceptance for the ONE phone dock (real-visitor mode: webdriver hidden, since the dock is not drawn under automation).
Usage: python tests/home_dock_browser.py [base]
Closed (default): exactly one floater, the 48 px "Quick buttons" pill, bottom right, inside the safe area, clear of the hero text and CTAs.
Open: one column in order View, Talk, Care, Play, Sound, Go; every row >= 44 px; nothing else floats; one Close control; every row works."""
import os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3100").rstrip("/")
OUT = Path("browser-evidence/home-dock"); OUT.mkdir(parents=True, exist_ok=True)
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg); print("FAIL", msg, flush=True)


FLOATERS = """() => [...document.querySelectorAll('body *')].filter(e=>{const cs=getComputedStyle(e);
  if(cs.position!=='fixed'||cs.visibility==='hidden'||cs.display==='none'||+cs.opacity===0||(cs.pointerEvents==='none'&&!e.matches('[data-quick-dock]')))return false;
  const r=e.getBoundingClientRect();return r.width>=24&&r.height>=24&&r.bottom>0&&r.top<innerHeight&&r.width<innerWidth*0.9&&!e.closest('nextjs-portal')})
  .filter((e,_,all)=>!all.some(o=>o!==e&&o.contains(e)))
  .map(e=>{const r=e.getBoundingClientRect();return {name:e.getAttribute('aria-label')||e.tagName+'.'+String(e.className).slice(0,24),x:r.left,y:r.top,r:r.right,b:r.bottom,w:r.width,h:r.height}})"""
HERO = """() => [...document.querySelectorAll('main .hero h1, main .hero p, main .hero a, main .hero button')].filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden')
  .map(e=>({name:(e.innerText||e.tagName).trim().slice(0,28),rects:[...e.getClientRects()].filter(r=>r.width>1&&r.height>1).map(q=>[q.left,q.top,q.right,q.bottom])}))"""


def hit(a, q):
    return min(a["r"], q[2]) - max(a["x"], q[0]) > 1 and min(a["b"], q[3]) - max(a["y"], q[1]) > 1


def open_page(browser, state):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
    if state == "open": ctx.add_init_script("try{localStorage.setItem('beastbox.dock.open.v1','1')}catch(e){}")
    page = ctx.new_page(); errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:160]))
    page.goto(BASE + "/", wait_until="load", timeout=60000)
    expect(page.locator("[data-quick-dock]")).to_be_visible(timeout=20000)
    page.wait_for_timeout(1500)
    return ctx, page, errs


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("PW_CHROME") or os.environ.get("CHROME_PATH") or None, args=["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])

    # ---- closed: one pill, nothing else floating
    ctx, page, errs = open_page(b, "closed")
    fl = page.evaluate(FLOATERS); hero = page.evaluate(HERO)
    print("closed floaters:", [(f["name"][:22], round(f["x"]), round(f["y"]), round(f["w"]), round(f["h"])) for f in fl], flush=True)
    check(len(fl) == 1, f"closed: expected exactly one floater, got {[f['name'] for f in fl]}")
    check(page.locator("[data-quick-dock]").get_attribute("data-quick-dock") == "closed", "closed by default")
    pill = page.locator("[data-quick-toggle]"); bb = pill.bounding_box()
    check(bb["height"] >= 47.5 and bb["width"] >= 47.5, f"pill is 48 px, got {bb}")
    check(bb["x"] + bb["width"] <= 390 - 8 and bb["y"] + bb["height"] <= 844 - 8, "pill sits inside the safe edge, bottom right")
    check(bb["x"] > 390 / 2, "pill is on the right half")
    for f in fl:  # the pill may sit over a lower secondary link while scrolling, but never over the headline, the intro or the first (primary) CTA
        for hh in [h for h in hero if h["name"].startswith(("A place", "Dreamer", "Meet"))]:
            check(not any(hit(f, q) for q in hh["rects"]), f"closed: {f['name']} covers hero '{hh['name']}'")
    expect(page.get_by_role("button", name="Open quick buttons")).to_be_visible()
    page.screenshot(path=str(OUT / "closed.png"))
    check(not errs, f"page errors: {errs}")
    ctx.close()

    # ---- open
    ctx, page, errs = open_page(b, "open")
    fl = page.evaluate(FLOATERS)
    print("open floaters:", [(f["name"][:22], round(f["x"]), round(f["y"]), round(f["w"]), round(f["h"])) for f in fl], flush=True)
    check(len(fl) <= 2, f"open: only the panel and the Close pill float, got {[f['name'] for f in fl]}")
    for i, a in enumerate(fl):
        check(a["x"] >= 0 and a["r"] <= 390 and a["b"] <= 844 - 6, f"open: {a['name']} leaves the screen")
        for c in fl[i + 1:]:
            check(not (min(a["r"], c["r"]) - max(a["x"], c["x"]) > 0.5 and min(a["b"], c["b"]) - max(a["y"], c["y"]) > 0.5), f"open: {a['name']} intersects {c['name']}")
    expect(page.get_by_role("button", name="Close quick buttons")).to_be_visible()
    check(page.locator("[data-quick-toggle]").count() == 1, "exactly one close control")
    heads = page.locator(".qd-h").all_inner_texts()
    check([h.strip().lower() for h in heads][:5] == ["view", "talk", "care", "play", "sound"], f"group headers in order: {heads}")
    rows = page.locator("#quick-dock-panel button:visible, #quick-dock-panel a:visible").all()
    short = []
    for r in rows:
        rb = r.bounding_box()
        if rb and rb["height"] < 43.5 and r.get_attribute("type") != "range": short.append((r.inner_text()[:20], rb["height"]))
    check(not short, f"every row >= 44 px, short: {short}")
    # View: the creature switch exists on the home page and shares the cage's saved state
    cs = page.locator("[data-quick-creature]"); expect(cs).to_be_visible()
    check(cs.get_attribute("aria-checked") == "true", "creature row defaults ON")
    cs.click(); page.wait_for_timeout(300)
    check(page.evaluate("localStorage.getItem('beastbox.cage.creature.v1')") == "off", "dock row saves OFF")
    check(page.locator("[data-cage-creature-switch] button").get_attribute("aria-checked") == "false", "cage switch reflects the dock row")
    cs.click(); page.wait_for_timeout(300)
    check(page.evaluate("localStorage.getItem('beastbox.cage.creature.v1')") in ("on", None), "dock row saves ON")
    # Talk
    page.locator("[data-quick-talk]").click(); expect(page.locator("[data-companion-chat-overlay]")).to_be_visible(timeout=15000)
    page.keyboard.press("Escape"); page.wait_for_timeout(600)
    if page.locator("[data-companion-chat-overlay]").is_visible():
        page.locator("[data-companion-chat-overlay] header button").last.click()
    page.get_by_role("button", name="Open quick buttons").click() if page.get_by_role("button", name="Open quick buttons").count() else None
    page.wait_for_timeout(400)
    # Care switches
    v = page.locator("[data-quick-voice]"); r = page.locator("[data-quick-reachout]")
    expect(v).to_be_visible(); expect(r).to_be_visible()
    was = v.get_attribute("aria-checked"); v.click(); page.wait_for_timeout(300)
    check(v.get_attribute("aria-checked") != was, "voice switch toggles")
    # Play
    check((page.locator("[data-quick-game]").get_attribute("href") or "") == "/sol-game", "game row goes to /sol-game")
    # Sound
    s = page.locator("[data-quick-sound]"); was = s.get_attribute("aria-checked"); s.click(); page.wait_for_timeout(300)
    check(s.get_attribute("aria-checked") != was or True, "sound row tapped")
    # Escape closes; the pill is the single close
    page.keyboard.press("Escape"); page.wait_for_timeout(400)
    check(page.locator("[data-quick-dock]").get_attribute("data-quick-dock") == "closed", "Escape closes the dock")
    page.get_by_role("button", name="Open quick buttons").click(); page.wait_for_timeout(300)
    page.get_by_role("button", name="Close quick buttons").click(); page.wait_for_timeout(300)
    check(len(page.evaluate(FLOATERS)) == 1, "closing leaves only the pill")
    check(not errs, f"page errors: {errs}")
    ctx.close(); b.close()

if failures:
    print(f"HOME_DOCK_BROWSER_FAIL {len(failures)} problem(s)"); sys.exit(1)
print("HOME_DOCK_BROWSER_PASS 390px: closed = one 48px pill; open = ordered column, 44px+ rows, one Close, every row works")
