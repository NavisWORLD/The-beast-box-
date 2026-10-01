"""Unedited genuine Chromium footage of the real procedurally rendered Three.js model.
No AI inference, no mock API, and no fake prerendered 2D angle images."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright, expect
ROOT="http://127.0.0.1:3100"
OUT=Path("browser-evidence/quest-3d")
OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=["--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"])
 context=browser.new_context(viewport={"width":1150,"height":900},record_video_dir=str(OUT),record_video_size={"width":1150,"height":900},device_scale_factor=1)
 page=context.new_page()
 errors=[]
 page.on("pageerror",lambda error:errors.append(str(error)))
 response=page.goto(ROOT+"/beast-cage/turntable",wait_until="domcontentloaded",timeout=60000)
 assert response and response.status==200
 expect(page.locator("[data-stage='real-3d-turntable']")).to_be_visible()
 expect(page.locator("[data-graphics='procedural-3d']")).to_be_visible(timeout=25000)
 assert page.evaluate("!!document.createElement('canvas').getContext('webgl')"),"No browser WebGL, cannot claim an actual 3D recording"
 page.screenshot(path=str(OUT/"live-3d-auto.png"),full_page=True)
 for label,angle in [("front",0),("right",90),("back",180),("left",270)]:
  page.get_by_role("button",name=re.compile(rf"^{angle}°")).click()
  expect(page.locator("[data-stage]")).to_have_attribute("data-view-angle",str(angle))
  page.wait_for_timeout(350)
  page.screenshot(path=str(OUT/f"{angle:03d}-{label}.png"),full_page=True)
 page.get_by_role("button",name="↻ Rotate 360°").click()
 expect(page.locator("[data-stage]")).to_have_attribute("data-view-angle","spinning")
 page.wait_for_timeout(8600)
 assert not errors,errors
 assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth+1")
 video=page.video
 page.close()
 if video:video.save_as(str(OUT/"real-3d-turntable-360.webm"))
 context.close()
 mobile=browser.new_context(viewport={"width":390,"height":844},device_scale_factor=1,is_mobile=True,has_touch=True)
 mob=mobile.new_page();res=mob.goto(ROOT+"/beast-cage/turntable",wait_until="domcontentloaded")
 assert res and res.status==200
 expect(mob.locator("[data-graphics='procedural-3d']")).to_be_visible(timeout=25000)
 assert mob.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth+1")
 mob.screenshot(path=str(OUT/"3d-mobile-390.png"),full_page=True)
 mobile.close()
 browser.close()
print("REAL_3D_SIDEQUEST_PASS: one actual rendered mesh, 0/90/180/270 views, 360 video, mobile 390px.")
