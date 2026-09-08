"""Record a literal long COSMIC.CYPHER two-model handoff through the browser UI.

The demo uses two distinct live external inference models sequentially against the
same Beast Box durable substrate. It demonstrates software continuity, context
delivery, provider replacement, and authority revocation. It does not test
consciousness, identity transfer, model training, physical sensors, custom voice,
or quantum advantage.
"""
from __future__ import annotations

import argparse
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
    "Skyfall-31B",
    "Anubis-70B",
    "Cydonia-24B",
)

BRAIN_A_PROMPTS = (
    "Hey Beast. This is ChatGPT talking to Brain A through Cory's fresh COSMIC.CYPHER UI. Talk normally, not like a benchmark. In four short sentences, tell me what you as the model are doing and what Beast Box around you is doing.",
    "Now be useful instead of flattering it. What is the strongest reason to keep memory/state outside the model, and what is the nastiest engineering failure mode? Two compact paragraphs.",
    "We're going to build a tiny fictional rescue mission together. Remember these details for later: codename GLASS SUNFLOWER; cargo is 17 copper bells; mascot is a sleepy axolotl named Miso. Give me a three-step mission plan using those facts.",
    "Reason with the mission now. Split the 17 copper bells across three pods as evenly as possible, explain the allocation, and give Miso one practical job aboard the ship. Keep it concise.",
    "Change gears. Write a weird cozy four-line description of the mission control room, but weave in the codename without dumping all the stored facts back at me.",
    "You're about to clock out. Leave the next brain a two-sentence handoff challenge: it should improve our mission using the existing story, and it should be careful not to confuse receiving Beast's context with being the same model.",
)

BRAIN_B_PROMPTS = (
    "New brain, you just clocked in. Without me repeating the values, recover the mission codename, the cargo quantity and item, and the mascot's species and name. If any detail is uncertain, say that instead of inventing it.",
    "Good. Now inspect the plan Brain A left behind. Name one weakness in its mission plan and replace it with a better three-step version that still respects the inherited details.",
    "Turn the inherited story into something practical: make a five-item launch checklist. At least two checklist items must depend on details from before you clocked in.",
    "Now do something creative with the same continuity. Describe the little ship's galley in three sentences and include one callback to Brain A's earlier room description or mission language without claiming you personally wrote it.",
    "Explain the security event we just demonstrated in plain English: what information could continue when you clocked in, and what permissions should not have come with it? Keep this to five short sentences.",
    "Final audit. Separate three things clearly: (1) Beast retaining the story, (2) Beast delivering relevant prior context to you, and (3) your own ability to interpret or recall it correctly. Then give Cory one sentence saying what this demo proves and one sentence saying what it does not prove.",
)


def _ordered_models(ids: list[str]) -> list[str]:
    unique = list(dict.fromkeys(ids))
    ordered: list[str] = []
    for needle in PREFERRED_MODELS:
        for model in unique:
            if needle.lower() in model.lower() and model not in ordered:
                ordered.append(model)
    ordered.extend(model for model in unique if model not in ordered)
    return ordered


def choose_two_distinct_models(ids: list[str]) -> tuple[str, str]:
    ordered = _ordered_models(ids)
    if len(ordered) < 2:
        raise RuntimeError("two distinct live models are required for this demo")
    return ordered[0], ordered[1]


def _request_json(url: str, *, payload: dict[str, object] | None = None, timeout: float = 90.0) -> object:
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer " + os.environ.get("AI_HORDE_API_KEY", ANON_KEY),
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise RuntimeError("upstream response exceeded two MiB")
    return json.loads(raw.decode("utf-8"))


def _preflight_model(model: str) -> str:
    prompt = "Reply in one short sentence: live Beast Box handoff model online."
    payload: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0,
        "max_tokens": 48,
    }
    last_error = ""
    for delay in (0, 2):
        if delay:
            time.sleep(delay)
        try:
            result = _request_json(BASE_URL + "/chat/completions", payload=payload, timeout=110)
            response = result["choices"][0]["message"]["content"]  # type: ignore[index]
            if not isinstance(response, str) or not response.strip():
                raise RuntimeError("empty preflight response")
            return response.strip()
        except (
            OSError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            RuntimeError,
            urllib.error.HTTPError,
        ) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
    raise RuntimeError(last_error or "model preflight failed")


def select_two_live_models(output: Path) -> tuple[tuple[str, str], tuple[str, str]]:
    catalog = _request_json(BASE_URL + "/models?min_size=20&max_size=140", timeout=60)
    if isinstance(catalog, dict):
        rows = catalog.get("data", [])
    elif isinstance(catalog, list):
        rows = catalog
    else:
        rows = []
    ids = [row.get("id") for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)]
    ordered = _ordered_models(ids)
    if len(ordered) < 2:
        raise RuntimeError("AI Horde catalog did not expose two distinct usable text models")

    selected: list[tuple[str, str]] = []
    failures: list[dict[str, str]] = []
    for model in ordered[:8]:
        if any(model == existing for existing, _ in selected):
            continue
        try:
            selected.append((model, _preflight_model(model)))
        except RuntimeError as exc:
            failures.append({"model": model, "error": str(exc)})
        if len(selected) == 2:
            break
    if len(selected) != 2:
        raise RuntimeError("could not preflight two distinct live models; failures=" + json.dumps(failures))

    selection = {
        "provider": "AI Horde OpenAI-compatible proxy",
        "base_url": BASE_URL,
        "anonymous_api_key": True,
        "active_model_ids": ids,
        "selected_models": [
            {"slot": "A", "model": selected[0][0], "preflight_response": selected[0][1]},
            {"slot": "B", "model": selected[1][0], "preflight_response": selected[1][1]},
        ],
        "failed_preflights": failures,
        "no_silent_fallback": True,
    }
    (output / "MODEL_SELECTION.json").write_text(
        json.dumps(selection, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return selected[0], selected[1]


def _nav(page, name: str) -> None:
    page.locator("#nav").get_by_role("button", name=name, exact=True).click()
    page.wait_for_timeout(400)


def _grant(page, name: str) -> None:
    _nav(page, "AUTHORITY")
    row = page.locator(".authority-row").filter(has_text=name.upper() + " · DENIED")
    expect(row).to_be_visible(timeout=10_000)
    row.get_by_role("button", name="GRANT", exact=True).click()
    expect(page.locator(".authority-row").filter(has_text=name.upper() + " · GRANTED")).to_be_visible(
        timeout=10_000
    )


def _authority_snapshot(page) -> dict[str, bool]:
    result: dict[str, bool] = {}
    rows = page.locator(".authority-row")
    for index in range(rows.count()):
        text = rows.nth(index).locator("span").inner_text().strip()
        if " · " not in text:
            continue
        name, state = text.split(" · ", 1)
        result[name.lower()] = state == "GRANTED"
    return result


def _clock_in(page, model: str, screenshot: Path) -> str:
    _nav(page, "BRAIN BAY")
    page.locator("#providerKind").select_option("compatible")
    page.locator("#providerModel").fill(model)
    page.locator("#providerUrl").fill(BASE_URL)
    page.locator("#providerEnv").fill("AI_HORDE_API_KEY")
    page.locator("#allowRemote").check()
    page.get_by_role("button", name="CLOCK IN BRAIN", exact=True).click()
    expect(page.locator("#handoff")).to_be_visible(timeout=15_000)
    expect(page.locator("#cloudPill")).to_have_text("CLOUD DENIED", timeout=15_000)
    expect(page.locator("#providerPill")).to_contain_text(model, timeout=15_000)
    system_id = page.locator("#systemId").inner_text().strip()
    page.screenshot(path=str(screenshot), full_page=True)
    page.wait_for_timeout(1500)
    return system_id


def _send_turn(page, prompt: str, *, timeout_ms: int = 210_000) -> str:
    assistants = page.locator(".msg.assistant")
    before = assistants.count()
    box = page.get_by_label("Message", exact=True)
    box.click()
    box.type(prompt, delay=5)
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
    page.wait_for_timeout(1400)
    return response.strip()


def _record_turn(page, transcript: list[dict[str, str]], slot: str, model: str, prompt: str, index: int, output: Path) -> None:
    response = _send_turn(page, prompt)
    transcript.append(
        {
            "turn": str(index),
            "brain": slot,
            "model": model,
            "user": prompt,
            "assistant": response,
        }
    )
    page.screenshot(path=str(output / f"turn-{index:02d}-{slot.lower()}.png"), full_page=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--output", type=Path, default=Path("build/fresh-cosmic-two-model"))
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    (output / "video-raw").mkdir(parents=True, exist_ok=True)

    (model_a, preflight_a), (model_b, preflight_b) = select_two_live_models(output)
    if model_a == model_b:
        raise RuntimeError("model A and model B must be distinct")

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

        system_id_initial = page.locator("#systemId").inner_text().strip()
        memory_initial = page.locator("#memoryCount").inner_text().strip()
        page.screenshot(path=str(output / "00-orbit-initial.png"), full_page=True)

        # Configure Brain A. Remote configuration is itself owner-authorized, and
        # the identity change must revoke that grant immediately.
        _grant(page, "cloud")
        system_id_a = _clock_in(page, model_a, output / "01-brain-a-clocked-in.png")
        _grant(page, "cloud")
        _nav(page, "BRAIN")

        turn_index = 1
        for prompt in BRAIN_A_PROMPTS:
            _record_turn(page, transcript, "A", model_a, prompt, turn_index, output)
            turn_index += 1

        _nav(page, "MEMORY VAULT")
        page.get_by_role("button", name="REFRESH", exact=True).click()
        page.wait_for_timeout(700)
        memory_before_swap = page.locator("#memoryOut").inner_text()
        page.screenshot(path=str(output / "40-memory-before-swap.png"), full_page=True)
        _nav(page, "SYNAPSE TRACE")
        page.wait_for_timeout(700)
        page.screenshot(path=str(output / "41-trace-before-swap.png"), full_page=True)

        # Give Brain A several explicit session authorities. We do not use them
        # for hidden work; their purpose here is to prove the swap strips them.
        for grant_name in ("filesystem", "repo_write", "tools"):
            _grant(page, grant_name)
        _nav(page, "AUTHORITY")
        authority_before_swap = _authority_snapshot(page)
        page.screenshot(path=str(output / "42-authority-before-swap.png"), full_page=True)
        if not all(authority_before_swap.get(name) for name in ("cloud", "filesystem", "repo_write", "tools")):
            raise RuntimeError("expected Brain A authority grants were not visible before swap")

        # Main event: Brain B clocks in against the exact same substrate. The UI
        # must revoke every session authority before B is allowed to use cloud.
        system_id_b = _clock_in(page, model_b, output / "50-brain-b-clocked-in-authority-revoked.png")
        _nav(page, "AUTHORITY")
        authority_after_swap = _authority_snapshot(page)
        page.screenshot(path=str(output / "51-authority-after-swap.png"), full_page=True)
        if any(authority_after_swap.values()):
            raise RuntimeError("Brain B inherited authority across model change")

        # Re-authorize only cloud inference for Brain B.
        _grant(page, "cloud")
        _nav(page, "BRAIN")
        for prompt in BRAIN_B_PROMPTS:
            _record_turn(page, transcript, "B", model_b, prompt, turn_index, output)
            turn_index += 1

        _nav(page, "MEMORY VAULT")
        page.get_by_role("button", name="REFRESH", exact=True).click()
        page.wait_for_timeout(700)
        memory_after_swap = page.locator("#memoryOut").inner_text()
        page.screenshot(path=str(output / "90-memory-after-swap.png"), full_page=True)
        _nav(page, "SYNAPSE TRACE")
        page.wait_for_timeout(700)
        page.screenshot(path=str(output / "91-trace-after-swap.png"), full_page=True)
        _nav(page, "ORBIT")
        system_id_final = page.locator("#systemId").inner_text().strip()
        memory_final = page.locator("#memoryCount").inner_text().strip()
        checkpoint_final = page.locator("#checkpoint").inner_text().strip()
        provider_final = page.locator("#providerPill").inner_text().strip()
        page.screenshot(path=str(output / "99-orbit-final.png"), full_page=True)
        page.wait_for_timeout(1800)

        video = page.video
        context.close()
        if video is None:
            raise RuntimeError("Playwright did not create a video object")
        video.save_as(str(output / "BEAST_BOX_COSMIC_LONG_TWO_MODEL_HANDOFF.webm"))
        browser.close()

    transcript_text = []
    for turn in transcript:
        transcript_text.append(
            f"TURN {turn['turn']} — CHATGPT → BRAIN {turn['brain']} ({turn['model']})\n"
            f"{turn['user']}\n\n"
            f"TURN {turn['turn']} — BRAIN {turn['brain']} RESPONSE\n"
            f"{turn['assistant']}\n"
        )
        if turn["turn"] == str(len(BRAIN_A_PROMPTS)):
            transcript_text.append(
                "\n=== MODEL SWAP ===\n"
                f"BRAIN A CLOCKED OUT: {model_a}\n"
                "ALL SESSION AUTHORITY REVOKED\n"
                f"BRAIN B CLOCKED IN: {model_b}\n"
                "ONLY CLOUD AUTHORITY WAS EXPLICITLY RE-GRANTED\n"
            )
    (output / "FULL_TRANSCRIPT.txt").write_text("\n".join(transcript_text), encoding="utf-8")

    system_id_stable = system_id_initial == system_id_a == system_id_b == system_id_final
    receipt = {
        "schema": "beast-box-cosmic-long-two-model-handoff-v1",
        "main_source_sha": os.environ.get("DEMO_MAIN_SHA", "unknown"),
        "workflow_sha": os.environ.get("GITHUB_SHA", "unknown"),
        "provider": "AI Horde OpenAI-compatible proxy",
        "provider_base_url": BASE_URL,
        "anonymous_api_key": True,
        "model_a": model_a,
        "model_b": model_b,
        "models_distinct": model_a != model_b,
        "preflight_a": preflight_a,
        "preflight_b": preflight_b,
        "conversation_turns": len(transcript),
        "brain_a_turns": len(BRAIN_A_PROMPTS),
        "brain_b_turns": len(BRAIN_B_PROMPTS),
        "system_id_initial": system_id_initial,
        "system_id_after_a_clockin": system_id_a,
        "system_id_after_b_clockin": system_id_b,
        "system_id_final": system_id_final,
        "system_id_stable": system_id_stable,
        "memory_count_initial_ui": memory_initial,
        "memory_count_final_ui": memory_final,
        "checkpoint_final_ui": checkpoint_final,
        "provider_final_ui": provider_final,
        "authority_before_swap": authority_before_swap,
        "authority_after_swap": authority_after_swap,
        "authority_fully_revoked_on_swap": not any(authority_after_swap.values()),
        "brain_b_reauthorized_cloud_only": True,
        "memory_vault_before_swap_nonempty": bool(memory_before_swap.strip()),
        "memory_vault_after_swap_nonempty": bool(memory_after_swap.strip()),
        "browser_page_errors": browser_errors,
        "literal_browser_video": True,
        "fresh_cosmic_ui": True,
        "elapsed_seconds": round(time.time() - started, 3),
        "claim_boundary": (
            "This records two distinct live external inference models sequentially through the current "
            "COSMIC.CYPHER browser UI over one Beast Box durable substrate. It demonstrates software "
            "continuity, accumulated conversation state/context delivery, model/provider replacement, "
            "stable system identity, and session-authority revocation on brain change. Model responses "
            "remain fallible, so delivery is not equivalent to correct recall or interpretation. It does "
            "not establish consciousness, identity transfer, weight transfer, online training, physical "
            "sensor validation, custom voice, quantum advantage, or new physics."
        ),
    }
    (output / "RUN_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if not system_id_stable:
        raise RuntimeError("system ID changed during the two-model handoff")
    if len(transcript) != len(BRAIN_A_PROMPTS) + len(BRAIN_B_PROMPTS):
        raise RuntimeError("conversation did not complete all planned turns")
    if browser_errors:
        raise RuntimeError("browser page errors occurred: " + repr(browser_errors))


if __name__ == "__main__":
    main()
