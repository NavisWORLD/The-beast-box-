"""Real browser download acceptance: guest can export GBA assets without auth."""
from pathlib import Path
import json,zipfile,io,urllib.request
from playwright.sync_api import sync_playwright,expect
ROOT="http://127.0.0.1:3100"
OUT=Path("browser-evidence/gba-export")
OUT.mkdir(parents=True,exist_ok=True)
def no_overflow(page):
 return page.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1")
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=["--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"])
 for width,height in [(1440,900),(430,932),(390,844),(375,812),(320,720)]:
  ctx=browser.new_context(viewport={"width":width,"height":height},is_mobile=width<500,has_touch=width<500,accept_downloads=True)
  page=ctx.new_page()
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  resp=page.goto(ROOT+"/beast-cage/guest",wait_until="domcontentloaded")
  assert resp and resp.status==200
  expect(page.get_by_role("heading",name="Your Beast. Ready to play.")).to_be_visible()
  expect(page.get_by_label("Configure and export game companion").get_by_role("link",name="Play Lost COSMOS")).to_be_visible()
  assert no_overflow(page),width
  page.get_by_role("button",name="Aurora").click()
  page.get_by_role("button",name="Celebrate").click()
  expect(page.get_by_role("button",name="Celebrate")).to_have_attribute("aria-pressed","true")
  if width in (1440,390,320):page.screenshot(path=str(OUT/("guest-"+str(width)+".png")),full_page=True,animations="disabled")
  page.get_by_text("Exports & developer files",exact=True).click()
  with page.expect_download(timeout=12000) as pending:
   page.get_by_role("button",name="Download my GBA companion (.zip)").click()
  download=pending.value
  assert download.suggested_filename.startswith("beast-cage-bb-")
  assert download.suggested_filename.endswith("-gba-module.zip")
  path=OUT/("pack-"+str(width)+".zip")
  download.save_as(path)
  with zipfile.ZipFile(path) as z:
   assert z.testzip() is None
   names=set(z.namelist())
   expected={"gba/companion_tiles.4bpp","gba/companion_palette.bgr555","gba/companion_assets.h","gba/companion_state.bin","companion.soul.json","gba/beast_companion.c","gba/beast_companion.h","gba/AGENTS.md","art/cosmic-creature.svg"}
   assert expected<=names,names
   assert len(z.read("gba/companion_tiles.4bpp"))==8192
   assert len(z.read("gba/companion_palette.bgr555"))==32
   state=z.read("gba/companion_state.bin")
   assert len(state)==60 and state[:4]==b"BCG1" and state[6]==0 and state[8:]==b"\0"*52
   soul=json.loads(z.read("companion.soul.json"))
   assert soul["signals"]["measured"] is False
   assert soul["signals"]["cns_dyn12"] is None
   assert soul["includes_personal_memories"] is False
   assert soul["tool_authority"] is False
   assert soul["visual_look"]=="aurora"
  assert no_overflow(page)
  assert not errors,(width,errors[:3])
  ctx.close()
 code,json_url=urllib.request.urlopen(ROOT+"/api/gba-release").status,ROOT+"/api/gba-release"
 assert code==200
 browser.close()
print("BEAST_CAGE_GBA_GUEST_BROWSER_PASS: real GBA ZIP, 5 responsive sizes, no owner data")
