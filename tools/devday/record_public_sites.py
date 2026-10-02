"""Only capture *public and unauthenticated* sites; no owner login or fake content."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path("public-site-evidence")
out.mkdir(parents=True,exist_ok=True)
candidates={
    "chatgpt_site":"https://beast-box-control-deck-cory.pheras-king.chatgpt.site",
    "beastbox_production":"https://www.beastboxcosmos.xyz"
}
receipts={}
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox","--enable-webgl","--use-gl=angle","--use-angle=swiftshader"])
    for label,url in candidates.items():
        context=browser.new_context(viewport={"width":1360,"height":780},device_scale_factor=1,record_video_dir=str(out))
        page=context.new_page()
        try:
            resp=page.goto(url,wait_until="domcontentloaded",timeout=30000)
            page.wait_for_timeout(1700)
            title=page.title()
            text=page.locator("body").inner_text(timeout=6000)[:1500]
            final=page.url
            status=resp.status if resp else None
            # Auth/login or transient error pages do NOT count as public pages.
            blocked=status!=200 or any(s in (title+" "+text[:250]).lower() for s in ("sign in to","authentication required","access denied","you need permission","page not found","404 not found"))
            receipts[label]={"url":url,"final":final,"status":status,"title":title,"blocked":blocked,"excerpt":text[:180]}
            if blocked:
                page.close(); context.close()
                continue
            page.screenshot(path=str(out/f"{label}-real-public.png"),full_page=True,animations="disabled")
            page.mouse.move(1040,440)
            page.wait_for_timeout(2000)
            page.mouse.wheel(0,660)
            page.wait_for_timeout(2400)
            page.mouse.wheel(0,-500)
            page.wait_for_timeout(1500)
            video=page.video
            page.close()
            if video:video.save_as(str(out/f"{label}-real-public.webm"))
        except Exception as e:
            receipts[label]={"url":url,"status":None,"blocked":True,"reason":str(e)[:350]}
            try:page.close()
            except Exception:pass
        finally:
            context.close()
    browser.close()
(out/"PROOF.json").write_text(json.dumps(receipts,indent=2),encoding="utf8")
print(json.dumps(receipts))
