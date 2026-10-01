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
        response=page.goto(ROOT+"/beast-cage",wait_until="domcontentloaded",timeout=30000)
        assert response and response.status==200,(width,"route")
        page.get_by_role("heading",name=re.compile("A small companion")).wait_for()
        no_overflow(page,str(width)+" initial")
        lumen=page.get_by_role("button",name=re.compile("Lumen"))
        lumen.click()
        expect(lumen).to_have_attribute("aria-pressed","true")
        page.get_by_role("button",name="Save look on this device").click()
        expect(page.locator(".cage-save-status")).to_contain_text("Visual look saved locally")
        page.reload(wait_until="domcontentloaded")
        expect(page.get_by_role("button",name=re.compile("Lumen"))).to_have_attribute("aria-pressed","true",timeout=5000)
        no_overflow(page,str(width)+" persisted")
        # If this browser actually supports WebGL, this test requires real 3D,
        # not a screenshot pretending a model was rendered.
        supports_gl=page.evaluate("!!document.createElement('canvas').getContext('webgl')")
        if supports_gl:
            page.locator(".cage-hero-creature[data-graphics='procedural-3d']").wait_for(timeout=16000)
        mode=page.locator(".cage-hero-creature").get_attribute("data-graphics")
        page.screenshot(path=str(OUT/f"cage-{width}.png"),full_page=True,animations="disabled")
        assert not errors,(width,errors[:4])
        results.append((width,mode,"passed"))
        context.close()
    reduced=browser.new_context(viewport={"width":390,"height":844},reduced_motion="reduce")
    page=reduced.new_page()
    page.goto(ROOT+"/beast-cage",wait_until="domcontentloaded")
    expect(page.locator(".cage-universe")).to_have_attribute("data-reduced-motion","true")
    expect(page.locator(".cosmic-creature-fallback")).to_be_visible()
    no_overflow(page,"reduced-motion")
    page.screenshot(path=str(OUT/"reduced-motion.png"),full_page=True,animations="disabled")
    reduced.close()
    browser.close()
print("BEAST_CAGE_BROWSER_PASS",results,"Static reduced-motion fallback passed. No physical sensors accessed.")
