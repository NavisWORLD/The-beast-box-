"""Browser checks for the shared COSMOS sound bus. Not a physical iPhone test."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE=os.environ.get("BEASTBOX_BASE_URL","http://127.0.0.1:3100").rstrip("/")
OUT=Path(os.environ.get("BEAST_SOUND_EVIDENCE_DIR","browser-evidence/site-sound"))
OUT.mkdir(parents=True,exist_ok=True)
AUDIO_PROBE="""(() => {
 window.__cosmosAudio={contexts:0,oscillators:0};
 const Native=window.AudioContext||window.webkitAudioContext;
 if(!Native)return;
 const Wrapped=new Proxy(Native,{construct(target,args){
  const context=Reflect.construct(target,args);
  window.__cosmosAudio.contexts++;
  const make=context.createOscillator.bind(context);
  context.createOscillator=(...oscArgs)=>{window.__cosmosAudio.oscillators++;return make(...oscArgs);};
  return context;
 }});
 if(window.AudioContext)window.AudioContext=Wrapped;
 if(window.webkitAudioContext)window.webkitAudioContext=Wrapped;
})();"""
results=[]
with sync_playwright() as playwright:
 launch={"headless":True,"args":["--no-sandbox","--disable-dev-shm-usage"]}
 if os.environ.get("SUPPORT_BROWSER_EXECUTABLE"):
  launch["executable_path"]=os.environ["SUPPORT_BROWSER_EXECUTABLE"]
 browser=playwright.chromium.launch(**launch)
 try:
  for width in [320,375,390,430,1440]:
   context=browser.new_context(viewport={"width":width,"height":844},
         has_touch=width<600,reduced_motion="reduce" if width==320 else "no-preference")
   context.add_init_script(AUDIO_PROBE)
   page=context.new_page()
   errors=[]
   page.on("pageerror",lambda err: errors.append(str(err)))
   response=page.goto(BASE,wait_until="domcontentloaded",timeout=60000)
   assert response and response.status==200
   pill=page.locator('[aria-label="Cosmic sound controls"]')
   expect(pill).to_be_visible()
   expect(page.get_by_role("button",name="Activate Beast Box sound with a test chirp")).to_be_visible()
   assert page.evaluate("window.__cosmosAudio.contexts")==0,"audio context created without user interaction"
   assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),f"{width} horizontal overflow"
   # A real click/tap is required before music/SFX may schedule.
   settings=page.get_by_role("button",name="Open sound options")
   settings.tap() if width<600 else settings.click()
   # User-facing proof of WebAudio initialization: a gesture, a real context and oscillators.
   chirp=page.get_by_role("button",name="Test Beast Box sound with a short chirp")
   chirp.tap() if width<600 else chirp.click()
   expect(page.get_by_role("button",name="Mute the entire Beast Box site")).to_be_visible(timeout=10000)
   assert page.evaluate("window.__cosmosAudio.contexts")>=1,"No AudioContext after activation"
   assert page.evaluate("window.__cosmosAudio.oscillators")>=1,"No oscillator after test chirp"
   if width<600:
    assert pill.bounding_box()["width"]<112,"Mobile sound controls block creature or buttons"
    support=page.get_by_role("button",name="Open Feed the Beast support panel")
    expect(support).to_be_visible()
    assert support.bounding_box()["width"]<=72,"Support launcher covers mobile care and gallery"
   slider=page.get_by_role("slider",name="Beast Box music, creature and effect volume")
   expect(slider).to_be_visible()
   slider.press("Home")
   for _ in range(5):slider.press("ArrowRight")
   assert abs(page.evaluate("JSON.parse(localStorage.getItem('beastbox-music-v1')).volume")-.25)<.001
   page.get_by_role("button",name="Mute the entire Beast Box site").click()
   assert page.evaluate("localStorage.getItem('beastbox-site-sound-v1')")=="off"
   expect(page.get_by_role("button",name="Enable sound throughout Beast Box")).to_be_visible()
   # Fresh document obeys saved explicit mute; a muted support pet stays silent.
   page.goto(BASE+"/beast-cage",wait_until="domcontentloaded")
   expect(page.get_by_role("button",name="Enable sound throughout Beast Box")).to_be_visible()
   assert page.evaluate("localStorage.getItem('beastbox-site-sound-v1')")=="off"
   page.get_by_role("button",name="Enable sound throughout Beast Box").click()
   expect(page.get_by_role("button",name="Mute the entire Beast Box site")).to_be_visible()
   assert page.evaluate("localStorage.getItem('beastbox-site-sound-v1')")=="on"
   expect(page.locator('[aria-label="Cosmic sound controls"]')).to_be_visible()
   assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),f"{width} Cage overflow"
   assert not errors, f"{width} errors: {errors}"
   if width==390:
    # Static /spark page has its own sound button. On iPhone it must ACTIVATE,
    # not interpret the first attempt as an instruction to mute.
    page.goto(BASE+"/spark/index.html",wait_until="domcontentloaded",timeout=60000)
    voice=page.locator("#voice")
    expect(voice).to_contain_text("TAP FOR SOUND",timeout=30000)
    voice.tap()
    expect(voice).to_contain_text("SOUND ON",timeout=15000)
    assert page.evaluate("window.__cosmosAudio.contexts")>=1,"Static Spark did not open audio after tap"
   page.screenshot(path=str(OUT/f"sound-{width}.png"))
   results.append({"width":width,"no_autoplay":True,"chirp_oscillator_rendered":True,"compact_mobile_sound":True,"mute_persisted":True,"volume_persisted":True,"unmute_after_navigation":True,"no_horizontal_overflow":True,"errors":errors})
   context.close()
 finally:browser.close()
(OUT/"report.json").write_text(json.dumps({"mode":"Chrome viewport checks, NOT physical Safari","views":results},indent=2)+"\n")
print(json.dumps(results))
