"""390px phone acceptance for Look Closer and the Cage (real Chromium, software WebGL, touch emulated). Usage: python tests/phone_look_browser.py [base]
Look Closer: open sky (no boxed stage), plain subtitle (no engine name), one spelling of the beast name, the last section clears the
bottom bar, and with the quick dock open no floating control sits on another one. Cage: canonical link names, no raw creature id."""
import json, os, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3100").rstrip("/")
ROOT = Path(__file__).resolve().parent.parent
SESSION = json.loads((ROOT / "public/spark/zeref-live-20261010/unsigned-session.json").read_text())
SESSION["beast"]["displayName"] = "Zeref-Nightcat-Dragon"
# The site dock is not drawn under automation, so present as a real browser; start with the dock open (worst case for overlaps).
INIT = ('localStorage.setItem("beastbox.dock.open.v1","1");localStorage.setItem("beastbox-companion-session-v1",%s);'
        'Object.defineProperty(navigator,"webdriver",{get:()=>false});' % json.dumps(json.dumps(SESSION)))
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("FAIL", msg, flush=True)


OVERLAPS = """() => {
 const out=[];const els=[...document.querySelectorAll('body *')].filter(e=>{const cs=getComputedStyle(e);if(cs.position!=='fixed'||cs.visibility==='hidden'||cs.display==='none'||+cs.opacity===0||cs.pointerEvents==='none')return false;
  const r=e.getBoundingClientRect();return r.width>=30&&r.height>=30&&r.width<innerWidth&&r.bottom>0&&r.top<innerHeight&&!e.closest('nextjs-portal')&&e.tagName!=='NEXTJS-PORTAL'});
 const top=els.filter(e=>!els.some(o=>o!==e&&o.contains(e)));
 for(let i=0;i<top.length;i++)for(let j=i+1;j<top.length;j++){const a=top[i].getBoundingClientRect(),b=top[j].getBoundingClientRect();
  const w=Math.min(a.right,b.right)-Math.max(a.left,b.left),h=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);
  if(w>6&&h>6)out.push([top[i].tagName+'.'+String(top[i].className).slice(0,30),top[j].tagName+'.'+String(top[j].className).slice(0,30),Math.round(w),Math.round(h)]);}
 return out;}"""


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("PW_CHROME") or None, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    ctx.add_init_script(INIT)
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:160]))
    page.goto(BASE + "/beast-cage/look", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("[data-stage='real-3d-turntable']", timeout=90000)
    page.wait_for_timeout(4000)
    stage = page.evaluate("""() => {const e=document.querySelector("[data-stage='real-3d-turntable']");const r=e.getBoundingClientRect(),cs=getComputedStyle(e);
      return {w:r.width,bw:cs.borderTopWidth,rad:cs.borderTopLeftRadius,shadow:cs.boxShadow,ov:cs.overflow,aria:e.getAttribute('aria-label'),sky:!!document.querySelector('[data-open-sky]')}}""")
    check(stage["w"] >= 388, f"stage is full width on a phone {stage}")
    check(stage["bw"] == "0px" and stage["rad"] == "0px" and stage["shadow"] == "none", f"stage has no box (border, radius, shadow) {stage}")
    check(stage["sky"] and not re.search("three", stage["aria"] or "", re.I), f"open-sky stage with a plain aria-label {stage}")
    check(page.is_visible("[data-stage-seeded]"), "SEEDED chip stays visible on the stage")
    sub = page.inner_text("[data-look-subtitle]")
    check(re.search(r"in 3D, built from your saved look\.$", sub) and not re.search("three", sub, re.I), f"subtitle is plain: {sub!r}")
    body = page.inner_text("body")
    check("Zeref-Nightcat-Dragon" not in body, "the name is never spelled with hyphens on the page")
    check("Zeref \u00b7 Nightcat Dragon" in body, "the name uses the middle-dot form")
    check(page.evaluate("document.documentElement.scrollWidth") <= 391, "no horizontal overflow at 390px")
    for y in (0, 300, 700):
        page.evaluate(f"window.scrollTo(0,{y})")
        page.wait_for_timeout(500)
        o = page.evaluate(OVERLAPS)
        check(not o, f"no floating control sits on another at scrollY={y}: {o}")
    # The OPEN GAME pill: label fully visible, 48 px close, never on another floating control when idle, steps aside while scrolling.
    page.evaluate("window.scrollTo(0, 600)")
    page.wait_for_timeout(1200)
    pill = page.evaluate("""() => {const s=document.querySelector('[data-spark-player][data-player-mode=minimized]');if(!s)return null;const o=s.querySelector('a,button:not([aria-label^=Close])');const c=s.querySelector('[aria-label="Close game card"]');
      const r=s.getBoundingClientRect(),cr=c.getBoundingClientRect(),or=o.getBoundingClientRect();return {op:+getComputedStyle(s).opacity,w:r.width,right:r.right,vw:innerWidth,cw:cr.width,ch:cr.height,clipped:o.scrollWidth>o.clientWidth+1,label:o.textContent.trim(),ol:or.right<=cr.left+1,bottom:r.bottom,vh:innerHeight}}""")
    check(pill is not None, "minimized game pill is present on Look Closer")
    if pill and pill["w"] == 0:
        # One phone dock: the loose OPEN GAME pill is replaced by an "Open ...'s game" row in the dock column (same action, no second floater).
        page.wait_for_timeout(1200)
        row = page.evaluate("() => {const e=document.querySelector('[data-quick-game-card]');if(!e)return null;const r=e.getBoundingClientRect();return {h:r.height,t:(e.textContent||'').trim()}}")
        check(row is not None and row["h"] >= 44 and re.search(r"game", row["t"], re.I), f"pill is replaced by a 44px+ game row in the one dock {row}")
        o = page.evaluate(OVERLAPS)
        check(not o, f"one dock sits on no other floating control: {o}")
    elif pill:
        check(pill["op"] > 0.9, f"pill is back after scrolling stops {pill}")
        check(pill["cw"] >= 48 and pill["ch"] >= 48, f"pill close button is at least 48x48 {pill}")
        check(not pill["clipped"] and pill["label"] == "OPEN GAME" and pill["ol"], f"pill label is whole and does not run under the close button {pill}")
        check(pill["right"] <= pill["vw"] and pill["bottom"] <= pill["vh"], f"pill is inside the screen {pill}")
        o = page.evaluate(OVERLAPS)
        check(not o, f"idle pill sits on no other floating control: {o}")
        page.evaluate("window.scrollBy(0, 40)")
        page.wait_for_timeout(380)
        check(page.evaluate("+getComputedStyle(document.querySelector('[data-spark-player]')).opacity") < 0.5, "pill steps aside while the page scrolls")
        page.wait_for_timeout(1000)
    # The last section must clear the bottom bar.
    page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    page.wait_for_timeout(600)
    h2 = page.evaluate("""() => {const h=[...document.querySelectorAll('h2')].find(e=>/creation process/i.test(e.textContent));const r=h.getBoundingClientRect();return {bottom:r.bottom,vh:innerHeight}}""")
    check(h2["bottom"] < h2["vh"] - 72, f"'The actual creation process' is clear of the bottom bar {h2}")
    page.goto(BASE + "/beast-cage", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("#habitat", timeout=90000)
    page.wait_for_timeout(2500)
    cage = page.inner_text("body")
    for old in ("Game lab", "Workshop deck", "Lost COSMOS Field (camera)"):
        check(old not in cage, f"old menu name '{old}' is gone")
    check(not re.search(r"bb-[0-9a-f]{8}", cage), "no raw creature id on the cage page")
    check(page.evaluate("document.documentElement.scrollWidth") <= 391, "cage: no horizontal overflow at 390px")
    check(not errs, f"no page errors: {errs}")
    b.close()
if failures:
    print(f"{len(failures)} failure(s)")
    sys.exit(1)
print("phone look/cage OK")
