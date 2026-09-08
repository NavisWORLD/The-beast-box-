"""Record a literal COSMIC.CYPHER browser conversation against a live compatible cloud model.

This demo exercises the current main-derived browser UI and durable runtime. It is
not a consciousness, identity, or model-training test. The only remote authority
granted is cloud inference for the selected provider.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

from playwright.sync_api import expect, sync_playwright


BASE_URL = "https://oai.aihorde.net/v1"
ANON_KEY = "0000000000"
PREFERRED_MODELS = (
    "Behemoth-X-123B",
    "Behemoth-128B",
    "Anubis-70B",
    "Skyfall-31B",
    "Cydonia-24B",
)
PROMPTS = (
    "Hey Beast, this is ChatGPT talking to you through Cory's freshly finished COSMIC.CYPHER UI. No benchmark voice - just talk to me normally. What's it like from your side: what are you doing, and what is Beast Box doing around you? Keep it to 4 short sentences.",
    "Okay, now challenge the idea instead of flattering it. What's genuinely useful about a model-independent persistent substrate, and what's the biggest engineering risk? Keep it conversational and use two short paragraphs.",
    "Cool. Remember these two things for later in this same conversation: GREEN SUNFLOWER and the joke 'the brain forgot its badge.' Work both into a tiny joke so I know you heard me.",
    "Forget architecture for a minute. If Beast Box were a tiny room on a spaceship, describe the room in 3 vivid sentences. Make it weird but cozy.",
    "Last one. Without me repeating them, tell me the phrase and the joke I gave you earlier. Then give Cory one sentence on what this live demo proves, and one sentence on what it absolutely does not prove.",
)


def _request_json(url: str, *, payload: dict[str, object] | None = None, timeout: float = 90.0) -> object:
    headers = {"Accept": "application/json", "Authorization": "Bearer " + os.environ.get("AI_HORDE_API_KEY", ANON_KEY)}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise RuntimeError("upstream response exceeded two MiB")
    return json.loads(raw.decode("utf-8"))


def select_model(output: Path) -> tuple[str, str]:
    catalog = _request_json(BASE_URL + "/models?min_size=20&max_size=140", timeout=60)
    if isinstance(catalog, dict):
        rows = catalog.get("data", [])
    elif isinstance(catalog, list):
        rows = catalog
    else:
        rows = []
    ids = [row.get("id") for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)]
    if not ids:
        raise RuntimeError("AI Horde OpenAI catalog returned no usable live text models")
    selected = next((model for needle in PREFERRED_MODELS for model in ids if needle.lower() in model.lower()), ids[0])

    preflight_prompt = "Reply in one short sentence: fresh COSMIC UI model online."
    preflight_payload: dict[str, object] = {
        "model": selected,
        "messages": [{"role": "user", "content": preflight_prompt}],
        "stream": False,
        "temperature": 0,
        "max_tokens": 48,
    }
    last_error = ""
    preflight = ""
    for delay in (0, 2, 5, 10):
        if delay:
            time.sleep(delay)
        try:
            result = _request_json(BASE_URL + "/chat/completions", payload=preflight_payload, timeout=120)
            preflight = result["choices"][0]["message"]["content"]  # type: ignore[index]
            if not isinstance(preflight, str) or not preflight.strip():
                raise RuntimeError("empty preflight response")
            break
        except (OSError, KeyError, IndexError, TypeError, ValueError, RuntimeError, urllib.error.HTTPError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
    if not preflight:
        raise RuntimeError("selected cloud model failed preflight: " + last_error)

    selection = {
        "provider": "AI Horde OpenAI-compatible proxy",
        "base_url": BASE_URL,
        "anonymous_api_key": True,
        "selected_model": selected,
        "active_model_ids": ids,
        "preflight_prompt": preflight_prompt,
        "preflight_response": preflight,
    }
    (output / "MODEL_SELECTION.json").write_text(json.dumps(selection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return selected, preflight


def _nav(page, name: str) -> None:
    page.locator("#nav").get_by_role("button", name=name, exact=True).click()
    page.wait_for_timeout(450)


def _grant(page, name: str) -> None:
    _nav(page, "AUTHORITY")
    row = page.locator(".authority-row").filter(has_text=name.upper() + " · DENIED")
    expect(row).to_be_visible(timeout=10_000)
    row.get_by_role("button", name="GRANT", exact=True).click()
    expect(page.locator(".authority-row").filter(has_text=name.upper() + " · GRANTED")).to_be_visible(timeout=10_000)


def _send_turn(page, prompt: str, *, timeout_ms: int = 180_000) -> str:
    assistants = page.locator(".msg.assistant")
    before = assistants.count()
    box = page.get_by_label("Message", exact=True)
    box.click()
    box.type(prompt, delay=7)
    page.get_by_role("button", name="SEND", exact=True).click()

    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if assistants.count() > before:
            break
        notice = page.locator("#notice.error")
        if notice.count() and notice.is_visible():
            text = notice.inner_text().strip()
            if text:
                raise RuntimeError("COSMIC UI chat request failed: " + text)
        page.wait_for_timeout(500)
    else:
        raise RuntimeError("timed out waiting for assistant response")

    node = assistants.nth(before)
    response = node.evaluate("el => el.childNodes.length ? (el.childNodes[0].textContent || '') : ''")
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("assistant response was empty")
    page.locator("#chatlog").evaluate("el => { el.scrollTop = el.scrollHeight; }")
    page.wait_for_timeout(2500)
    return response.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--output", type=Path, default=Path("build/fresh-cosmic-conversation"))
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    (output / "video-raw").mkdir(parents=True, exist_ok=True)

    selected_model, preflight = select_model(output)
    transcript: list[dict[str, str]] = []
    browser_errors: list[str] = []
    started = time.time()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            reduced_motion="reduce",
            record_video_dir=str(output / "video-raw"),
            record_video_size={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.on("pageerror", lambda error: browser_errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(args.url, wait_until="networkidle")
        expect(page.locator("#runtimePill")).to_have_text("SUBSTRATE VERIFIED", timeout=20_000)
        system_id_before = page.locator("#systemId").inner_text().strip()
        page.screenshot(path=str(output / "00-orbit-fresh.png"), full_page=True)
        page.wait_for_timeout(2000)

        # The old brain receives a one-session cloud grant only so the owner can
        # configure a remote provider. The identity change must revoke it.
        _grant(page, "cloud")
        _nav(page, "BRAIN BAY")
        page.locator("#providerKind").select_option("compatible")
        page.locator("#providerModel").fill(selected_model)
        page.locator("#providerUrl").fill(BASE_URL)
        page.locator("#providerEnv").fill("AI_HORDE_API_KEY")
        page.locator("#allowRemote").check()
        page.get_by_role("button", name="CLOCK IN BRAIN", exact=True).click()
        expect(page.locator("#handoff")).to_be_visible(timeout=15_000)
        expect(page.locator("#cloudPill")).to_have_text("CLOUD DENIED", timeout=15_000)
        system_id_after_clockin = page.locator("#systemId").inner_text().strip()
        page.screenshot(path=str(output / "01-brain-clocked-in-authority-revoked.png"), full_page=True)
        page.wait_for_timeout(1800)

        # Explicitly re-authorize only cloud inference for the new brain.
        _grant(page, "cloud")
        expect(page.locator("#cloudPill")).to_have_text("CLOUD AUTHORIZED", timeout=10_000)
        _nav(page, "BRAIN")
        page.wait_for_timeout(1200)

        for index, prompt in enumerate(PROMPTS, start=1):
            response = _send_turn(page, prompt)
            transcript.append({"turn": str(index), "user": prompt, "assistant": response})
            page.screenshot(path=str(output / f"turn-{index:02d}.png"), full_page=True)

        # Capture the durable story state after the literal conversation.
        _nav(page, "MEMORY VAULT")
        page.get_by_role("button", name="REFRESH", exact=True).click()
        page.wait_for_timeout(900)
        page.screenshot(path=str(output / "90-memory-vault.png"), full_page=True)
        _nav(page, "ORBIT")
        system_id_after = page.locator("#systemId").inner_text().strip()
        memory_records = page.locator("#memoryCount").inner_text().strip()
        checkpoint = page.locator("#checkpoint").inner_text().strip()
        provider_pill = page.locator("#providerPill").inner_text().strip()
        page.screenshot(path=str(output / "99-orbit-after-conversation.png"), full_page=True)
        page.wait_for_timeout(2200)

        video = page.video
        context.close()
        if video is None:
            raise RuntimeError("Playwright did not create a video object")
        video.save_as(str(output / "BEAST_BOX_COSMIC_FRESH_UI_REAL_CONVERSATION.webm"))
        browser.close()

    transcript_text = []
    for turn in transcript:
        transcript_text.append(f"TURN {turn['turn']} — CHATGPT\n{turn['user']}\n\nTURN {turn['turn']} — BEAST MODEL\n{turn['assistant']}\n")
    (output / "FULL_TRANSCRIPT.txt").write_text("\n".join(transcript_text), encoding="utf-8")

    receipt = {
        "schema": "beast-box-cosmic-fresh-ui-real-conversation-v1",
        "main_source_sha": os.environ.get("DEMO_MAIN_SHA", "unknown"),
        "workflow_sha": os.environ.get("GITHUB_SHA", "unknown"),
        "provider": "AI Horde OpenAI-compatible proxy",
        "provider_base_url": BASE_URL,
        "anonymous_api_key": True,
        "model": selected_model,
        "preflight_response": preflight,
        "conversation_turns": len(transcript),
        "system_id_before": system_id_before,
        "system_id_after_clockin": system_id_after_clockin,
        "system_id_after": system_id_after,
        "system_id_stable": system_id_before == system_id_after_clockin == system_id_after,
        "memory_records_ui": memory_records,
        "checkpoint_ui": checkpoint,
        "provider_pill": provider_pill,
        "cloud_authority_reauthorized_after_brain_change": True,
        "browser_page_errors": browser_errors,
        "literal_browser_video": True,
        "fresh_cosmic_ui": True,
        "elapsed_seconds": round(time.time() - started, 3),
        "claim_boundary": (
            "This records a real browser conversation through the current COSMIC.CYPHER UI and Beast durable runtime "
            "using one live external inference model. It demonstrates software chat, context/memory delivery, durable state, "
            "provider clock-in and explicit cloud authority. It does not establish consciousness, identity, model training, "
            "physical sensor validation, custom voice, quantum advantage, or model-swap continuity in this particular run."
        ),
    }
    (output / "RUN_RECEIPT.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if browser_errors:
        raise RuntimeError("browser page errors occurred: " + repr(browser_errors))


if __name__ == "__main__":
    main()
