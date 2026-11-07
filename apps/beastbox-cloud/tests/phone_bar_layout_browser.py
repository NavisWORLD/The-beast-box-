"""Phone layout at 390x844 (Cory's iPhone shots, Nov 7 2026).

1. ONE bottom bar (Share my world · Quick buttons · LOST COSMOS · Sound) and no overlap between the world controls:
   Universe chip, narration line, View / Motion / Quality chips, the Tiny Universe zoom row, Beach view / Spawn in, the share card.
2. Brain chat: the composer stays visible (also with the keyboard up), the thread scrolls, the global overlays are hidden.
The site's own dock is not drawn under navigator.webdriver, so this suite reports webdriver=false like a phone browser does.
"""
import os, sys
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3100").rstrip("/")
PASSWORD = os.environ.get("BEASTBOX_OWNER_PASSWORD", "")
W, H = 390, 844
SEL = {
    "universe_chip": "[data-world-menu-button]", "narration": "[data-lw-line]", "view": "[data-lw-view]",
    "motion": "[data-lw-motion]", "quality": "[data-lw-quality]", "zoom": "[data-u3d-zoom]",
    "share_card": "[data-share-world]", "quick_pill": ".qd-toggle", "bar": "[data-phone-bar]",
    "beach": "[data-lw-beachcam]", "spawn": "[data-lw-spawn]",
}
RECTS = """(S)=>{const o={};for(const [k,s] of Object.entries(S)){o[k]=[...document.querySelectorAll(s)].filter(e=>{
 const r=e.getBoundingClientRect(),c=getComputedStyle(e);return r.width>2&&r.height>2&&c.display!=='none'&&c.visibility!=='hidden'&&r.bottom>0&&r.top<innerHeight;})
 .map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom];});}return o;}"""

def hit(a, b):
    return a[0] < b[2] - 1 and b[0] < a[2] - 1 and a[1] < b[3] - 1 and b[1] < a[3] - 1

def no_overlap(rects, where):
    keys = [k for k in rects if rects[k]]
    bad = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if {a, b} <= {"view", "motion", "quality"}:
                continue  # one stacked chip column, laid out by flexbox
            for ra in rects[a]:
                for rb in rects[b]:
                    if hit(ra, rb):
                        bad.append((a, b, ra, rb))
    assert not bad, f"{where}: overlapping controls {bad}"

def check_bar(page, where):
    bar = page.locator("[data-phone-bar]")
    assert bar.is_visible(), f"{where}: bottom bar missing"
    box = bar.bounding_box()
    assert box["y"] + box["height"] <= H + 0.5 and box["x"] >= 0 and box["x"] + box["width"] <= W + 0.5, (where, box)
    words = bar.inner_text()
    for w in ("Share my world", "Quick buttons", "LOST COSMOS"):
        assert w in words, (where, words)
    assert any(w in words for w in ("Sound off", "Sound on", "Tap for sound")), (where, words)
    assert not page.locator(".qd-toggle").is_visible(), f"{where}: the old Quick buttons pill still floats"
    assert not page.locator("[data-share-world]").is_visible(), f"{where}: the share card still floats"
    return box

def main():
    with sync_playwright() as p:
        exe = os.environ.get("CHROME_PATH") or None
        b = p.chromium.launch(executable_path=exe, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        ctx = b.new_context(viewport={"width": W, "height": H}, is_mobile=True, has_touch=True, device_scale_factor=1)
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
        page = ctx.new_page()
        for path in ("/", "/universe", "/beast-cage"):
            page.goto(BASE + path, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(7000)
            if path == "/universe" and page.locator("[data-universe-3d]").count() == 0 and page.locator("[data-universe-mode]").count():
                page.locator("[data-universe-mode]").first.evaluate("e=>e.click()")
                page.wait_for_timeout(6000)
            bar = check_bar(page, path)
            no_overlap(page.evaluate(RECTS, SEL), path)
            os.makedirs("browser-evidence/phone-bar", exist_ok=True)
            page.screenshot(path=f"browser-evidence/phone-bar/{path.strip('/') or 'home'}-390.png")
            # the share card opens as a sheet above the bar, with the same switch and words
            page.locator("[data-bar-share]").click()
            card = page.locator("[data-share-world]")
            assert card.is_visible(), f"{path}: share sheet did not open"
            assert card.get_by_role("switch").inner_text().strip() in ("Share my world with Zeref", "Sharing ✓")
            cb = card.bounding_box()
            assert cb["y"] + cb["height"] <= bar["y"] + 0.5, (path, cb, bar)
            page.locator("[data-bar-share]").click()
            # Quick buttons open the same column above the bar
            page.locator("[data-bar-quick]").click()
            panel = page.locator("#quick-dock-panel")
            assert panel.is_visible(), f"{path}: quick buttons column did not open"
            pb = panel.bounding_box()
            assert pb["y"] + pb["height"] <= bar["y"] + 0.5 and pb["y"] >= 0, (path, pb, bar)
            page.locator("[data-bar-quick]").click()
            print("PASS", path)

        if not PASSWORD:
            print("SKIP brain chat: BEASTBOX_OWNER_PASSWORD not set")
        else:
            page.goto(BASE + "/workspace?owner=1", wait_until="domcontentloaded", timeout=90000)
            page.get_by_label("OWNER PASSWORD").fill(PASSWORD)
            page.get_by_role("button", name="Unlock workstation").click()
            page.get_by_role("button", name="Open navigation").wait_for(timeout=60000)
            page.get_by_role("button", name="Open navigation").click()
            page.get_by_role("button", name="BRAIN", exact=True).click()
            page.wait_for_timeout(1500)
            for h in (H, 470):  # 470 ≈ an iPhone with the keyboard up
                page.set_viewport_size({"width": W, "height": h})
                page.wait_for_timeout(600)
                box = page.get_by_label("Message Beast Box").bounding_box()
                assert box and box["y"] >= 0 and box["y"] + box["height"] <= h + 0.5, f"composer not visible at {W}x{h}: {box}"
                send = page.locator(".composer button").last.bounding_box()
                assert send and send["y"] + send["height"] <= h + 0.5, f"send button hidden at {W}x{h}: {send}"
            page.set_viewport_size({"width": W, "height": H})
            page.wait_for_timeout(400)
            page.screenshot(path="browser-evidence/phone-bar/brain-chat-390.png")
            ov = page.evaluate("()=>getComputedStyle(document.querySelector('.chat-thread')).overflowY")
            assert ov in ("auto", "scroll"), ov
            for s in ("[data-share-world]", ".qd-toggle", "[data-phone-bar]", "#quick-dock-panel"):
                assert not page.locator(s).first.is_visible(), f"brain chat: {s} still covers the chat"
            # the workstation menu still opens over the chat (it must not be covered by the pinned chat panel)
            page.get_by_role("button", name="Open navigation").click()
            page.get_by_role("button", name="SETTINGS").click(timeout=8000)
            page.wait_for_timeout(500)
            assert page.evaluate("()=>!document.body.dataset.brainChat"), "brain chat mode must end when leaving Brain"
            print("PASS brain chat")
        b.close()

if __name__ == "__main__":
    main()
