"""Genuine built-app browser checks for seeded Genesis and portable BCP1 game assets."""
from pathlib import Path
import json, os, re, struct, zipfile, zlib
from playwright.sync_api import sync_playwright, expect

BASE=os.environ.get("GENESIS_BASE","http://127.0.0.1:3100")
OUT=Path("browser-evidence/cosmic-genesis")
OUT.mkdir(parents=True,exist_ok=True)
SIZES=[(1440,900),(430,932),(390,844),(320,720)]

def layout_ok(page,label):
 sizes=page.evaluate("({scroll:document.documentElement.scrollWidth,width:document.documentElement.clientWidth})")
 assert sizes["scroll"]<=sizes["width"]+1,(label,sizes)

with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=[
  "--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"
 ])
 for width,height in SIZES:
  context=browser.new_context(viewport={"width":width,"height":height},
    device_scale_factor=1,is_mobile=width<500,has_touch=width<500,accept_downloads=True)
  page=context.new_page()
  errors=[];privileged=[]
  page.on("pageerror",lambda error:errors.append(str(error)))
  page.on("request",lambda request:privileged.append(request.url) if "/api/bridge/" in request.url else None)
  result=page.goto(BASE+"/beast-cage/guest",wait_until="domcontentloaded",timeout=40000)
  assert result and result.status==200
  layout_ok(page,f"{width} initial")
  forge=page.get_by_role("region",name="Genesis Forge procedural character generator")
  forge.get_by_label("Character seed").fill("genesis-v1-acceptance")
  forge.get_by_label("Cosmic family").select_option("nebula")
  forge.get_by_role("button",name="Generate from this seed").click()
  card=forge.get_by_label("Balanced fictional game stats")
  expect(card).to_be_visible()
  initial=card.inner_text()
  # Family and appearance options must not silently reroll gameplay attributes.
  forge.get_by_label("Cosmic family").select_option("aurora")
  forge.get_by_role("button",name="Generate from this seed").click()
  assert card.inner_text()==initial,(width,"cosmetic family changed game stats")
  forge.get_by_role("button",name="Let it explore").click()
  expect(forge.get_by_text("Classical seeded behavior",exact=False)).to_be_visible()
  forge.get_by_role("button",name="Save game character on this device").click()
  saved=page.evaluate("localStorage.getItem('beastbox-genesis-v1-saved-game-characters')")
  assert saved and len(json.loads(saved))==1
  page.reload(wait_until="domcontentloaded")
  saved_label=forge.get_by_role("button",name=re.compile("^Select "))
  expect(saved_label).to_be_visible()
  saved_label.click()
  assert card.inner_text()==initial
  # Exact real public browser download: inspect bytes, CRC, extension, and privacy flags.
  button=page.get_by_role("button",name=re.compile("Download my GBA companion"))
  with page.expect_download(timeout=20000) as pending:button.click()
  download=pending.value
  assert download.suggested_filename.startswith("beast-cage-bb-"),download.suggested_filename
  path=OUT/f"actual-aurora-{width}.zip";download.save_as(path)
  with zipfile.ZipFile(path) as archive:
   assert archive.testzip() is None
   tiles=archive.read("gba/companion_tiles.4bpp")
   palette=archive.read("gba/companion_palette.bgr555")
   legacy=archive.read("gba/companion_state.bin")
   game=archive.read("gba/companion_profile.bin")
   profile=json.loads(archive.read("companion.profile.json"))
   soul=json.loads(archive.read("companion.soul.json"))
   assert len(tiles)==8192 and len(palette)==32
   assert len(legacy)==60 and legacy[:4]==b"BCG1" and legacy[6]==0
   assert len(game)==64 and game[:4]==b"BCP1" and game[4]==1
   assert struct.unpack_from("<I",game,60)[0]==zlib.crc32(game[:60])
   assert sum(game[8:18])==500 and all(20<=n<=80 for n in game[8:18])
   assert profile["family"]=="aurora" and profile["seed"]=="genesis-v1-acceptance"
   assert soul["includes_personal_memories"] is False and soul["tool_authority"] is False
   assert soul["signals"]["measured"] is False
   assert "gba/beast_creature_profile.c" in archive.namelist()
  layout_ok(page,f"{width} exported")
  page.screenshot(path=str(OUT/f"forge-{width}.png"),full_page=True,animations="disabled")
  assert not errors,(width,errors)
  assert not privileged,(width,privileged)
  context.close()
 reduced=browser.new_context(viewport={"width":390,"height":844},reduced_motion="reduce")
 page=reduced.new_page()
 page.goto(BASE+"/beast-cage/guest",wait_until="domcontentloaded")
 expect(page.locator('[data-spark-beast="true"]').first).to_be_visible()
 layout_ok(page,"reduced-motion")
 page.screenshot(path=str(OUT/"reduced-motion.png"),full_page=True,animations="disabled")
 reduced.close();browser.close()
print("COSMIC_GENESIS_REAL_BROWSER_PASS: four actual responsive widths, deterministic stats, opted-in local save, CRC32 GBA export, guest isolation, reduced-motion Spark companion.")
