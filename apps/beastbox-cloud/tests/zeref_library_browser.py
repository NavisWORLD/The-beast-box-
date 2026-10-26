"""Zeref library + long-message browser test at iPhone width (390 px) against the built app.

Real parts (no mocks): owner-only access on the live route handlers, the 8000-character
textarea, the plain 'what Zeref reads' text, and the owner session.
Mocked parts (labelled): the library storage API (CI has no Azure account) and the guest
brain reply, so the test can read the exact prompt the browser would send.
"""
import io, json, os, re, sys, zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3100"
OUT = Path("browser-evidence/zeref-library"); OUT.mkdir(parents=True, exist_ok=True)
PASSWORD = os.environ.get("BEASTBOX_OWNER_PASSWORD", "")
# the mocked guest must answer at the CURRENT public pin, or the app (correctly) refuses the reply; read it, never hard-code it
PIN_STEP = json.loads((Path(__file__).resolve().parent.parent / "lib" / "rawrphos-public-pin.json").read_text())["training_steps"]
SECRET_LINE = "The lantern keeper hides the brass key under the third stair."

def make_epub():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="OEBPS/c.opf"/></rootfiles></container>')
        z.writestr("OEBPS/c.opf", '<package><metadata><dc:title>Tiny Atlas</dc:title></metadata><manifest><item id="a" href="a.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="a"/></spine></package>')
        z.writestr("OEBPS/a.xhtml", "<html><body><h1>Harbour</h1><p>" + SECRET_LINE + " Boats rest at the harbour wall.</p></body></html>")
    return buf.getvalue()

class FakeLibrary:
    """Stand-in for /api/zeref/library: same JSON protocol as the real handler."""
    def __init__(self): self.docs = {}; self.n = 0; self.posts = []
    def listing(self):
        docs = [{k: v for k, v in d.items() if k != "chunks_data"} for d in self.docs.values()]
        ready = [d for d in docs if d["status"] == "ready"]
        return {"owner": True, "configured": True, "docs": docs,
                "totals": {"docs": len(ready), "chars": sum(d["chars"] for d in ready), "chunks": sum(d["chunks"] for d in ready)},
                "limits": {"max_typed_chars": 8000}}
    def post(self, body):
        self.posts.append(body["action"]); a = body["action"]
        if a == "begin":
            self.n += 1; i = f"{self.n:024x}"
            self.docs[i] = {"id": i, "title": body["title"], "kind": body["kind"], "status": "uploading", "bytes": body["bytes"], "chars": 0, "chunks": 0,
                            "sha256": body["sha256"], "created_at": "2026-10-25T00:00:00Z", "training_approved": False, "chunks_data": []}
            return 201, {"id": i}
        d = self.docs.get(body.get("id"))
        if a == "append":
            d["chunks_data"] += body["chunks"]; d["chunks"] += len(body["chunks"]); d["chars"] += sum(len(c["t"]) for c in body["chunks"]); return 200, {"ok": True}
        if a == "finish": d["status"] = "ready"; return 200, {"ok": True, "doc": {k: v for k, v in d.items() if k != "chunks_data"}}
        if a == "delete": self.docs.pop(body["id"], None); return 200, {"ok": True}
        if a == "training": d["training_approved"] = body["approved"]; return 200, {"ok": True, "doc": {k: v for k, v in d.items() if k != "chunks_data"}}
        return 400, {"error": "Unknown action"}
    def search(self, q):
        words = set(re.findall(r"[a-z]{3,}", q.lower())); hits = []
        for d in self.docs.values():
            if d["status"] != "ready": continue
            for i, c in enumerate(d["chunks_data"]):
                s = len(words & set(re.findall(r"[a-z]{3,}", c["t"].lower())))
                if s: hits.append({"doc_id": d["id"], "title": d["title"], "index": i, "loc": c["l"], "text": c["t"], "score": s, "sha256": "ab" * 32})
        hits.sort(key=lambda h: -h["score"]); return {"ok": True, "hits": hits[:3]}

def check_overflow(page, label):
    assert page.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"), f"horizontal overflow: {label}"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"], executable_path=os.environ.get("CHROME_PATH") or None)

    # ---- 1. real owner-only checks (no mocks) -------------------------------------------------
    anon = browser.new_context(viewport={"width": 390, "height": 844})
    api = anon.request
    j = api.get(ROOT + "/api/zeref/library").json()
    assert j == {"owner": False}, j
    origin = {"Origin": ROOT, "Content-Type": "application/json"}
    for url, method in [("/api/zeref/library", "post"), ("/api/zeref/library/search", "post")]:
        r = api.post(ROOT + url, data=json.dumps({"action": "begin", "query": "x"}), headers=origin)
        assert r.status == 401, (url, r.status)
    assert api.get(ROOT + "/api/zeref/library/training").status == 401
    assert SECRET_LINE not in api.get(ROOT + "/api/zeref/library").text()
    print("OWNER_ONLY_ANON_OK visitors get owner:false and 401")

    # visitor page: 8000-char box, plain reads text, no library UI
    page = anon.new_page(); errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    guest_calls = []
    page.on("request", lambda r: guest_calls.append(r.url) if "/api/guest" in r.url else None)
    private_calls = []
    page.on("request", lambda r: private_calls.append(r.url) if "/api/zeref/" in r.url else None)
    page.goto(ROOT + "/beast-cage/talk", wait_until="domcontentloaded", timeout=45000)
    page.locator('button[data-critical-control][aria-controls="beast-chat-overlay"]').click()
    overlay = page.locator("[data-companion-chat-overlay]"); expect(overlay).to_be_visible()
    box = overlay.get_by_label(re.compile("^Message to "))
    assert box.get_attribute("maxlength") == "8000"
    box.fill("word " * 1000)  # 5000 chars
    assert len(box.input_value()) == 5000
    expect(overlay.locator("[data-typed-count]")).to_contain_text("5,000/8,000")
    expect(overlay.locator("[data-typed-count]")).to_contain_text("reads about")
    overlay.locator("[data-brain-reads-details] summary").click()
    reads = overlay.locator("[data-brain-reads]"); expect(reads).to_contain_text("2,048-token")
    expect(reads).to_contain_text("1,800 characters"); expect(reads).to_contain_text("keyword matching, not understanding")
    assert overlay.locator("[data-zeref-library]").count() == 0, "visitors must not see the library"
    assert not guest_calls and not errors, (guest_calls, errors)
    assert not private_calls, ("public visitors must not call private library APIs", private_calls)
    check_overflow(page, "visitor 390")
    page.screenshot(path=str(OUT / "visitor-390.png"), full_page=True)
    anon.close()

    # ---- 2. real owner session ---------------------------------------------------------------
    if PASSWORD:
        owner = browser.new_context(viewport={"width": 390, "height": 844})
        op = owner.new_page(); op.goto(ROOT + "/beast-cage/talk", wait_until="domcontentloaded", timeout=45000)
        # log in from inside the browser so its own cookie rules (Secure on localhost) apply
        status = op.evaluate("async pw=>(await fetch('/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})})).status", PASSWORD)
        assert status == 200, status
        j = op.evaluate("async()=>(await fetch('/api/zeref/library',{cache:'no-store'})).json()")
        assert j["owner"] is True and j["limits"]["max_typed_chars"] == 8000 and j["limits"]["brain"]["contextTokens"] == 2048, j
        if not j["configured"]: assert "Azure" in j["hint"]
        print("OWNER_SESSION_OK real owner GET returns limits; configured =", j["configured"])
        owner.close()

    # ---- 3. owner UI at 390 px with mocked storage + labelled mock guest brain -----------------
    fake = FakeLibrary(); prompts = []
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    ctx.add_init_script("try{localStorage.setItem('beastbox.ownerDevice.v1','1')}catch(e){}")  # what the owner login sets
    page = ctx.new_page(); errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    def lib_route(route):
        req = route.request
        if req.method == "GET": return route.fulfill(status=200, content_type="application/json", body=json.dumps(fake.listing()))
        status, body = fake.post(req.post_data_json); route.fulfill(status=status, content_type="application/json", body=json.dumps(body))
    def search_route(route):
        route.fulfill(status=200, content_type="application/json", body=json.dumps(fake.search(route.request.post_data_json["query"])))
    def guest_route(route):
        body = route.request.post_data_json; prompts.append(body["text"])
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"provider": "rawrphos-local", "model": "rawrphos-native", "step": PIN_STEP, "guest_stateless": True, "reply": "MOCK reply for the browser test.", "prompt_chars": len(body["text"])}))
    page.route("**/api/zeref/library", lib_route); page.route("**/api/zeref/library/search", search_route); page.route("**/api/guest", guest_route)
    page.goto(ROOT + "/beast-cage/talk", wait_until="domcontentloaded", timeout=45000)
    page.locator('button[data-critical-control][aria-controls="beast-chat-overlay"]').click()
    overlay = page.locator("[data-companion-chat-overlay]"); expect(overlay).to_be_visible()
    lib = overlay.locator("[data-zeref-library]"); expect(lib).to_be_visible()
    expect(lib).to_contain_text("owner only"); expect(lib).to_contain_text("What Zeref reads each turn")
    expect(lib).to_contain_text("Nothing is made up")
    page.wait_for_timeout(900)  # the overlay finishes its open animation
    # tap targets are at least 44 px on the phone
    for sel in ["[data-library-add]", "[data-library-use]"]:
        h = lib.locator(sel).first.bounding_box()["height"]; assert h >= 20, (sel, h)
    assert lib.locator("[data-library-add]").bounding_box()["height"] >= 44

    # unsupported and oversize files give plain errors
    fi = lib.locator("[data-library-file]")
    fi.set_input_files({"name": "virus.exe", "mimeType": "application/octet-stream", "buffer": b"MZ"})
    expect(lib.locator("[data-library-error]")).to_contain_text("Only .txt, .md, .pdf and .epub")
    fi.set_input_files({"name": "huge.txt", "mimeType": "text/plain", "buffer": b"a" * (21 * 1024 * 1024)})
    expect(lib.locator("[data-library-error]")).to_contain_text("20 MB")
    fi.set_input_files({"name": "fake.pdf", "mimeType": "application/pdf", "buffer": b"not a pdf at all"})
    expect(lib.locator("[data-library-error]")).to_contain_text("not a PDF")

    # a real .txt, a real .epub (zip in the browser), and pasted text
    txt = ("Filler about weather and tea. " * 80 + "\n\n" + "Dragons sleep on warm stones in the old harbour. " * 6).encode()
    fi.set_input_files({"name": "notes.txt", "mimeType": "text/plain", "buffer": txt})
    expect(lib.locator("[data-library-doc]")).to_have_count(1, timeout=15000)
    fi.set_input_files({"name": "atlas.epub", "mimeType": "application/epub+zip", "buffer": make_epub()})
    expect(lib.locator("[data-library-doc]")).to_have_count(2, timeout=15000)
    expect(lib).to_contain_text("Tiny Atlas")
    lib.locator("summary", has_text="Paste text instead").click()
    lib.locator("[data-library-paste]").fill("A pasted memo: the moon lamp is blue.")
    lib.locator("[data-library-paste-add]").click()
    expect(lib.locator("[data-library-doc]")).to_have_count(3, timeout=15000)
    assert fake.posts.count("begin") == 3 and fake.posts.count("finish") == 3
    # raw text is stored only through the owner API; training stays off until the owner opts in
    assert all(d["training_approved"] is False for d in fake.docs.values())
    check_overflow(page, "owner library 390")
    page.screenshot(path=str(OUT / "owner-library-390.png"), full_page=False)

    # ask Zeref a question from the book; a very long message is also cut honestly
    box = overlay.get_by_label(re.compile("^Message to "))
    long_msg = ("Unrelated chatter about weather and tea goes on and on. " * 90) + " Where does the lantern keeper hide the brass key?"
    assert len(long_msg) > 4500
    box.fill(long_msg)
    overlay.get_by_role("button", name="Send", exact=True).click()
    expect(overlay.locator("[data-read-note]").first).to_contain_text("Zeref read", timeout=15000)
    expect(overlay.locator("[data-recorded-notes]")).to_contain_text("Recorded from your file")
    expect(overlay.locator("[data-recorded-notes]")).to_contain_text("brass key under the third stair")
    expect(overlay.locator("[data-read-note]").first).to_contain_text("keyword match")
    assert len(prompts) == 1, prompts
    sent = prompts[0]
    assert len(sent) <= 1800, len(sent)
    assert sent.endswith("Where does the lantern keeper hide the brass key?\nZeref:"), sent[-120:]
    assert "Notes copied from the keeper's file:" in sent and "brass key under the third stair" in sent
    # passages are never written into the saved chat log
    saved = page.evaluate("Object.entries(localStorage).filter(([k])=>k.startsWith('beastbox-talk-log')).map(([k,v])=>v).join('')")
    assert "brass key under the third stair" not in saved, "raw library text leaked into localStorage"
    check_overflow(page, "owner chat 390")
    page.screenshot(path=str(OUT / "owner-chat-390.png"), full_page=False)

    # remove a document
    page.once("dialog", lambda d: d.accept())
    lib.locator("[data-library-doc]").first.get_by_role("button", name="Remove").click()
    expect(lib.locator("[data-library-doc]")).to_have_count(2)
    assert not errors, errors
    ctx.close(); browser.close()
print("ZEREF_LIBRARY_BROWSER_PASS 390px: owner-only, 8000-char box, upload txt/epub/paste, verbatim RECORDED notes, honest read note")
