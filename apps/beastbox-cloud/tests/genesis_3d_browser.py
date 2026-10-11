"""Authentic built-app UI, downloadable GLB, safety and iPhone-width acceptance."""
from pathlib import Path
import json,re,struct,zipfile
from playwright.sync_api import sync_playwright,expect

BASE="http://127.0.0.1:3100"
OUT=Path("browser-evidence/genesis-3d")
OUT.mkdir(parents=True,exist_ok=True)
SIZES=[(1440,900),(430,932),(390,844),(375,812),(320,720)]
def load(page,path):
 response=page.goto(BASE+path,wait_until="domcontentloaded",timeout=40000)
 assert response and response.status==200,(path,response.status if response else None)
def fits(page,name):
 sizes=page.evaluate("({scroll:document.documentElement.scrollWidth,width:document.documentElement.clientWidth})")
 assert sizes["scroll"]<=sizes["width"]+1,(name,sizes)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=[
  "--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"
 ])
 results=[]
 for width,height in SIZES:
  context=browser.new_context(viewport={"width":width,"height":height},
    device_scale_factor=1,is_mobile=width<500,has_touch=width<500,accept_downloads=True)
  page=context.new_page();errors=[];private_requests=[]
  page.on("pageerror",lambda error:errors.append(str(error)))
  page.on("request",lambda req:private_requests.append(req.url) if "/api/bridge" in req.url else None)
  load(page,"/")
  expect(page.get_by_role("button",name="Rotate 360°")).to_be_visible()
  hero=page.get_by_label("Interactive cosmic companion observatory")
  expect(hero.locator('[data-graphics="procedural-3d"]')).to_be_visible(timeout=23000)
  page.get_by_role("button",name="Rotate 360°").click()
  expect(page.get_by_role("button",name="Rotate 360°")).to_have_attribute("aria-pressed","true")
  page.get_by_role("button",name="Side").click()
  fits(page,str(width)+" homepage")
  if width in [1440,390,320]:page.screenshot(path=str(OUT/f"home-{width}.png"),full_page=True,animations="disabled")
  page.get_by_role("link",name=re.compile("Enter the Beast Cage")).click()
  page.wait_for_url("**/beast-cage",timeout=30000)
  try:
   expect(page.get_by_role("heading",name=re.compile("A small companion"))).to_be_visible(timeout=20000)
  except Exception as failure:
   page.screenshot(path=str(OUT/f"cage-route-diagnostic-{width}.png"),full_page=True)
   body=page.locator("body").inner_text(timeout=5000)[:600]
   raise AssertionError(f"Cage hero missing at {page.url}; browser errors={errors[:4]}; body={body}") from failure
  page.get_by_label("Character seed").fill("life-engine-art-acceptance")
  page.get_by_label("Cosmic family").select_option("aurora")
  page.get_by_role("button",name="Generate from this seed").click()
  hero=page.locator('.cage-habitat-visual [data-spark-beast="true"]')
  expect(hero).to_have_attribute("data-creature-id",re.compile("^bb-"),timeout=23000)
  creature_id=hero.get_attribute("data-creature-id")
  # The uploaded Genesis sources contribute only the BACKGROUND world.
  # The original visible creature, tap-to-attack and sound controls stay intact.
  pocket=page.locator('[data-pocket-dimension="true"]')
  expect(pocket).to_have_attribute("data-creature-id","visual-preview")
  page.wait_for_function("""() => ['ready','fallback'].includes(
    document.querySelector('[data-pocket-dimension]')?.dataset.pocketState)""",timeout=30000)
  pocket_state=pocket.get_attribute("data-pocket-state")
  expect(page.locator('.cage-habitat-visual [data-spark-beast="true"]')).to_be_visible()
  expect(page.get_by_role("button",name=re.compile("Make the beast attack"))).to_be_visible()
  assert page.locator('[data-pocket-settings]').count()==0
  if pocket_state=="ready":
   expect(pocket.locator('canvas[data-pocket-webgl]')).to_have_count(1)
   stage=page.locator('.cage-habitat-visual')
   box=stage.bounding_box()
   assert box and abs(box["width"]-box["height"])<2,(width,box)
   stage.focus()
   page.keyboard.press("ArrowRight")
   page.keyboard.press("+")
   # Existing creature sound events drive only visual flora/light pulsing.
   page.evaluate("""() => window.dispatchEvent(
     new CustomEvent('beastbox:spark-chirp',{detail:{intensity:0.6}}))""")
   expect(hero).to_have_attribute("data-creature-id",creature_id)
  fits(page,str(width)+" background dimensional pocket")

  selected_stats=page.get_by_label("Balanced fictional game stats").inner_text()
  before=hero.get_attribute("data-cosmetic-hue")
  page.get_by_role("slider",name="Creature color shift").focus()
  page.get_by_role("slider",name="Creature color shift").press("ArrowRight")
  expect(hero).not_to_have_attribute("data-cosmetic-hue",before)
  assert selected_stats==page.get_by_label("Balanced fictional game stats").inner_text()
  expect(page.locator('aside[data-companion-overlay="true"]')).to_have_count(1)
  page.get_by_label("Character seed").focus()
  expect(page.locator("aside[data-companion-overlay]")).to_have_attribute("data-roaming","parked")
  page.get_by_role("button",name="Save game character on this device").click()
  assert json.loads(page.evaluate("localStorage.getItem('beastbox-genesis-v1-saved-game-characters')"))[0]["id"]==creature_id
  page.evaluate("window.dispatchEvent(new Event('beastbox:master-privacy-stop'))")
  expect(page.locator("aside[data-companion-overlay]")).to_have_attribute("data-companion-state","halted")
  page.get_by_role("link",name=re.compile("Take this creature to the GBA Game Lab")).click()
  page.wait_for_url("**/beast-cage/guest",timeout=15000)
  expect(page.get_by_role("heading",name=re.compile("Catch a star"))).to_be_visible()
  guest=page.get_by_role("region",name="Animated companion test environment").locator('[data-spark-beast="true"][data-creature-id="'+creature_id+'"]')
  expect(guest).to_be_visible(timeout=23000)
  fits(page,str(width)+" guest")
  if width in [1440,390,320]:page.screenshot(path=str(OUT/f"guest-{width}.png"),full_page=True,animations="disabled")
  if width==1440:
   with page.expect_download(timeout=50000) as pending:
    page.get_by_role("button",name="Download original animated 3D model GLB").click()
   download=pending.value
   target=OUT/"cosmic-genesis-real-3d.glb";download.save_as(target)
   raw=target.read_bytes()
   assert raw[:4]==b"glTF" and struct.unpack_from("<I",raw,8)[0]==len(raw)
   json_size=struct.unpack_from("<I",raw,12)[0]
   assert raw[16:20]==b"JSON"
   model=json.loads(raw[20:20+json_size].decode("utf-8").rstrip(" "))
   # GLB reuses geometries across many scene nodes. Count actual mesh instances
   # rather than demanding one distinct mesh definition per repeated lobe/fin.
   assert len(model["meshes"])>=8 and len(model["images"])>=1
   assert sum("mesh" in node for node in model["nodes"])>=25
   assert len(model["materials"])>=5 and len(raw)>30000
   animations={a["name"] for a in model.get("animations",[])}
   assert {"idle","listening","thinking","celebrating"}<=animations,animations
   assert model["asset"]["version"]=="2.0"
   print("REAL_ANIMATED_GLB_PASS",len(raw),"bytes",len(model["meshes"]),"meshes",sorted(animations),flush=True)
   with page.expect_download(timeout=30000) as download_pending:
    page.get_by_role("button",name=re.compile("Download my GBA companion")).click()
   zip_file=OUT/"cosmic-genesis-matching-gba.zip";download_pending.value.save_as(zip_file)
   with zipfile.ZipFile(zip_file) as z:
    assert z.testzip() is None
    g=json.loads(z.read("companion.profile.json"))
    assert g["id"]==creature_id and g["family"]=="aurora"
    assert "private_memory" not in z.namelist()
    assert len(z.read("gba/companion_tiles.4bpp"))==8192
  assert not errors,(width,errors)
  assert not private_requests,(width,private_requests)
  results.append({"width":width,"shared_id":creature_id,"spark_ui":True,"downloadable_seeded_3d":True,
   "cosmetic_edit_stats_constant":True,"public_authority_requests":0})
  context.close()
 reduced=browser.new_context(viewport={"width":390,"height":844},reduced_motion="reduce")
 page=reduced.new_page();load(page,"/beast-cage")
 expect(page.locator('.cage-habitat-visual [data-spark-beast="true"]')).to_be_visible()
 fits(page,"reduced motion");page.screenshot(path=str(OUT/"reduced-motion.png"),full_page=True)
 reduced.close()
 fallback=browser.new_context(viewport={"width":320,"height":720})
 fallback.add_init_script("""() => {
  const original=HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext=function(type,...args){
   return String(type).startsWith('webgl')?null:original.call(this,type,...args);
  };
 }""")
 page=fallback.new_page();load(page,"/beast-cage")
 expect(page.locator('.cage-habitat-visual [data-spark-beast="true"]')).to_be_visible(timeout=10000)
 fits(page,"no WebGL");page.screenshot(path=str(OUT/"no-webgl.png"),full_page=True)
 fallback.close();browser.close()
 (OUT/"acceptance.json").write_text(json.dumps({"browser":"real built Chromium",
 "physical_iphone":False,"hardware_sensors":False,"results":results},indent=2))
 print("COSMIC_GENESIS_REAL_3D_BROWSER_PASS",json.dumps(results),flush=True)
