from pathlib import Path
import json
from playwright.sync_api import sync_playwright
root=Path("tools/devday/updated-cosmic-deck-v2").resolve()
out=Path("recorded-cosmic-deck-v2").resolve();out.mkdir(exist_ok=True)
issues=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=["--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"])
 context=browser.new_context(viewport={"width":1280,"height":720},record_video_dir=str(out),record_video_size={"width":1280,"height":720})
 page=context.new_page();page.on("pageerror",lambda e:issues.append(str(e)))
 result=page.goto((root/"index.html").as_uri(),wait_until="domcontentloaded");assert result and result.status==200
 assert page.get_by_role("heading",name="THE BEAST, UNDER CONTROL.").count()==1
 assert page.locator(".model").count()==5
 assert page.locator("[data-stage]").count()==8
 page.wait_for_timeout(1300);page.screenshot(path=str(out/"01-hero.png"))
 page.locator('[data-view="3d"]').click()
 assert "playing" in (page.locator("#companion").get_attribute("class") or "")
 page.wait_for_timeout(2600);page.screenshot(path=str(out/"02-actual-3d-demo.png"))
 page.locator('[data-view="art"]').click();page.wait_for_timeout(500)
 page.locator("#models").scroll_into_view_if_needed();page.wait_for_timeout(900)
 for model in ["PHOS","SAMGO","MUSE","SOL","RAWRPHØS"]:
  page.locator('[data-model="'+model+'"]').click();assert page.locator("#picked").inner_text()==model
  page.wait_for_timeout(650)
 page.screenshot(path=str(out/"03-unique-family-logos.png"))
 page.locator("#signals").scroll_into_view_if_needed();page.wait_for_timeout(850)
 for stage in [2,4,5,7]:
  b=page.locator('[data-stage="'+str(stage)+'"]');b.click();assert b.get_attribute("aria-pressed")=="true";page.wait_for_timeout(700)
 page.screenshot(path=str(out/"04-signal-path.png"))
 page.locator("#real3d").scroll_into_view_if_needed();page.wait_for_timeout(900)
 page.locator("#full3d").evaluate('v=>{v.muted=true;v.currentTime=2;v.play().catch(()=>{});}')
 page.wait_for_timeout(5300);page.screenshot(path=str(out/"05-real-turntable.png"))
 page.locator("#models").scroll_into_view_if_needed();page.wait_for_timeout(1200)
 assert not issues,issues
 assert page.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1")
 vid=page.video;page.close();vid.save_as(str(out/"actual-updated-deck-browser.webm"));context.close()
 receipt={"desktop":"PASS","controls":"5 independently illustrated identities, 8 real UI stage controls, previously recorded genuine 3D clip","page_errors":[]}
 for w in [320,390,430]:
  cx=browser.new_context(viewport={"width":w,"height":800},is_mobile=True,has_touch=True,reduced_motion="reduce")
  pg=cx.new_page();rr=pg.goto((root/"index.html").as_uri(),wait_until="domcontentloaded");assert rr and rr.status==200
  assert pg.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"),f"overflow: {w}"
  pg.locator('[data-model="PHOS"]').click();assert pg.locator("#picked").inner_text()=="PHOS"
  pg.locator('[data-stage="4"]').click();assert pg.locator("#stage-name").inner_text()=="Persistent COSMOS memory"
  pg.screenshot(path=str(out/f"mobile-{w}.png"),full_page=True,animations="disabled")
  cx.close();receipt[f"mobile_{w}"]="PASS"
 browser.close()
(out/"RECORDING_RECEIPTS.json").write_text(json.dumps(receipt,indent=2),encoding="utf8")
print(json.dumps(receipt))
