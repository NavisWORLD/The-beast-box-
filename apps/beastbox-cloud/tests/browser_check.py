"""Browser acceptance for the isolated private preview; uses public CI-only credentials."""
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE="http://127.0.0.1:3100"
OUT=Path("browser-evidence")
OUT.mkdir(exist_ok=True)
PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a8AAAAABJRU5ErkJggg==")
results={}
def assert_no_overflow(page, tag):
    v=page.evaluate("({scroll:document.documentElement.scrollWidth, width:document.documentElement.clientWidth})")
    assert v["scroll"]<=v["width"]+1, f"{tag} overflow: {v}"

with sync_playwright() as p:
    browser=p.chromium.launch(channel="chrome",headless=True,args=["--no-sandbox"])
    desktop=browser.new_context(viewport={"width":1440,"height":900},device_scale_factor=1)
    unauth=desktop.new_page()
    errors=[]
    unauth.on("pageerror", lambda error:errors.append(str(error)))
    response=unauth.goto(BASE,wait_until="domcontentloaded")
    assert response and response.status==200
    assert unauth.get_by_text("Your AI.").count()>=1
    assert_no_overflow(unauth,"desktop landing")
    unauth.screenshot(path=str(OUT/"01-landing-desktop.png"),full_page=True)
    r=unauth.request.post(BASE+"/api/bridge/chat",data={"text":"Unauthorized attempt"})
    assert r.status==401, ("unauthenticated bridge",r.status)
    unauth.get_by_role("link",name="Enter Cosmic Chaos").click()
    unauth.get_by_label("OWNER PASSWORD").fill("public-ci-fixture-not-secret")
    unauth.get_by_role("button",name="Unlock workstation").click()
    unauth.get_by_text("BACKEND OFFLINE").wait_for(timeout=20000)
    assert unauth.get_by_text("Your conversation, your story.").count()==1
    assert unauth.get_by_role("button",name="Send message").is_disabled()
    unauth.screenshot(path=str(OUT/"02-workstation-desktop.png"),full_page=True)
    unauth.get_by_role("button",name="MEMORY VAULT").click()
    unauth.get_by_text("The memory vault.").wait_for(timeout=10000)
    assert unauth.get_by_text("No accessible records. Connect the real service to read your vault.").count()==1
    unauth.screenshot(path=str(OUT/"03-memory-desktop.png"),full_page=True)
    unauth.get_by_role("button",name="SETTINGS").click()
    unauth.get_by_text("Connect your universe").wait_for(timeout=10000)
    assert unauth.get_by_role("button",name="Hugging Face").count()==1
    assert unauth.get_by_role("button",name="Azure Blob Storage").count()==1
    assert unauth.get_by_role("button",name="IBM watsonx.ai").count()==1
    assert unauth.get_by_role("button",name="Ollama Cloud").count()==1
    assert unauth.get_by_role("button",name="Save encrypted credential").is_disabled()
    assert unauth.get_by_label("Live owner senses").is_visible()
    assert unauth.get_by_role("button",name="Start vision").is_visible()
    assert_no_overflow(unauth,"desktop BYOK settings")
    unauth.screenshot(path=str(OUT/"07-cloud-settings-desktop.png"),full_page=True)
    results["desktop"]="PASS: marketing, auth, offline gate, memory honesty, BYOK settings fail-closed"
    mobile=browser.new_context(viewport={"width":390,"height":844},device_scale_factor=1,is_mobile=True,has_touch=True)
    page=mobile.new_page()
    page.on("pageerror",lambda error:errors.append(str(error)))
    r=page.goto(BASE,wait_until="domcontentloaded")
    assert r and r.status==200
    assert_no_overflow(page,"mobile landing")
    page.screenshot(path=str(OUT/"04-landing-mobile.png"),full_page=True)
    page.goto(BASE+"/workspace",wait_until="domcontentloaded")
    page.get_by_label("OWNER PASSWORD").fill("public-ci-fixture-not-secret")
    page.get_by_role("button",name="Unlock workstation").click()
    page.get_by_text("BACKEND OFFLINE").wait_for(timeout=20000)
    assert_no_overflow(page,"mobile workstation")
    page.screenshot(path=str(OUT/"05-workstation-mobile.png"),full_page=True)
    page.get_by_role("button",name="Stage file or photo locally").click()
    page.locator('input[type="file"]').set_input_files({"name":"ci-photo.png","mimeType":"image/png","buffer":PNG})
    page.get_by_text("ci-photo.png").wait_for(timeout=8000)
    assert page.get_by_text("LOCAL ONLY").count()>0
    assert page.get_by_role("button",name="Send message").is_disabled()
    assert page.get_by_label("Live owner senses").is_hidden()
    assert_no_overflow(page,"mobile attachment")
    page.screenshot(path=str(OUT/"06-attachment-local-only.png"),full_page=True)
    page.get_by_role("button",name="Open navigation").click()
    page.get_by_role("button",name="SETTINGS").click()
    page.get_by_text("Connect your universe").wait_for(timeout=10000)
    assert page.get_by_role("button",name="Save encrypted credential").is_disabled()
    assert page.get_by_label("Live owner senses").is_visible()
    assert page.get_by_role("button",name="Start vision").is_visible()
    # Navigation must preserve the same mounted sensing component and keep chat usable.
    page.evaluate("""window.__sensesNode = document.querySelector('[aria-label="Live owner senses"]')""")
    assert_no_overflow(page,"mobile BYOK settings")
    page.screenshot(path=str(OUT/"08-cloud-settings-mobile.png"),full_page=True)
    page.get_by_role("button",name="Open navigation").click()
    page.get_by_role("button",name="BRAIN").click()
    assert page.get_by_label("Live owner senses").is_hidden()
    assert page.evaluate("""document.querySelector('[aria-label="Live owner senses"]') === window.__sensesNode""")
    page.get_by_role("button",name="Stage file or photo locally").click()
    assert page.get_by_role("button",name="Send message").is_disabled()
    assert_no_overflow(page,"mobile chat after settings")
    results["mobile"]="PASS: landing, auth, no overflow, photo stage only, BYOK settings fail-closed"
    assert not errors, "Client errors: "+str(errors)
    results["console_errors"]=errors
    browser.close()
(OUT/"result.json").write_text(json.dumps(results,indent=2)+"\n")
print("BROWSER_ACCEPTANCE="+json.dumps(results,sort_keys=True))
