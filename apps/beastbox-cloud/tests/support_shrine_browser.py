"""Real browser acceptance for the support shrine; never submits a payment.

Run against a local/preview server. SUPPORT_BROWSER_EXECUTABLE optionally selects
an existing Chromium. SUPPORT_BROWSER=webkit tests WebKit, not a physical iPhone.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("SUPPORT_BASE_URL", "http://127.0.0.1:3100")
OUT = Path(os.environ.get("SUPPORT_EVIDENCE_DIR", "/tmp/beastbox-support-evidence"))
OUT.mkdir(parents=True, exist_ok=True)
MONTHLY = [
    ("pocket-spark", "$5/month", "https://buy.stripe.com/3cIbJ27zN7kO8mN97pa7C01"),
    ("beast-keeper", "$15/month", "https://buy.stripe.com/fZueVe5rF7kO9qR3N5a7C02"),
    ("cosmos-builder", "$50/month", "https://buy.stripe.com/3cI28s2ft7kO6eF0ATa7C03"),
    ("universe-patron", "$150/month", "https://buy.stripe.com/6oU00kaLZax0eLb5Vda7C04"),
]
ONCE = [
    ("feed-the-beast", "$10 once", "https://donate.stripe.com/cNiaEY4nBcF87iJ1EXa7C05"),
    ("compute-burst", "$50 once", "https://donate.stripe.com/3cI8wQ8DRbB446x5Vda7C06"),
    ("hardware-rune", "$100 once", "https://donate.stripe.com/4gM00kdYb5cG8mN0ATa7C07"),
    ("launch-fuel", "$500 once", "https://donate.stripe.com/fZu7sM4nB20u0UlfvNa7C08"),
]
CANONICAL = """() => Object.fromEntries(['beastbox-companion-session-v1',
  'beastbox-active-creature-v1'].map(k => [k, localStorage.getItem(k)]))"""
AUDIO_PROBE = """(() => {
  window.__supportAudio = {contexts:0, voices:0, resumes:0};
  const Native = window.AudioContext || window.webkitAudioContext;
  if (!Native) return;
  const Wrapped = new Proxy(Native, {construct(target, args) {
    const ctx = Reflect.construct(target, args);
    window.__supportAudio.contexts++;
    const osc = ctx.createOscillator.bind(ctx);
    ctx.createOscillator = (...args) => {window.__supportAudio.voices++; return osc(...args);};
    const resume = ctx.resume.bind(ctx);
    ctx.resume = (...args) => {window.__supportAudio.resumes++; return resume(...args);};
    return ctx;
  }});
  if (window.AudioContext) window.AudioContext = Wrapped;
  if (window.webkitAudioContext) window.webkitAudioContext = Wrapped;
})();"""

def check_group(page, rows, touch=False):
    cards = page.locator("[data-support-tier]")
    expect(cards).to_have_count(4)
    for tier, price, url in rows:
        card = page.locator(f'[data-support-tier="{tier}"]')
        expect(card.get_by_text(price, exact=True)).to_be_visible()
        link = card.locator("a[data-support-checkout]")
        expect(link).to_have_attribute("href", url)
        expect(link).to_have_attribute("rel", "noopener noreferrer")
        expect(link).to_have_attribute("target", "_blank")
        # Both a touch/keyboard pet and a real checkout anchor remain available.
        pet = card.get_by_role("button", name="Meet " + card.get_attribute("data-support-name"))
        pet.tap() if touch else pet.click()
        expect(page.locator("[data-support-transmission]")).not_to_be_empty()
        box = pet.bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44, "small touch target"

def run(browser, engine, width, reduced=False):
    context = browser.new_context(viewport={"width":width, "height":844},
                                  has_touch=width < 600, reduced_motion="reduce" if reduced else "no-preference")
    context.add_init_script(AUDIO_PROBE)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.goto(BASE, wait_until="networkidle")
    launcher = page.get_by_role("button", name="Open Feed the Beast support panel")
    expect(launcher).to_be_visible()
    assert page.evaluate("window.__supportAudio.contexts") == 0, "audio autoplay"
    # Ambient music is independent from shrine SFX. Pause the site soundtrack
    # before asserting that Mute Beast sounds creates no additional voices.
    options = page.get_by_role("button", name="Open sound options")
    options.tap() if width < 600 else options.click()
    page.get_by_role("button", name="Pause cosmic background music").click()
    page.get_by_role("button", name="Close sound options").click()
    initial = page.evaluate(CANONICAL)
    launcher.tap() if width < 600 else launcher.click()
    shrine = page.get_by_role("dialog", name="Feed the Beast")
    expect(shrine).to_be_visible()
    monthly = page.get_by_role("tab", name="Monthly Companions")
    expect(monthly).to_have_attribute("aria-selected", "true")
    page.screenshot(path=str(OUT / f"{engine}-{width}-entrance{'-reduced' if reduced else ''}.png"))
    check_group(page, MONTHLY, width < 600)
    page.screenshot(path=str(OUT / f"{engine}-{width}-monthly{'-reduced' if reduced else ''}.png"))
    page.get_by_role("tab", name="One-Time Fuel").click()
    check_group(page, ONCE, width < 600)
    page.screenshot(path=str(OUT / f"{engine}-{width}-once{'-reduced' if reduced else ''}.png"))
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "horizontal overflow"
    close = page.get_by_role("button", name="Close support panel")
    close_box = close.bounding_box()
    assert close_box["y"] >= 0 and close_box["y"] + close_box["height"] <= 844, "close offscreen"
    assert close_box["width"] >= 44 and close_box["height"] >= 44
    # The entire document remains usable; no body scroll lock.
    assert page.evaluate("getComputedStyle(document.body).overflow") != "hidden"
    page.get_by_role("tab", name="One-Time Fuel").focus()
    page.keyboard.press("ArrowLeft")
    expect(monthly).to_be_focused()
    expect(monthly).to_have_attribute("aria-selected", "true")
    page.get_by_role("tab", name="One-Time Fuel").click()
    # Intercept the destination, never submit or simulate a successful payment.
    context.route("https://donate.stripe.com/**", lambda route: route.fulfill(status=200, body="Checkout destination intercepted by local acceptance test."))
    with page.expect_popup() as opened:
        page.locator('[data-support-tier="feed-the-beast"] a[data-support-checkout]').click()
    popup = opened.value
    popup.wait_for_load_state()
    assert popup.url == ONCE[0][2]
    expect(page.locator("[data-support-transmission]")).to_contain_text("Opening cosmic fuel portal")
    assert "payment successful" not in shrine.inner_text().lower()
    assert "stardust received" not in shrine.inner_text().lower()
    popup.close()
    expect(shrine.get_by_role("link", name="GitHub Sponsors")).to_have_attribute("href", "https://github.com/sponsors/NavisWORLD")
    expect(shrine.get_by_role("link", name="Buy Me a Coffee")).to_have_attribute("href", "https://buymeacoffee.com/Cosmic_syanpse")
    assert page.evaluate(CANONICAL) == initial, "support modified canonical creature state"
    assert page.evaluate("window.__supportAudio.voices") > 0, "no interaction audio scheduled"
    audio_after_interactions = page.evaluate("window.__supportAudio")
    page.get_by_role("button", name="Mute Beast sounds").click()
    before = page.evaluate("window.__supportAudio.voices")
    page.get_by_role("button", name="Sprinkle stardust on the Beast").click()
    page.wait_for_timeout(100)
    assert page.evaluate("window.__supportAudio.voices") == before, "mute failed"
    if reduced:
        assert page.locator(".support-mascot-breathe").first.evaluate("e => getComputedStyle(e).animationName") == "none"
    page.keyboard.press("Escape")
    expect(shrine).to_have_count(0)
    expect(launcher).to_be_focused()
    page.reload(wait_until="networkidle")
    launcher.click()
    expect(page.get_by_role("button", name="Enable Beast sounds")).to_be_visible()
    expect(page.get_by_role("button", name="Enable Beast sounds")).to_have_attribute("aria-pressed", "false")
    assert not errors, errors
    result = {"engine":engine,"width":width,"reducedMotion":reduced,"passed":True,
              "audioAfterInteractions":audio_after_interactions,"audioAfterMutedReload":page.evaluate("window.__supportAudio")}
    context.close()
    return result

with sync_playwright() as p:
    engine = os.environ.get("SUPPORT_BROWSER", "chromium")
    kwargs = {"headless":True}
    if engine == "chromium":
        kwargs["args"] = ["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
        if os.environ.get("SUPPORT_BROWSER_EXECUTABLE"):
            kwargs["executable_path"] = os.environ["SUPPORT_BROWSER_EXECUTABLE"]
        else:
            kwargs["channel"] = "chrome"
    browser = getattr(p, engine).launch(**kwargs)
    results = [run(browser, engine, w) for w in [1440,390,430]]
    results.append(run(browser, engine, 390, True))
    browser.close()
    (OUT / f"{engine}-results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
