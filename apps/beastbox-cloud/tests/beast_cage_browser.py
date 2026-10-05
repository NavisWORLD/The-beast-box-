"""Real public browser acceptance with original art, no owner data or sensors."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright, expect

ROOT="http://127.0.0.1:3100"
OUT=Path("browser-evidence/beast-cage")
OUT.mkdir(parents=True,exist_ok=True)
results=[]

def no_overflow(page,label):
    sizes=page.evaluate("({scroll:document.documentElement.scrollWidth,width:document.documentElement.clientWidth})")
    assert sizes["scroll"]<=sizes["width"]+1,(label,sizes)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"])
    for width,height in [(1440,900),(430,932),(390,844),(375,812),(320,720)]:
        context=browser.new_context(viewport={"width":width,"height":height},device_scale_factor=1,is_mobile=width<500,has_touch=width<500)
        page=context.new_page()
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        # The public HOMEPAGE must render the actual creature too, not merely
        # its static illustrative reference image.
        home=page.goto(ROOT+"/",wait_until="domcontentloaded",timeout=30000)
        assert home and home.status==200
        page.get_by_role("heading",name=re.compile("A small companion")).wait_for()
        no_overflow(page,str(width)+" homepage")
        if page.evaluate("!!document.createElement('canvas').getContext('webgl')"):
            page.locator(".beast-landing-creature [data-graphics='procedural-3d']").wait_for(timeout=16000)
        if width in (1440,390,320):
            page.screenshot(path=str(OUT/f"homepage-{width}.png"),full_page=True,animations="disabled")
        response=page.goto(ROOT+"/beast-cage",wait_until="domcontentloaded",timeout=30000)
        assert response and response.status==200,(width,"route")
        page.get_by_role("heading",name=re.compile("A small companion")).wait_for()
        no_overflow(page,str(width)+" initial")
        dock=page.locator('[data-lost-cosmos-dock="true"]')
        expect(dock).to_have_attribute("data-dock-state","mini")
        box=dock.bounding_box()
        assert box and box["width"]<=300,(width,box)
        if width in (390,320):
            # On phones the mini player is a pill; when it would cover a page control it
            # tucks into an edge tab, and tapping the tab brings the pill controls back.
            if dock.get_attribute("data-dock-pill")=="tucked":
                page.get_by_role("button",name="Show Lost Cosmos player").click()
                expect(dock).to_have_attribute("data-dock-pill","pill")
            page.get_by_role("button",name="Close Lost Cosmos player").click()
            expect(dock).to_have_attribute("data-dock-state","closed")
            page.get_by_role("button",name="Open Lost Cosmos player").click()
            expect(dock).to_have_attribute("data-dock-state","mini")
        page.get_by_role("button",name="Enable creature sounds").click()
        expect(page.get_by_role("button",name="Mute creature sounds")).to_have_attribute("aria-pressed","true")
        lumen=page.get_by_role("button",name=re.compile("Lumen"))
        lumen.click()
        expect(lumen).to_have_attribute("aria-pressed","true")
        page.get_by_role("button",name="Save visual family").click()
        expect(page.locator(".cage-save-status")).to_contain_text("Visual family saved locally")
        # Verify local storage write BEFORE navigation. Wait for hydration
        # after reload; WebGL shader setup on slow CI can outlive DOMContentLoaded.
        assert page.evaluate("localStorage.getItem('beastbox-cage-appearance-v1')")=="aurora"
        page.reload(wait_until="load")
        page.wait_for_function("localStorage.getItem('beastbox-cage-appearance-v1')==='aurora'",timeout=15000)
        expect(page.get_by_role("button",name=re.compile("Lumen"))).to_have_attribute("aria-pressed","true",timeout=15000)
        no_overflow(page,str(width)+" persisted")
        # Beast Cage intentionally uses the Spark pixel creature now; the
        # separate turntable/download path continues to prove real 3D export.
        hero=page.locator('.cage-habitat-visual [data-spark-beast="true"]')
        expect(hero).to_be_visible(timeout=16000)
        expect(hero).to_have_attribute("data-creature-id",re.compile("^bb-"))
        page.screenshot(path=str(OUT/f"cage-{width}.png"),full_page=True,animations="disabled")
        assert not errors,(width,errors[:4])
        results.append((width,"spark-beast","passed"))
        context.close()
    reduced=browser.new_context(viewport={"width":390,"height":844},reduced_motion="reduce")
    page=reduced.new_page()
    page.goto(ROOT+"/beast-cage",wait_until="domcontentloaded")
    expect(page.locator(".cage-universe")).to_have_attribute("data-reduced-motion","true")
    expect(page.locator('.cage-habitat-visual [data-spark-beast="true"]')).to_be_visible()
    no_overflow(page,"reduced-motion")
    page.screenshot(path=str(OUT/"reduced-motion.png"),full_page=True,animations="disabled")
    reduced.close()
    browser.close()
print("BEAST_CAGE_BROWSER_PASS",results,"Spark reduced-motion presentation passed. No physical sensors accessed.")
