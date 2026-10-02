"""Real public UI-only footage; does not mock or claim successful model inference."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT="http://127.0.0.1:3100"
OUT=Path("browser-evidence/sidequest")
OUT.mkdir(parents=True,exist_ok=True)
(OUT/"video").mkdir(exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=["--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"])
 for width,height in [(1440,900),(390,844),(320,720)]:
  context=browser.new_context(viewport={"width":width,"height":height},device_scale_factor=1,record_video_dir=str(OUT/"video"),record_video_size={"width":width,"height":height})
  page=context.new_page()
  errors=[]
  sent=[]
  page.on("pageerror",lambda err:errors.append(str(err)))
  page.on("request",lambda req:sent.append(req.url) if "/api/guest" in req.url else None)
  response=page.goto(ROOT+"/beast-cage/talk",wait_until="domcontentloaded",timeout=45000)
  assert response and response.status==200
  expect(page.get_by_role("heading",name="Talk to the little Beast.")).to_be_visible()
  input=page.get_by_label("Say something to the Beast")
  input.fill("Hey Beast, introduce yourself!")
  expect(page.get_by_role("button",name="Send to real model")).to_be_enabled()
  page.wait_for_timeout(1900)
  assert not sent,"Recording MUST NOT use a simulated or paid chat request"
  assert not errors,(width,errors)
  assert page.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"),width
  page.screenshot(path=str(OUT/f"talk-{width}.png"),full_page=True,animations="disabled")
  video=page.video
  page.close()
  if video:video.save_as(str(OUT/f"demo-ui-{width}.webm"))
  context.close()
 reduced=browser.new_context(viewport={"width":390,"height":844},reduced_motion="reduce")
 page=reduced.new_page();page.goto(ROOT+"/beast-cage/talk",wait_until="domcontentloaded")
 expect(page.get_by_role("heading",name="Talk to the little Beast.")).to_be_visible()
 page.screenshot(path=str(OUT/"talk-reduced-motion.png"),full_page=True)
 reduced.close();browser.close()
print("REAL_SIDEQUEST_BROWSER_PASS UI footage recorded without fabricating model responses")
