"""Per-route button/option audit (real Chromium). Usage: python tests/world_audit_browser.py <base> [out.json] [--strict]
Checks every visible control on each route at phone (390) and desktop (1100): name, destination, honest disabled reason,
duplicate labels with different targets, overlapping fixed chips, dock covering the last content, horizontal overflow,
and (for safe buttons) that a click has an observable effect. Sensor/destructive buttons are never clicked."""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3100").rstrip("/")
OUT = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "world-audit.json"
STRICT = "--strict" in sys.argv
ROUTES = ["/", "/beast-cage", "/universe", "/beast-cage/look", "/beast-cage/world", "/beast-cage/turntable", "/beast-cage/play",
          "/beast-cage/field", "/beast-cage/guest", "/beast-cage/go", "/beast-cage/talk", "/sol-game", "/brain-bay", "/research",
          "/settings", "/try", "/next", "/privacy", "/account", "/workspace"]
SKIP_CLICK = re.compile(r"start|stop|delete|clear|remember|send|sign|log ?out|buy|pay|dispatch|install|camera|mic|speech|vision|sensor|connect|download|upload|grant|allow|enable|hatch|save|reset all|revoke|discard|forget|unlock", re.I)

COLLECT = r"""() => {
  const vis = (e) => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.display !== 'none' && parseFloat(s.opacity) > 0.05 && r.bottom > -5 && r.top < document.documentElement.scrollHeight + 5; };
  const nm = (e) => (e.getAttribute('aria-label') || e.innerText || e.textContent || e.getAttribute('title') || e.getAttribute('alt') || e.value || e.getAttribute('placeholder') || '').replace(/\s+/g, ' ').trim();
  const els = [...document.querySelectorAll('button, a[href], summary, input:not([type=hidden]), select, textarea, [role=button], [role=tab], [role=switch]')];
  return els.filter(vis).filter((e) => e.matches('summary') || !e.closest('details:not([open])')).map((e, i) => { const r = e.getBoundingClientRect(); let fixed = false, p = e;
    while (p && p !== document.body) { const ps = getComputedStyle(p).position; if (ps === 'fixed' || ps === 'sticky') { fixed = true; break; } p = p.parentElement; }
    const lab = e.labels && e.labels[0] ? e.labels[0].innerText.replace(/\s+/g,' ').trim() : '';
    return { i, tag: e.tagName.toLowerCase(), type: e.getAttribute('type') || '', name: nm(e) || lab, href: e.getAttribute('href') || '',
      disabled: !!e.disabled || e.getAttribute('aria-disabled') === 'true', title: e.getAttribute('title') || '', describedby: e.getAttribute('aria-describedby') || '',
      pressed: e.getAttribute('aria-pressed'), expanded: e.getAttribute('aria-expanded'), fixed,
      cls: (e.className && e.className.toString().slice(0, 50)) || '', x: Math.round(r.left), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height), vx: Math.round(r.left), vy: Math.round(r.top) }; });
}"""
HOOK = """() => { window.__fx = 0; window.__ev = 0; const mo = new MutationObserver(m => { window.__fx += m.length; }); mo.observe(document.documentElement, {subtree:true, childList:true, attributes:true, characterData:false});
  const de = window.dispatchEvent.bind(window); window.dispatchEvent = (e) => { window.__ev++; return de(e); };
  const f = window.fetch.bind(window); window.fetch = (...a) => { window.__ev++; return f(...a); }; }"""


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def fixed_overlaps(items):
    fx = [x for x in items if x["fixed"] and x["w"] > 20 and x["h"] > 14]
    out = []
    for a in range(len(fx)):
        for b in range(a + 1, len(fx)):
            A, B = fx[a], fx[b]
            ix = min(A["x"] + A["w"], B["x"] + B["w"]) - max(A["x"], B["x"])
            iy = min(A["y"] + A["h"], B["y"] + B["h"]) - max(A["y"], B["y"])
            if ix > 6 and iy > 6 and ix * iy > 0.25 * min(A["w"] * A["h"], B["w"] * B["h"]):
                out.append([A["name"][:30], B["name"][:30]])
    return out


def audit_route(browser, route, vp, session_cookie=None):
    w, h = vp
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500, has_touch=w < 500)
    if session_cookie:
        ctx.add_cookies([session_cookie])
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:160]))
    rep = {"route": route, "vp": w, "findings": [], "controls": 0, "clicked": 0, "dead": []}
    try:
        resp = page.goto(BASE + route, wait_until="domcontentloaded", timeout=45000)
        rep["status"] = resp.status if resp else None
        page.wait_for_timeout(3500)
        page.evaluate(HOOK)
        rep["overflowX"] = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        if rep["overflowX"] > 1:
            rep["findings"].append("horizontal overflow %spx" % rep["overflowX"])
        items = page.evaluate(COLLECT)
        rep["controls"] = len(items)
        seen = {}
        for it in items:
            if it["tag"] in ("a", "button", "summary") or it["type"] in ("checkbox", "radio", "button", "submit"):
                if not it["name"]:
                    rep["findings"].append("no accessible name: %s %s" % (it["tag"], it["cls"]))
            if it["tag"] == "a" and (it["href"] in ("", "#") or it["href"].startswith("javascript:")):
                rep["findings"].append("dead link: %r" % it["name"][:40])
            if it["disabled"] and not (it["title"] or it["describedby"]):
                rep["findings"].append("disabled with no reason: %r" % it["name"][:50])
            if it["tag"] == "a" and it["name"]:
                seen.setdefault(norm(it["name"]), set()).add(it["href"].split("#")[0])
        for k, v in seen.items():
            if len(v) > 1 and k:
                rep["findings"].append("same label, different targets: %r -> %s" % (k[:40], sorted(v)))
        ov = fixed_overlaps(items)
        if ov:
            rep["findings"].append("overlapping fixed/sticky controls: %s" % ov[:4])
        # dock vs last content (scroll to bottom)
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_timeout(500)
        dk = page.evaluate("""() => { const d = document.querySelector('[data-site-dock]'); if (!d) return null; const r = d.getBoundingClientRect(); if (r.width < 2) return null;
          const els = [...document.querySelectorAll('main *, footer *')].filter(e => e.children.length === 0 && (e.innerText||'').trim().length > 2 && getComputedStyle(e).position !== 'fixed');
          let last = null, lb = -1; for (const e of els) { const b = e.getBoundingClientRect(); if (b.width > 1 && b.bottom <= innerHeight + 2 && b.bottom > lb && b.top > 0) { lb = b.bottom; last = e; } }
          return { dockTop: r.top, dockL: r.left, dockR: r.right, last: last ? (last.innerText||'').trim().slice(0, 40) : null, lastBottom: lb, lastL: last ? last.getBoundingClientRect().left : 0, lastR: last ? last.getBoundingClientRect().right : 0 }; }""")
        if dk and dk["last"] and dk["lastBottom"] > dk["dockTop"] + 2 and min(dk["dockR"], dk["lastR"]) - max(dk["dockL"], dk["lastL"]) > 4:
            rep["findings"].append("dock covers last content: %r (bottom %d > dock top %d)" % (dk["last"], dk["lastBottom"], dk["dockTop"]))
        page.evaluate("window.scrollTo(0,0)")
        # click test on safe, enabled, in-page buttons
        cand = [it for it in items if it["tag"] in ("button", "summary") and not it["disabled"] and it["name"] and not SKIP_CLICK.search(it["name"]) and it["w"] > 8][:40]
        for it in cand:
            try:
                before_url = page.url
                b0 = page.evaluate("[window.__fx||0, window.__ev||0]")
                els = page.query_selector_all("button, summary")
                tgt = None
                for e in els:
                    try:
                        if e.is_visible() and ((e.get_attribute("aria-label") or e.inner_text() or "").strip().replace("\n", " ")[:40] == it["name"][:40]):
                            tgt = e; break
                    except Exception:
                        pass
                if not tgt:
                    continue
                st0 = (tgt.get_attribute("aria-pressed"), tgt.get_attribute("aria-expanded"))
                tgt.evaluate("e => e.click()")  # JS click: software-rendered WebGL pages never reach 'stable' for a real pointer click
                page.wait_for_timeout(450)
                rep["clicked"] += 1
                moved = page.url != before_url
                b1 = page.evaluate("[window.__fx||0, window.__ev||0]") if not moved else [1, 1]
                st1 = (tgt.get_attribute("aria-pressed"), tgt.get_attribute("aria-expanded")) if not moved else st0
                if not moved and b1 == b0 and st1 == st0:
                    rep["dead"].append(it["name"][:50])
                    if it.get("pressed") != "true":  # an already-selected toggle legitimately changes nothing
                      rep["findings"].append("click has no observable effect: %r" % it["name"][:50])
                if moved:
                    page.goto(BASE + route, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(2500)
                    page.evaluate(HOOK)
            except Exception as ex:
                rep["findings"].append("click error %r: %s" % (it["name"][:30], str(ex)[:60]))
        if errs:
            rep["findings"].append("page errors: %s" % errs[:2])
    except Exception as ex:
        rep["findings"].append("route failed: %s" % str(ex)[:100])
    ctx.close()
    return rep


def main():
    cookie = None
    pw = os.environ.get("BEASTBOX_OWNER_PASSWORD")
    results = []
    with sync_playwright() as p:
        exe = os.environ.get("BEAST_BROWSER_EXECUTABLE") or ("/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None)
        br = p.chromium.launch(headless=True, **({"executable_path": exe} if exe else {}), args=["--no-sandbox", "--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        if pw:
            c = br.new_context()
            r = c.request.post(BASE + "/api/session", data=json.dumps({"password": pw}), headers={"Content-Type": "application/json", "Origin": BASE})
            if r.ok:
                ck = [x for x in c.cookies() if x["name"]]
                cookie = {k: ck[0][k] for k in ("name", "value", "domain", "path")} if ck else None
            c.close()
        for route in ROUTES:
            for vp in [(390, 844), (1100, 700)]:
                if route == "/workspace" and not cookie and vp[0] == 390 and False:
                    continue
                rep = audit_route(br, route, vp, cookie if route.startswith("/workspace") else None)
                results.append(rep)
                print(route, vp[0], "controls", rep["controls"], "clicked", rep["clicked"], "findings", len(rep["findings"]), flush=True)
                for f in rep["findings"]:
                    print("   -", f, flush=True)
        br.close()
    json.dump(results, open(OUT, "w"), indent=1)
    total = sum(len(r["findings"]) for r in results)
    print("TOTAL findings", total, "routes", len(results))
    if STRICT and total:
        sys.exit(1)

main()
