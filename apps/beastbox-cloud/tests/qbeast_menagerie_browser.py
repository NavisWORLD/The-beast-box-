"""Real Chromium acceptance for the existing QBEAST Cage gallery.

No fake telemetry, network hardware request, saved creature mutation or ROM reset.
CI verifies 320/375/390/430/desktop and actual Canvas pixel alpha, not source strings.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=os.environ.get("BEASTBOX_BASE_URL","http://127.0.0.1:3100").rstrip("/")
OUT=Path(os.environ.get("MENAGERIE_EVIDENCE_DIR","browser-evidence/menagerie"))
OUT.mkdir(parents=True,exist_ok=True)
report=[]

with sync_playwright() as playwright:
    browser=playwright.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage","--use-gl=swiftshader"])
    try:
        for width,height in [(320,720),(375,812),(390,844),(430,932),(1280,900)]:
            context=browser.new_context(viewport={"width":width,"height":height},reduced_motion="reduce",device_scale_factor=1)
            page=context.new_page()
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto(BASE+"/beast-cage#menagerie",wait_until="domcontentloaded",timeout=60000)
            room=page.locator('[data-menagerie="recorded-archive"]')
            room.wait_for(state="visible",timeout=30000)
            first=room.locator("[data-archive-qbeast-id]").first
            first.wait_for(state="visible",timeout=75000)
            count=room.locator("[data-archive-qbeast-id]").count()
            assert 1<=count<=12, f"{width}: expected bounded real sprite cards, got {count}"
            before=page.evaluate("localStorage.getItem('beastbox-companion-session-v1')")
            ids=room.locator("[data-archive-qbeast-id]").evaluate_all("(items)=>items.map(x=>x.dataset.archiveQbeastId)")
            assert len(ids)==len(set(ids)),f"{width}: duplicate example IDs"
            def pixel_ready():
                return room.locator("[data-archive-qbeast-id] canvas").first.evaluate("""canvas=>{
                    if(!canvas.width||!canvas.height)return false;
                    const ctx=canvas.getContext('2d');
                    if(!ctx)return false;
                    const data=ctx.getImageData(0,0,canvas.width,canvas.height).data;
                    for(let i=3;i<data.length;i+=4){if(data[i]>0)return true}
                    return false;
                }""")
            page.wait_for_function("""()=>{const c=document.querySelector('#menagerie [data-archive-qbeast-id] canvas');
                if(!c)return false;const ctx=c.getContext('2d');if(!ctx)return false;
                const d=ctx.getImageData(0,0,c.width,c.height).data;
                for(let i=3;i<d.length;i+=4)if(d[i]>0)return true;return false;}""",timeout=30000)
            assert pixel_ready(),f"{width}: blank archive sprite"
            first.locator("summary").click()
            assert first.get_by_text("Count SHA-256").is_visible(),f"{width}: missing count receipt"
            first.locator("summary").click()
            assert room.get_by_text("DERIVED EXAMPLE",exact=False).first.is_visible()
            overflow=page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
            assert overflow<=1,f"{width}: {overflow}px horizontal overflow"
            next_btn=room.get_by_role("button",name="More recorded seeds")
            assert next_btn.is_enabled(),f"{width}: archive cannot page past first twelve"
            next_btn.click()
            page.wait_for_function("(oldId)=>document.querySelector('#menagerie [data-archive-qbeast-id]')?.dataset.archiveQbeastId !== oldId",arg=ids[0],timeout=30000)
            after_ids=room.locator("[data-archive-qbeast-id]").evaluate_all("(items)=>items.map(x=>x.dataset.archiveQbeastId)")
            assert after_ids[0]!=ids[0],f"{width}: pager did not change records"
            room.get_by_role("button",name="Previous seeds").click()
            page.wait_for_function("(original)=>document.querySelector('#menagerie [data-archive-qbeast-id]')?.dataset.archiveQbeastId===original",arg=ids[0],timeout=30000)
            assert page.evaluate("localStorage.getItem('beastbox-companion-session-v1')")==before,f"{width}: gallery changed the saved companion"
            assert not errors,f"{width}: JS errors: {errors}"
            room.screenshot(path=str(OUT/f"menagerie-{width}.png"))
            report.append({"width":width,"cards":count,"unique_ids":True,"canvas_pixels":True,"pagination":True,"no_local_save_mutation":True,"page_errors":errors,"horizontal_overflow_px":overflow})
            context.close()
    finally:
        browser.close()
(OUT/"report.json").write_text(json.dumps({"url":BASE+"/beast-cage#menagerie","mode":"Chromium reduced motion; NOT physical Safari","views":report},indent=2)+"\n")
print(json.dumps(report,indent=2))
